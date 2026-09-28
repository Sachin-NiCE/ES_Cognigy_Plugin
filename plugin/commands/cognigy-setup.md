---
description: Configure this plugin's Cognigy MCP server URL and Cognigy API credentials
---

This plugin talks to a centrally hosted Cognigy MCP server. It is stateless:
every request must carry your Cognigy API base URL and API key as headers,
which live in this plugin's `${CLAUDE_PLUGIN_ROOT}/.mcp.json`.

Steps:
1. Read `${CLAUDE_PLUGIN_ROOT}/.mcp.json`.
2. Ask the user for whichever of these are not already filled in (a placeholder
   like `REPLACE-WITH-...` or an empty string counts as not filled in):
   - **Cognigy MCP server URL** (the `url` field — your organization's hosted
     server, e.g. `https://cognigy-mcp.internal.example.com/mcp`). If the user
     doesn't know it, tell them to ask whoever deployed the server (see this
     repo's `server/README.md`).
   - **Cognigy API base URL** (e.g. `https://api-trial.cognigy.ai`, or your
     tenant's own host)
   - **Cognigy API key**
3. Edit `${CLAUDE_PLUGIN_ROOT}/.mcp.json`, setting:
   - `mcpServers.cognigy.url` to the server URL
   - `mcpServers.cognigy.headers["X-Cognigy-Base-Url"]` to the API base URL
   - `mcpServers.cognigy.headers["X-Cognigy-Api-Key"]` to the API key
4. Tell the user to restart Claude Code (or run `/mcp` to reconnect) for the
   change to take effect, then confirm with `/mcp` that the `cognigy` server
   shows as connected.

Never print the API key back to the user or log it anywhere. This file lives
locally on the user's machine only — it is not committed back to the plugin's
git repository.
