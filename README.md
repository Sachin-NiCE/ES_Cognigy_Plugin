# ES Cognigy Claude Plugin

Connects Claude Code to Cognigy.AI — manage project snapshots (backup/restore),
packages (export/import), and project settings (voice preview, Knowledge AI)
directly from Claude.

The project has two parts:

- **`server/`** — a stateless MCP server exposed over Streamable HTTP, meant
  to be deployed once on a shared host (e.g. a Linux VM). It holds no Cognigy
  credentials itself; every request carries the caller's own Cognigy API base
  URL and key as headers. See `server/README.md` for deployment instructions.
- **`plugin/`** — the actual Claude Code plugin: a manifest, an `.mcp.json`
  pointing at your deployed server, a `/cognigy-setup` command, and a skill
  per feature area that auto-loads workflow guidance for the tools. No Python
  or install step is needed on the end user's machine at all.

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

See `server/README.md`. nginx runs bundled inside the server's own container
(TLS termination on 443) — just drop your corporate cert/key into
`nginx/certs/` and `docker compose up -d --build`. Give the resulting URL to
your users for step 2 above.

## Repo layout

```
plugin/
  .claude-plugin/plugin.json   — plugin manifest
  .mcp.json                    — points at the hosted server; headers carry
                                  Cognigy credentials (filled in by /cognigy-setup)
  commands/cognigy-setup.md    — the /cognigy-setup command
  skills/snapshot-backups/     — guidance for list/create/restore/delete_snapshot
  skills/package-management/   — guidance for export/import/download/inspect
  skills/project-settings/     — guidance for set_voice_preview/set_knowledge_ai
  agents/                      — empty for now; see agents/README.md for how
                                  to add one later
server/
  app.py                       — FastMCP app (Streamable HTTP), one tool per operation
  cognigy_client.py            — shared Cognigy REST client (auth, task polling)
  tools/manage_snapshots.py    — project backup/restore
  tools/manage_packages.py     — package export/import
  tools/manage_settings.py     — voice preview & Knowledge AI settings
  nginx/default.conf.template  — TLS reverse proxy config (bundled in-container)
  supervisord.conf             — runs uvicorn + nginx as sibling processes
  entrypoint.sh                — renders nginx config, checks certs, starts supervisord
  Dockerfile, .dockerignore
  requirements.txt
  README.md                    — deployment instructions
docker-compose.yml             — builds/runs the container, publishes 80/443
nginx/certs/                   — put your corporate fullchain.pem/privkey.pem here (gitignored)
.claude-plugin/marketplace.json — marketplace manifest (source: ./plugin)
```

## What's next

Additional Cognigy tools (agent creation, tools/flow-nodes, knowledge/RAG,
voice gateway, etc.) will be added to `server/app.py` next, each with a
matching skill; the plugin's `agents/` folder is ready for multi-step
subagents once we scope one — both to be discussed separately.
