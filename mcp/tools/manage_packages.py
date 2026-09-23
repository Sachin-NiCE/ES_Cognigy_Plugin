"""manage_packages: export/import Cognigy package .zip files.

Endpoints (see mcp/cognigy_client.py for prefix/auth conventions):
    GET  /new/v2.0/projects/{projectId}/graph?packages=false&dependencies=true
         -> project resource graph, used to derive exportable resources
            and to resolve dependencies before export
    POST /new/v2.0/packages                     body: {projectId, name, description, resourceIds}
    GET  /new/v2.0/packages/{packageId}          -> package metadata
    POST /new/v2.0/packages/{packageId}/downloadlink  -> {downloadLink}
    POST /new/v2.0/packages/upload                multipart: file + projectId
    GET  /new/v2.0/projects/{projectId}/graph?packages=true
         -> merged with the package's own graph entry to build an import preview
    POST /new/v2.0/packages/{packageId}/merge    body: {resourceIds, strategies, localeMapping}

Async ops (export, upload, merge) return a task, polled via
CognigyClient.wait_for_task.

TODO (unverified against a live tenant): dedicated list/delete package
endpoints (likely GET/DELETE /new/v2.0/packages) were not exercised in the
reference implementation we studied - confirm paths before relying on them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from cognigy_client import CognigyClient


def list_exportable(project_id: str) -> dict[str, Any]:
    graph = _project_graph(project_id, packages=False, dependencies=True)
    return {"projectId": project_id, "graph": graph}


def export_package(
    project_id: str,
    resource_ids: list[str],
    name: str,
    description: Optional[str] = None,
    wait_for_completion: bool = True,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    body = {
        "projectId": project_id,
        "name": name,
        "description": description or "",
        "resourceIds": resource_ids,
    }
    with CognigyClient() as client:
        task = client.post("/new/v2.0/packages", json=body)
        if not wait_for_completion:
            return {"task": task}
        final = client.wait_for_task(task, project_id, timeout_s=timeout_s)
        package_id = (final.get("data") or {}).get("packageId")
        return {"task": final, "packageId": package_id}


def download_package(project_id: str, package_id: str, output_path: str) -> dict[str, Any]:
    with CognigyClient() as client:
        metadata = client.get(f"/new/v2.0/packages/{package_id}")
        link_resp = client.post(f"/new/v2.0/packages/{package_id}/downloadlink")
        download_link = link_resp.get("downloadLink")
        if not download_link:
            raise RuntimeError("Cognigy did not return a downloadLink for this package.")

        out = Path(output_path)
        if out.is_dir():
            filename = f"{metadata.get('name', package_id)}.zip"
            out = out / filename
        out.parent.mkdir(parents=True, exist_ok=True)

        out.write_bytes(client.get_absolute_bytes(download_link))

    return {"packageId": package_id, "savedTo": str(out.resolve()), "fileUri": out.resolve().as_uri()}


def upload_and_inspect(
    project_id: str,
    file_path: str,
    wait_for_completion: bool = True,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Package file not found: {file_path}")

    with CognigyClient() as client:
        with open(path, "rb") as f:
            task = client.post(
                "/new/v2.0/packages/upload",
                data={"projectId": project_id},
                files={"file": (path.name, f, "application/zip")},
            )
        if wait_for_completion:
            task = client.wait_for_task(task, project_id, timeout_s=timeout_s)

        package_id = (task.get("data") or {}).get("packageId")
        if not package_id:
            return {"task": task}
        return inspect_package(project_id, package_id)


def inspect_package(project_id: str, package_id: str) -> dict[str, Any]:
    with CognigyClient() as client:
        project_graph = _project_graph(project_id, packages=True, dependencies=True, _client=client)
        package_node = project_graph.get(package_id) or {}
        project_node = project_graph.get(project_id) or {}
    return {
        "packageId": package_id,
        "projectId": project_id,
        "packageResources": package_node,
        "projectResources": project_node,
        "note": (
            "Preview built by diffing the package's and project's resource graphs. "
            "Select resources to import and pass them as `resources` to import_package."
        ),
    }


def import_package(
    project_id: str,
    package_id: str,
    resources: Optional[list[dict[str, Any]]] = None,
    locale_mapping: Optional[list[dict[str, str]]] = None,
    wait_for_completion: bool = True,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    """UI-parity defaults: knowledgeStore resources default to strategy
    "replace", everything else to "re-identify"; autoRename is always True.
    """
    resource_ids: list[str] = []
    strategies: list[dict[str, Any]] = []
    for r in resources or []:
        if r.get("import", True) is False:
            continue
        rid = r["id"]
        resource_ids.append(rid)
        strategies.append(
            {
                "_id": rid,
                "autoRename": True,
                "identityConflictStrategy": r.get("strategy", "re-identify"),
            }
        )

    body: dict[str, Any] = {"resourceIds": resource_ids, "strategies": strategies}
    if locale_mapping:
        body["localeMapping"] = locale_mapping

    with CognigyClient() as client:
        task = client.post(f"/new/v2.0/packages/{package_id}/merge", json=body)
        if not wait_for_completion:
            return {"task": task}
        final = client.wait_for_task(task, project_id, timeout_s=timeout_s)
        return {"task": final, "imported": final.get("status") == "done"}


def read_task(project_id: str, task_id: str) -> dict[str, Any]:
    with CognigyClient() as client:
        return client.get_task(task_id, project_id)


def _project_graph(
    project_id: str,
    packages: bool,
    dependencies: bool,
    _client: Optional[CognigyClient] = None,
) -> dict[str, Any]:
    def _fetch(client: CognigyClient) -> dict[str, Any]:
        return client.get(
            f"/new/v2.0/projects/{project_id}/graph",
            params={"packages": str(packages).lower(), "dependencies": str(dependencies).lower()},
        )

    if _client is not None:
        return _fetch(_client)
    with CognigyClient() as client:
        return _fetch(client)
