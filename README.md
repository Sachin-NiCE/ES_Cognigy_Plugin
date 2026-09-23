# ES Cognigy Claude Plugin

Connects Claude Code to Cognigy.AI — manage project snapshots (backup/restore),
packages (export/import), and project settings (voice preview, Knowledge AI)
directly from Claude.

The project has two parts:

- **`server/`** — a stateless MCP server exposed over Streamable HTTP, meant
  to be deployed once on a shared host (e.g. a Linux VM). It holds no Cognigy
  credentials itself; every request carries the caller's own Cognigy API base
  URL and key as headers. See `server/README.md` for deployment instructions.
- **`plugin/`** — the actual Claude Code plugin, kept deliberately minimal:
  a manifest, an `.mcp.json` pointing at your deployed server, and a
  `/cognigy-setup` command. No Python or install step is needed on the end
  user's machine at all.

## For end users: installing the plugin

### Step 1 — add the marketplace and install

```
/plugin marketplace add <path or URL to this repo>
/plugin install cognigy@es-cognigy-plugin-dev
```
Then restart Claude Code.

### Step 2 — point it at your Cognigy MCP server

```
/cognigy-setup
```
You'll be asked for:
- the Cognigy MCP server URL (ask your admin — see `server/README.md`)
- your Cognigy API base URL (e.g. `https://api-trial.cognigy.ai`)
- your Cognigy API key

This writes those values into `plugin/.mcp.json` on your machine (not
committed back to git). Restart Claude Code / run `/mcp` afterwards to
reconnect.

## For admins: deploying the server

See `server/README.md` — run it in Docker (`docker compose up`) and put your
existing nginx (or other TLS-terminating reverse proxy) in front of it using
`nginx/cognigy-mcp.conf`. Give the resulting URL to your users for step 2
above.

## Repo layout

```
plugin/
  .claude-plugin/plugin.json   — plugin manifest
  .mcp.json                    — points at the hosted server; headers carry
                                  Cognigy credentials (filled in by /cognigy-setup)
  commands/cognigy-setup.md    — the /cognigy-setup command
  skills/, agents/              — empty for now; see plugin/README.md for how
                                  to add one later
server/
  app.py                       — FastMCP app (Streamable HTTP), one tool per operation
  cognigy_client.py            — shared Cognigy REST client (auth, task polling)
  tools/manage_snapshots.py    — project backup/restore
  tools/manage_packages.py     — package export/import
  tools/manage_settings.py     — voice preview & Knowledge AI settings
  Dockerfile, .dockerignore
  requirements.txt
  README.md                    — deployment instructions
docker-compose.yml             — the mcp service, bound to 127.0.0.1:8000
nginx/cognigy-mcp.conf         — drop-in config for your existing nginx
.claude-plugin/marketplace.json — marketplace manifest (source: ./plugin)
```

## What's next

Additional Cognigy tools (agent creation, tools/flow-nodes, knowledge/RAG,
voice gateway, etc.) will be added to `server/app.py` next, and the plugin's
`skills/`/`agents/` folders are ready for guided workflows or multi-step
subagents once we scope those — both to be discussed separately.
