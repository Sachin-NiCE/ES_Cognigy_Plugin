# cognigy plugin (client side)

Minimal Claude Code plugin: no local Python, no install step. It talks to a
centrally hosted MCP server (see `../server/`) over Streamable HTTP.

- `.claude-plugin/plugin.json` — manifest
- `.mcp.json` — points at the hosted server; `headers` carry the caller's
  Cognigy credentials (filled in by `/cognigy-setup`, never committed with
  real values)
- `commands/cognigy-setup.md` — the `/cognigy-setup` command
- `skills/` — one per feature area (snapshot-backups, package-management,
  project-settings); see `skills/README.md`
- `agents/` — empty for now; see `agents/README.md` for how to wire a
  subagent into `plugin.json` when we add one
