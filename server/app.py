#!/usr/bin/env python3
"""Cognigy MCP server — deployed centrally (e.g. on a shared Linux host),
exposed over Streamable HTTP.

STATELESS / PASS-THROUGH DESIGN: this server holds no Cognigy credentials of
its own. Every tool call must carry the caller's own Cognigy API base URL and
API key as request headers:

    X-Cognigy-Base-Url: https://api-trial.cognigy.ai
    X-Cognigy-Api-Key:  <the caller's Cognigy API key>

The Claude Code plugin's .mcp.json sends these on every request (see
plugin/.claude-plugin/plugin.json and plugin/commands/cognigy-setup.md).
This server never persists them to disk or logs them.

Run directly for local testing:
    python app.py --host 0.0.0.0 --port 8000

For production, run under an ASGI server (e.g. uvicorn) behind TLS:
    uvicorn app:app --host 0.0.0.0 --port 8000
See README.md in this folder for a systemd unit + reverse-proxy example.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mcp.server.fastmcp import Context, FastMCP

from cognigy_client import CognigyCreds
from tools import manage_packages, manage_settings, manage_snapshots

mcp = FastMCP("cognigy", stateless_http=True)

BASE_URL_HEADER = "x-cognigy-base-url"
API_KEY_HEADER = "x-cognigy-api-key"


def _creds(ctx: Context) -> CognigyCreds:
    request = ctx.request_context.request
    if request is None:
        raise RuntimeError("No HTTP request context available (unexpected transport).")

    base_url = request.headers.get(BASE_URL_HEADER)
    api_key = request.headers.get(API_KEY_HEADER)
    if not base_url or not api_key:
        raise ValueError(
            f"Missing credentials. This server requires the '{BASE_URL_HEADER}' and "
            f"'{API_KEY_HEADER}' headers on every request. Run /cognigy-setup in "
            "Claude Code to configure them."
        )
    return CognigyCreds(base_url=base_url, api_key=api_key)


# ---------------------------------------------------------------------------
# Snapshots (project backup/restore)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_snapshots(
    project_id: str,
    ctx: Context,
    limit: int = 25,
    skip: int = 0,
    name_filter: Optional[str] = None,
) -> dict[str, Any]:
    """List a project's Cognigy Snapshots (immutable, project-wide backups)."""
    return manage_snapshots.list_snapshots(_creds(ctx), project_id, limit=limit, skip=skip, name_filter=name_filter)


@mcp.tool()
def create_snapshot(
    project_id: str,
    ctx: Context,
    name: Optional[str] = None,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Create a backup Snapshot of a project (agents, flows, connections, LLMs,
    lexicons, extensions, functions, playbooks, locales). Does NOT capture
    endpoints, Knowledge AI content, intent trainer data, analytics, or logs.
    If name is omitted, it defaults to "<ProjectName>-<Mon DD>-<HHMM>" (UTC)."""
    return manage_snapshots.create_snapshot(_creds(ctx), project_id, name=name, description=description)


@mcp.tool()
def restore_snapshot(project_id: str, snapshot_id: str, ctx: Context, confirm: bool = False) -> dict[str, Any]:
    """Restore a project from a Snapshot. DESTRUCTIVE: replaces every current
    agent/flow/connection/LLM/etc. in the project and changes resource ids.
    Call with confirm=False first to see the preflight warning; only pass
    confirm=True after the user has explicitly agreed."""
    return manage_snapshots.restore_snapshot(_creds(ctx), project_id, snapshot_id, confirm=confirm)


@mcp.tool()
def delete_snapshot(project_id: str, snapshot_id: str, ctx: Context) -> dict[str, Any]:
    """Delete a Cognigy Snapshot."""
    return manage_snapshots.delete_snapshot(_creds(ctx), project_id, snapshot_id)


@mcp.tool()
def read_snapshot_task(project_id: str, task_id: str, ctx: Context) -> dict[str, Any]:
    """Poll a create/restore/delete Snapshot task that outlived its wait timeout."""
    return manage_snapshots.read_task(_creds(ctx), project_id, task_id)


# ---------------------------------------------------------------------------
# Packages (export/import)
# ---------------------------------------------------------------------------


@mcp.tool()
def list_exportable_resources(project_id: str, ctx: Context) -> dict[str, Any]:
    """List a project's resource graph to identify what can be packaged for export."""
    return manage_packages.list_exportable(_creds(ctx), project_id)


@mcp.tool()
def export_package(
    project_id: str,
    resource_ids: list[str],
    name: str,
    ctx: Context,
    description: Optional[str] = None,
) -> dict[str, Any]:
    """Export selected project resources (and their dependencies) into a new Cognigy package."""
    return manage_packages.export_package(_creds(ctx), project_id, resource_ids, name, description=description)


@mcp.tool()
def download_package(project_id: str, package_id: str, output_path: str, ctx: Context) -> dict[str, Any]:
    """Download a Cognigy package .zip. NOTE: output_path is a path on THIS
    SERVER's filesystem (this MCP server runs remotely), not the end user's machine."""
    return manage_packages.download_package(_creds(ctx), project_id, package_id, output_path)


@mcp.tool()
def upload_and_inspect_package(project_id: str, file_path: str, ctx: Context) -> dict[str, Any]:
    """Upload a package .zip and return an import preview of its resources.
    NOTE: file_path is a path on THIS SERVER's filesystem, not the end user's machine."""
    return manage_packages.upload_and_inspect(_creds(ctx), project_id, file_path)


@mcp.tool()
def inspect_package(project_id: str, package_id: str, ctx: Context) -> dict[str, Any]:
    """Return the import preview for an already-uploaded package."""
    return manage_packages.inspect_package(_creds(ctx), project_id, package_id)


@mcp.tool()
def import_package(
    project_id: str,
    package_id: str,
    ctx: Context,
    resources: Optional[list[dict[str, Any]]] = None,
    locale_mapping: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """Import selected resources from an uploaded package into the project.
    `resources` items: {id, import (bool, default True), strategy ("replace" | "re-identify")}.
    Knowledge stores default to "replace"; everything else to "re-identify"."""
    return manage_packages.import_package(
        _creds(ctx), project_id, package_id, resources=resources, locale_mapping=locale_mapping
    )


@mcp.tool()
def read_package_task(project_id: str, task_id: str, ctx: Context) -> dict[str, Any]:
    """Poll an export/upload/import Package task that outlived its wait timeout."""
    return manage_packages.read_task(_creds(ctx), project_id, task_id)


# ---------------------------------------------------------------------------
# Project settings (voice preview, Knowledge AI)
# ---------------------------------------------------------------------------


@mcp.tool()
def set_voice_preview(project_id: str, provider: str, ctx: Context, connection_id: Optional[str] = None) -> dict[str, Any]:
    """Configure the speech provider used for Voice Preview in a project.
    Supported providers: microsoft, google, aws, deepgram, elevenlabs.
    If connection_id is omitted, an existing matching Connection is auto-detected."""
    return manage_settings.set_voice_preview(_creds(ctx), project_id, provider, connection_id=connection_id)


@mcp.tool()
def set_knowledge_ai(
    project_id: str,
    ctx: Context,
    knowledge_search_model_id: Optional[str] = None,
    answer_extraction_model_id: Optional[str] = None,
    content_parser: Optional[str] = None,
    azure_di_connection_id: Optional[str] = None,
) -> dict[str, Any]:
    """Configure a project's Knowledge AI settings: the Knowledge Search and
    Answer Extraction LLMs (must be llm_model ids from the SAME project) and
    the content parser (default | legacy | azure). azure_di_connection_id is
    required when content_parser is "azure"."""
    return manage_settings.set_knowledge_ai(
        _creds(ctx),
        project_id,
        knowledge_search_model_id=knowledge_search_model_id,
        answer_extraction_model_id=answer_extraction_model_id,
        content_parser=content_parser,
        azure_di_connection_id=azure_di_connection_id,
    )


# ASGI app for `uvicorn app:app` in production.
app = mcp.streamable_http_app()


if __name__ == "__main__":
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="Run the Cognigy MCP server (dev mode).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    uvicorn.run(app, host=args.host, port=args.port)
