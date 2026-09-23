# ES Cognigy Claude Plugin

A Claude Code plugin (Python) that connects to a Cognigy.AI instance — manage
project snapshots (backup/restore), packages (export/import), and project
settings (voice preview, Knowledge AI) directly from Claude.

## Installation

**Two steps.**

### Step 1 — run the installer

The installer checks for Python 3.10+ and installs it if it's missing, then
creates an isolated virtual environment for the plugin's dependencies so
nothing is installed into your system/global Python.

**macOS / Linux:**
```
bash install.sh
```
If Python isn't found, it installs one via Homebrew (macOS) or apt/dnf/yum
(Linux, will prompt for `sudo`). If none of those package managers are
available, it prints a link to https://www.python.org/downloads/ and stops.

**Windows (PowerShell):**
```
powershell -ExecutionPolicy Bypass -File install.ps1
```
If Python isn't found, it installs one via `winget` in user scope (no admin
required). If `winget` isn't available, it prints a link to
https://www.python.org/downloads/ and stops.

Either script then:
1. Creates `.venv/` in this folder and installs `requirements.txt` into it
2. Rewrites `.mcp.json` to run the MCP server with that venv's interpreter
   (so it never depends on a bare `python`/`python3` being on your PATH)
3. Prompts you for your **Cognigy API base URL** and **API key**

### Step 2 — install the plugin in Claude Code

```
/plugin marketplace add <path to this folder>
/plugin install cognigy@es-cognigy-plugin-dev
```
Then restart Claude Code.

### Updating credentials later

Re-run the installer, or from inside Claude Code run `/cognigy-setup`, or
directly:
```
.venv/bin/python scripts/configure.py --show    # macOS/Linux
.venv\Scripts\python.exe scripts\configure.py --show   # Windows
```
Credentials are stored locally at `~/.claude/cognigy-plugin/config.json`
(owner-only permissions), never committed to this repo.

> **Note:** the installer rewrites `.mcp.json` with an absolute, machine-local
> path to `.venv`'s interpreter. Don't commit that change — it's specific to
> your machine. If you pull updates and want a clean `.mcp.json`, run
> `git checkout .mcp.json` and re-run the installer.

## What's here

- `install.sh` / `install.ps1` — installers (Python bootstrap + venv + config)
- `.claude-plugin/plugin.json` — plugin manifest
- `.mcp.json` — registers the Python MCP server (`mcp/server.py`)
- `mcp/server.py` — the MCP server; exposes the tools below
- `mcp/cognigy_client.py` — shared Cognigy REST client (auth, async task polling)
- `mcp/cognigy_config.py` — shared config read/write helpers
- `mcp/tools/manage_snapshots.py` — project backup/restore
- `mcp/tools/manage_packages.py` — package export/import
- `mcp/tools/manage_settings.py` — voice preview & Knowledge AI settings
- `scripts/configure.py` — CLI used by `/cognigy-setup` to store credentials
- `scripts/write_mcp_config.py` — used by the installers to wire up `.mcp.json`
- `hooks/` — SessionStart hook that reminds the user to run setup if unconfigured
- `commands/cognigy-setup.md` — the `/cognigy-setup` slash command

## What's next

Additional Cognigy tools (agent creation, tools/flow-nodes, knowledge/RAG,
voice gateway, etc.) will be added to `mcp/server.py` next — to be scoped
separately.
