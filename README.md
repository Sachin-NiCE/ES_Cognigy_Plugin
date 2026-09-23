# ES Cognigy Claude Plugin

A Claude Code plugin (Python) that connects to a Cognigy.AI instance.

## Setup

1. Install dependencies for the bundled MCP server:
   ```
   pip install -r requirements.txt
   ```
2. In Claude Code, run:
   ```
   /cognigy-setup
   ```
   and provide your Cognigy API base URL (e.g. `https://api-trial.cognigy.ai`) and API key.

Credentials are stored locally at `~/.claude/cognigy-plugin/config.json` (owner-only permissions),
never committed to this repo. Re-run `/cognigy-setup` anytime to change the URL or key, or run:
```
python scripts/configure.py --show
```
to check current configuration without exposing the key.

## What's here

- `.claude-plugin/plugin.json` — plugin manifest
- `.mcp.json` — registers the Python MCP server (`mcp/server.py`)
- `mcp/cognigy_config.py` — shared config read/write helpers
- `scripts/configure.py` — CLI used by `/cognigy-setup` to store credentials
- `hooks/` — SessionStart hook that reminds the user to run setup if unconfigured
- `commands/cognigy-setup.md` — the `/cognigy-setup` slash command

## What's next

Functional Cognigy tools (projects, agents, flows, etc.) will be added to `mcp/server.py` next —
to be scoped separately.
