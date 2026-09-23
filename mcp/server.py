#!/usr/bin/env python3
"""Cognigy MCP server for Claude Code.

Reads connection settings (API base URL + API key) written by
`/cognigy-setup` (see cognigy_config.py). Functional tools beyond the
connection check are added here later.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import httpx
from mcp.server.fastmcp import FastMCP

from cognigy_config import get_api_key, get_base_url, is_configured
from tools import manage_packages, manage_settings, manage_snapshots

mcp = FastMCP("cognigy")


def _client() -> httpx.Client:
    base_url = get_base_url()
    api_key = get_api_key()
    if not base_url or not api_key:
        raise RuntimeError(
            "Cognigy is not configured. Ask the user to run /cognigy-setup "
            "to set the API base URL and API key."
        )
    return httpx.Client(
        base_url=base_url,
        headers={"X-API-Key": api_key},
        timeout=30.0,
    )


@mcp.tool()
def cognigy_connection_status() -> dict[str, Any]:
    """Report whether the plugin has stored Cognigy credentials and, if so, whether they work."""
    if not is_configured():
        return {"configured": False, "message": "No API base URL / API key stored. Run /cognigy-setup."}

    base_url = get_base_url()
    try:
        with _client() as client:
            resp = client.get("/v2.0/projects", params={"limit": 1})
        return {
            "configured": True,
            "base_url": base_url,
            "reachable": resp.status_code < 500,
            "status_code": resp.status_code,
            "authenticated": resp.status_code not in (401, 403),
        }
    except httpx.HTTPError as exc:
        return {"configured": True, "base_url": base_url, "reachable": False, "error": str(exc)}



# ---------------------------------------------------------------------------
# Snapshots (project backup/restore)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_snapshots(project_id: str, limit: int = 25, skip: int = 0, name_filter: str | None = None) -> dict[str, Any]:
    """List a project's Cognigy Snapshots (immutable, project-wide backups)."""
    return manage_snapshots.list_snapshots(project_id, limit=limit, skip=skip, name_filter=name_filter)


@mcp.tool()
def create_snapshot(project_id: str, name: str | None = None, description: str | None = None) -> dict[str, Any]:
    """Create a backup Snapshot of a project (agents, flows, connections, LLMs,
    lexicons, extensions, functions, playbooks, locales). Does NOT capture
    endpoints, Knowledge AI content, intent trainer data, analytics, or logs.
    If name is omitted, it defaults to "<ProjectName>-<Mon DD>-<HH:MM>" (UTC)."""
    return manage_snapshots.create_snapshot(project_id, name=name, description=description)


@mcp.tool()
def restore_snapshot(project_id: str, snapshot_id: str, confirm: bool = False) -> dict[str, Any]:
    """Restore a project from a Snapshot. DESTRUCTIVE: replaces every current
    agent/flow/connection/LLM/etc. in the project and changes resource ids.
    Call with confirm=False first to see the preflight warning; only pass
    confirm=True after the user has explicitly agreed."""
    return manage_snapshots.restore_snapshot(project_id, snapshot_id, confirm=confirm)


@mcp.tool()
def delete_snapshot(project_id: str, snapshot_id: str) -> dict[str, Any]:
    """Delete a Cognigy Snapshot."""
    return manage_snapshots.delete_snapshot(project_id, snapshot_id)


# ---------------------------------------------------------------------------
# Packages (export/import)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_exportable_resources(project_id: str) -> dict[str, Any]:
    """List a project's resource graph to identify what can be packaged for export."""
    return manage_packages.list_exportable(project_id)


@mcp.tool()
def export_package(
    project_id: str,
    resource_ids: list[str],
    name: str,
    description: str | None = None,
) -> dict[str, Any]:
    """Export selected project resources (and their dependencies) into a new Cognigy package."""
    return manage_packages.export_package(project_id, resource_ids, name, description=description)


@mcp.tool()
def download_package(project_id: str, package_id: str, output_path: str) -> dict[str, Any]:
    """Download a Cognigy package .zip to a local path."""
    return manage_packages.download_package(project_id, package_id, output_path)


@mcp.tool()
def upload_and_inspect_package(project_id: str, file_path: str) -> dict[str, Any]:
    """Upload a local package .zip and return an import preview of its resources."""
    return manage_packages.upload_and_inspect(project_id, file_path)


@mcp.tool()
def inspect_package(project_id: str, package_id: str) -> dict[str, Any]:
    """Return the import preview for an already-uploaded package."""
    return manage_packages.inspect_package(project_id, package_id)


@mcp.tool()
def import_package(
    project_id: str,
    package_id: str,
    resources: list[dict[str, Any]] | None = None,
    locale_mapping: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Import selected resources from an uploaded package into the project.
    `resources` items: {id, import (bool, default True), strategy ("replace" | "re-identify")}.
    Knowledge stores default to "replace"; everything else to "re-identify"."""
    return manage_packages.import_package(project_id, package_id, resources=resources, locale_mapping=locale_mapping)


# ---------------------------------------------------------------------------
# Project settings (voice preview, Knowledge AI)
# ---------------------------------------------------------------------------


@mcp.tool()
def set_voice_preview(project_id: str, provider: str, connection_id: str | None = None) -> dict[str, Any]:
    """Configure the speech provider used for Voice Preview in a project.
    Supported providers: microsoft, google, aws, deepgram, elevenlabs.
    If connection_id is omitted, an existing matching Connection is auto-detected."""
    return manage_settings.set_voice_preview(project_id, provider, connection_id=connection_id)


@mcp.tool()
def set_knowledge_ai(
    project_id: str,
    knowledge_search_model_id: str | None = None,
    answer_extraction_model_id: str | None = None,
    content_parser: str | None = None,
    azure_di_connection_id: str | None = None,
) -> dict[str, Any]:
    """Configure a project's Knowledge AI settings: the Knowledge Search and
    Answer Extraction LLMs (must be llm_model ids from the SAME project) and
    the content parser (default | legacy | azure). azure_di_connection_id is
    required when content_parser is "azure"."""
    return manage_settings.set_knowledge_ai(
        project_id,
        knowledge_search_model_id=knowledge_search_model_id,
        answer_extraction_model_id=answer_extraction_model_id,
        content_parser=content_parser,
        azure_di_connection_id=azure_di_connection_id,
    )


if __name__ == "__main__":
    mcp.run()
