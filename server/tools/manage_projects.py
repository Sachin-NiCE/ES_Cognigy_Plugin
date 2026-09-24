"""manage_projects: create/list/delete Cognigy projects.

Endpoints (see server/cognigy_client.py for prefix/auth conventions):
    GET   /v2.0/projects                  -> list
    POST  /v2.0/projects                  body: {name, color, locale} -> create
    GET   /v2.0/projects/{id}             -> single project (used to read its
                                              current name before a rename)
    PATCH /v2.0/projects/{id}             body: {name} -> rename (used for
                                              both the soft-delete marker and,
                                              indirectly, nothing else here)
    PATCH /v2.0/flows/{id}                body: {name} -> rename the
                                              auto-provisioned flow to match
                                              the project name

DELETE IS A SOFT DELETE, ON PURPOSE: mirrors the same "never destroy human
data irreversibly" stance as manage_snapshots. A project is never actually
deleted via this API - `delete_project` only renames it with a `DELETE_`
prefix, exactly like the reference implementation this was modeled on treats
flow/project/agent resources. Everything inside the project (flows, agents,
endpoints) stays live; the caller is told this explicitly.

CREATE PROVISIONS A DEFAULT FLOW from server/templates/environment_setup/,
imported via the same package-import machinery as manage_packages
(list_exportable/upload_and_inspect/import_package), then renamed to match
the new project's name. That template is a trimmed, secret-scrubbed
copy of a real "*_Environment_Setup" flow - see
server/templates/build_environment_setup_template.py for how it was built
and what was deliberately left out (disabled nodes, the HTTP-request-onward
chain, and any real base URL/client ID/secret/endpoint-token values).
"""

from __future__ import annotations

import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Optional

from cognigy_client import CognigyClient, CognigyCreds
from tools import manage_packages

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "environment_setup"
TEMPLATE_FLOW_NAME = "Environment_Setup"  # placeholder name baked into the template


def list_projects(creds: CognigyCreds, limit: int = 25, skip: int = 0) -> dict[str, Any]:
    with CognigyClient(*creds) as client:
        return client.get("/v2.0/projects", params={"limit": limit, "skip": skip})


def create_project(creds: CognigyCreds, name: str, description: Optional[str] = None) -> dict[str, Any]:
    """Create a project and provision it with a default Environment Setup flow
    (see module docstring), renamed to match `name`.
    """
    with CognigyClient(*creds) as client:
        body: dict[str, Any] = {"name": name, "color": "blue", "locale": "en-US"}
        if description:
            body["description"] = description
        project = client.post("/v2.0/projects", json=body)
        project_id = project.get("_id") or project.get("id")

        agent_locale_ref = _find_locale_id(
            manage_packages.list_exportable(creds, project_id)["graph"].get(project_id, {})
        )

        template_zip = _build_template_zip()
        try:
            preview = manage_packages.upload_and_inspect(creds, project_id, str(template_zip))
            package_id = preview["packageId"]
            package_locale_ref = _find_locale_id(preview.get("packageResources", {}))

            locale_mapping = None
            if package_locale_ref and agent_locale_ref:
                locale_mapping = [{"packageLocaleId": package_locale_ref, "agentLocaleId": agent_locale_ref}]

            import_result = manage_packages.import_package(
                creds, project_id, package_id, resources=None, locale_mapping=locale_mapping
            )
        finally:
            template_zip.unlink(missing_ok=True)

        flow_id, flow_name = _find_flow_by_name(creds, project_id, TEMPLATE_FLOW_NAME)
        renamed = False
        if flow_id:
            client.patch(f"/v2.0/flows/{flow_id}", json={"name": name})
            flow_name = name
            renamed = True

    return {
        "projectId": project_id,
        "projectName": name,
        "flowId": flow_id,
        "flowName": flow_name,
        "flowRenamed": renamed,
        "importTask": import_result.get("task", {}).get("status"),
    }


def delete_project(creds: CognigyCreds, project_id: str, confirm: bool = False) -> dict[str, Any]:
    """Soft-delete: renames the project with a `DELETE_` prefix. Never a real
    delete - flows, agents and endpoints inside the project stay live and
    reachable. Without confirm=True this only reports a preflight; nothing
    is changed."""
    with CognigyClient(*creds) as client:
        project = client.get(f"/v2.0/projects/{project_id}")
        current_name = project.get("name", "")

        if current_name.startswith("DELETE_"):
            return {"alreadyMarked": True, "projectId": project_id, "name": current_name}

        if not confirm:
            return {
                "preflight": True,
                "warning": (
                    f'This will rename project "{current_name}" to "DELETE_{current_name}" '
                    "to mark it for manual deletion. Nothing inside it is deleted or taken "
                    "offline - flows, agents and endpoints remain live and reachable. "
                    "Re-run with confirm=True to proceed."
                ),
                "projectId": project_id,
                "name": current_name,
            }

        new_name = f"DELETE_{current_name}"
        client.patch(f"/v2.0/projects/{project_id}", json={"name": new_name})

    return {"markedForDeletion": True, "projectId": project_id, "name": new_name}


def _find_locale_id(resource_node: dict[str, Any]) -> Optional[str]:
    """`resource_node` is a project- or package-graph node: {"resources": [...]}.
    Returns the (primary) locale's mongo `_id` - despite the "packageLocaleId"/
    "agentLocaleId" names, `POST .../merge` validates both as `mongo-id`, i.e.
    it wants each locale's local `_id` in its own graph, not its portable
    UUID `referenceId` (confirmed against a live tenant - the API rejects a
    referenceId in either field with a 400)."""
    for resource in resource_node.get("resources", []):
        if resource.get("type") == "locale" and resource.get("properties", {}).get("primary", True):
            return resource.get("_id")
    return None


def _find_flow_by_name(creds: CognigyCreds, project_id: str, name: str) -> tuple[Optional[str], Optional[str]]:
    graph = manage_packages.list_exportable(creds, project_id)["graph"]
    project_node = graph.get(project_id, {})
    for resource in project_node.get("resources", []):
        if resource.get("type") == "flow" and resource.get("name") == name:
            return resource.get("_id"), resource.get("name")
    return None, None


def _build_template_zip() -> Path:
    """Zip server/templates/environment_setup/ into a temp .zip suitable for
    manage_packages.upload_and_inspect. Caller is responsible for deleting it."""
    fd, path_str = tempfile.mkstemp(suffix=".zip", prefix="environment-setup-template-")
    os.close(fd)
    out_path = Path(path_str)

    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in TEMPLATE_DIR.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=file_path.relative_to(TEMPLATE_DIR).as_posix())

    return out_path
