# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code plugin that connects to Cognigy.AI. It has two independently
deployed parts, and confusing them is the most common mistake to avoid:

- **`server/`** — a stateless FastMCP app exposed over Streamable HTTP,
  deployed once centrally (Docker, on a Linux host, with nginx bundled inside
  the same container for TLS termination). It holds **no** Cognigy
  credentials of its own.
- **`plugin/`** — the actual Claude Code plugin installed by end users. It is
  deliberately minimal: a manifest, an `.mcp.json` pointing at the deployed
  server, a `/cognigy-setup` command, and skills. No Python and no install
  step run on the end user's machine.

Do not add a local Python MCP server back into `plugin/` — that was the
original design and was deliberately replaced (see git history on
`feature/cognigy-plugin-initial`) once it was decided the server would be
centrally hosted, not spawned per-user.

## Credential model (read before touching auth-adjacent code)

The server is a **stateless, pass-through proxy**. Every tool call must carry
the caller's own Cognigy API base URL and API key as request headers:

```
X-Cognigy-Base-Url: https://api-trial.cognigy.ai
X-Cognigy-Api-Key:  <caller's Cognigy API key>
```

`server/cognigy_client.py`'s `CognigyClient` requires both as constructor
args (no local-file or env-var fallback — that fallback existed in an earlier
iteration and was removed on purpose). `server/app.py`'s `_creds(ctx)` helper
extracts them via `ctx.request_context.request.headers` (this is how you get
the raw Starlette request out of a FastMCP `Context` in a Streamable HTTP
tool — not obvious from the SDK docs, confirmed by reading
`mcp/server/streamable_http.py`'s `ServerMessageMetadata(request_context=request)`).
Every tool function in `server/app.py` takes a `ctx: Context` parameter for
this reason; every function in `server/tools/*.py` takes a `creds:
CognigyCreds` (a `NamedTuple(base_url, api_key)`) as its first argument.

The plugin's `plugin/.mcp.json` sends these headers on every request; the
`/cognigy-setup` command (`plugin/commands/cognigy-setup.md`) edits that file
directly (via Claude's own Edit tool) rather than running any script. Real
credential values must never be committed — the file lives with placeholder
values in the repo and gets real values written locally per user.

This passthrough design was a deliberate simplicity/security tradeoff
(discussed in-session): a real Cognigy key ends up in plaintext in every
user's local `.mcp.json`. A token-indirection layer (server issues its own
revocable token, maps it server-side to real Cognigy creds) was identified as
the natural next hardening step but is not yet built.

## Adding a new Cognigy tool

Follow the existing three-tool-area pattern exactly:

1. Add the actual Cognigy REST logic to a new or existing module in
   `server/tools/`, following the shape in `manage_snapshots.py` /
   `manage_packages.py` / `manage_settings.py`: every public function takes
   `creds: CognigyCreds` first, uses `with CognigyClient(*creds) as client:`,
   and returns a plain `dict[str, Any]`.
2. Register it as an `@mcp.tool()` in `server/app.py`, taking a `ctx: Context`
   parameter and calling `_creds(ctx)` to get credentials — `ctx` is excluded
   from the tool's public JSON schema automatically by FastMCP, do not try to
   hide it another way.
3. If the operation is async on the Cognigy side (returns a task), use
   `CognigyClient.wait_for_task` and also expose a `read_<area>_task` tool
   (see `read_snapshot_task`/`read_package_task`) — tasks can outlive the
   internal wait timeout and need to be pollable independently. This was
   missed once already (the tool functions existed in `tools/*.py` but were
   never wired into `app.py`) — don't repeat that gap.
4. Add a matching `plugin/skills/<name>/SKILL.md` (frontmatter `name` +
   `description`, workflow guidance, an `## Operations` section listing
   required/optional params per tool) and list it in
   `plugin/.claude-plugin/plugin.json`'s `skills` array.
5. Cognigy's REST API mixes two path prefixes on the same host: older
   resources (snapshots) live under `/v2.0/...`, newer ones (packages,
   project settings, tasks) under `/new/v2.0/...`. Check which an endpoint
   uses before assuming.
6. Several Cognigy list endpoints return HAL-style responses
   (`_embedded.<resource>` + `_links`), not a flat `items` array — this
   was a real bug once (`manage_settings._find_speech_connection` originally
   read `.get("items", [])`, silently finding nothing). When parsing a new
   list response, check both shapes or check the real response first.
7. Cognigy resource names (e.g. snapshot names) only allow
   `[A-Za-z0-9_-]` — spaces/colons are rejected with a 400. See
   `manage_snapshots._sanitize_resource_name` if you're generating a name
   rather than taking one from the user verbatim.

## Local development / testing

There's no test suite or lint config in this repo yet. To iterate on server
code locally without Docker:

```
cd server
python -m venv .venv && source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py --host 127.0.0.1 --port 8000
```

To exercise a tool end-to-end against a running server, use a real MCP client
rather than curl (Streamable HTTP is a JSON-RPC-over-HTTP protocol, not plain
REST) — the `mcp` Python package's `mcp.client.streamable_http.streamablehttp_client`
plus `mcp.ClientSession` is the pattern used during development of this repo:

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    headers = {"X-Cognigy-Base-Url": "...", "X-Cognigy-Api-Key": "..."}
    async with streamablehttp_client("http://127.0.0.1:8000/mcp", headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("list_snapshots", {"project_id": "..."})
            print(result.content)

asyncio.run(main())
```

Sanity checks worth running after any change to `server/app.py`:

```
python -m py_compile server/app.py server/cognigy_client.py server/tools/*.py
python -c "import app, asyncio; print([t.name for t in asyncio.run(app.mcp.list_tools())])"
```

## Docker / nginx deployment

`server/Dockerfile` builds a single image running **both** nginx and uvicorn
via `supervisord` (`server/supervisord.conf`) — nginx (root, binds 80/443)
terminates TLS and reverse-proxies `/mcp` to uvicorn on loopback
(`127.0.0.1:8000`, run as the unprivileged `mcp` user). `server/entrypoint.sh`
renders `server/nginx/default.conf.template` with the `SERVER_NAME` env var
via `envsubst`, fails fast if `/etc/nginx/certs/{fullchain,privkey}.pem` are
missing, then execs supervisord.

`docker-compose.yml` (repo root) builds/runs this, publishing 80/443 and
mounting `nginx/certs/` (repo root, gitignored — real certs never committed)
read-only into the container. This intentionally does *not* rely on or
configure any nginx already running on the host — TLS termination is fully
self-contained in the container. See `server/README.md` for the full
deployment walkthrough.

## Repo-editing gotcha

This repo is edited from Windows but always deployed on Linux. `.gitattributes`
forces LF line endings for `*.sh`, `*.py`, `*.conf`, `*.template`, and
`Dockerfile` — a CRLF-corrupted shebang in `entrypoint.sh` would silently
break container startup. If you add a new shell script or similarly
sensitive text file, add its extension to `.gitattributes` and run
`git add --renormalize .` rather than assuming Git handled it.
