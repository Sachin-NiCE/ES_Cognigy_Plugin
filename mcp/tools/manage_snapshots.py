"""manage_snapshots: project backup/restore via Cognigy Snapshots.

A Snapshot is an immutable, PROJECT-WIDE copy (agents, flows, connections,
LLMs, lexicons, extensions, functions, playbooks, locales). It does NOT
capture endpoints, Knowledge AI content, intent trainer data, analytics, or
logs — say so before creating or restoring.

Endpoints (see mcp/cognigy_client.py for prefix/auth conventions):
    GET    /v2.0/snapshots?projectId=...
    POST   /v2.0/snapshots                body: {projectId, name, description}
    POST   /v2.0/snapshots/{id}/restore   body: {projectId}
    DELETE /v2.0/snapshots/{id}
Async ops return a task, polled via CognigyClient.wait_for_task.

TODO (unverified against a live tenant): GET /v2.0/snapshots/{id}/resources
was found only via search, not confirmed in official docs.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from cognigy_client import CognigyClient

_NON_RESOURCE_NAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")


def _sanitize_resource_name(value: str) -> str:
    """Cognigy resource names only allow [A-Za-z0-9_-]; collapse everything else to '-'."""
    sanitized = _NON_RESOURCE_NAME_CHARS.sub("-", value).strip("-")
    return sanitized or "snapshot"


def _default_snapshot_name(client: CognigyClient, project_id: str) -> str:
    """<ProjectName>-<Mon DD>-<HHMM> (UTC), e.g. "Assistant-Agent-Sep22-1405"."""
    project = client.get(f"/v2.0/projects/{project_id}")
    project_name = (project or {}).get("name", project_id)
    timestamp = datetime.now(timezone.utc).strftime("%b%d-%H%M")
    return _sanitize_resource_name(f"{project_name}-{timestamp}")


def list_snapshots(
    project_id: str,
    limit: int = 25,
    skip: int = 0,
    name_filter: Optional[str] = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"projectId": project_id, "limit": limit, "skip": skip}
    if name_filter:
        params["filter"] = name_filter
    with CognigyClient() as client:
        return client.get("/v2.0/snapshots", params=params)


def create_snapshot(
    project_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    wait_for_completion: bool = True,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    """If `name` is omitted, it defaults to "<ProjectName>-<Mon DD>-<HH:MM>" (UTC)."""
    with CognigyClient() as client:
        if not name:
            name = _default_snapshot_name(client, project_id)
        body = {"projectId": project_id, "name": name, "description": description or ""}
        task = client.post("/v2.0/snapshots", json=body)
        if not wait_for_completion:
            return {"task": task}
        final = client.wait_for_task(task, project_id, timeout_s=timeout_s)
        return {"task": final, "created": final.get("status") == "done"}


def restore_snapshot(
    project_id: str,
    snapshot_id: str,
    confirm: bool = False,
    wait_for_completion: bool = True,
    timeout_s: float = 600.0,
) -> dict[str, Any]:
    """Restore is destructive: ALL current project resources are replaced by
    the snapshot's contents, and resource ids change. Without confirm=True
    this returns a preflight warning only and performs no action.
    """
    if not confirm:
        return {
            "preflight": True,
            "warning": (
                "Restoring will DELETE and recreate every agent, flow, connection, "
                "LLM, lexicon, extension, function, playbook and locale currently in "
                "this project, replacing them with the snapshot's contents. Resource "
                "ids will change. Endpoints, Knowledge AI content, intent trainer data, "
                "analytics and logs are NOT part of the snapshot and will not be restored. "
                "Re-run with confirm=True to proceed."
            ),
            "projectId": project_id,
            "snapshotId": snapshot_id,
        }

    with CognigyClient() as client:
        task = client.post(f"/v2.0/snapshots/{snapshot_id}/restore", json={"projectId": project_id})
        if not wait_for_completion:
            return {"task": task}
        final = client.wait_for_task(task, project_id, timeout_s=timeout_s)
        return {"task": final, "restored": final.get("status") == "done"}


def delete_snapshot(project_id: str, snapshot_id: str) -> dict[str, Any]:
    with CognigyClient() as client:
        client.delete(f"/v2.0/snapshots/{snapshot_id}", params={"projectId": project_id})
    return {"deleted": True, "snapshotId": snapshot_id}


def read_task(project_id: str, task_id: str) -> dict[str, Any]:
    with CognigyClient() as client:
        return client.get_task(task_id, project_id)
