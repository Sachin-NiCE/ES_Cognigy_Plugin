---
description: Configure this plugin's Cognigy MCP server URL and Cognigy API credentials
---

This plugin talks to a centrally hosted Cognigy MCP server. It is stateless:
every request must carry your Cognigy API base URL and API key as headers.
`${CLAUDE_PLUGIN_ROOT}/.mcp.json` reads these from three environment
variables (`${COGNIGY_MCP_URL}`, `${COGNIGY_API_BASE_URL}`,
`${COGNIGY_API_KEY}`) rather than having them written into the file
directly — this file is reinstalled fresh from the plugin's marketplace
source every time the plugin is (re)installed or the marketplace is
refreshed, so anything written into it is wiped on the next install. Real
env vars set on the user's machine are NOT touched by a plugin
reinstall, so setup only has to run once per machine.

Steps:
1. Check which of `COGNIGY_MCP_URL`, `COGNIGY_API_BASE_URL`,
   `COGNIGY_API_KEY` are already set in the user's environment (ask the user
   to run `echo $COGNIGY_MCP_URL` etc. on macOS/Linux, or
   `echo $env:COGNIGY_MCP_URL` on Windows PowerShell — do not assume, actually
   check).
2. Ask the user for whichever of these are not already set:
   - **Cognigy MCP server URL** (e.g. `https://cognigy-mcp.internal.example.com/mcp`).
     If the user doesn't know it, tell them to ask whoever deployed the
     server (see this repo's `server/README.md`).
   - **Cognigy API base URL** (e.g. `https://api-trial.cognigy.ai`, or your
     tenant's own host)
   - **Cognigy API key**
3. Persist them as **permanent** environment variables (not just for the
   current shell session), matching the user's OS:
   - **Windows**: run each of these via the Bash/PowerShell tool
     (`setx` writes to the permanent user environment, not just the current
     process — the user must open a brand new terminal/restart Claude Code
     to see it):
     ```
     setx COGNIGY_MCP_URL "https://..."
     setx COGNIGY_API_BASE_URL "https://..."
     setx COGNIGY_API_KEY "..."
     ```
   - **macOS/Linux**: append export lines to the user's shell profile
     (`~/.zshrc`, `~/.bashrc`, or `~/.bash_profile` — detect which shell/file
     is actually in use rather than guessing) AND export them in the current
     session so `/mcp` can pick them up without a restart:
     ```
     echo 'export COGNIGY_MCP_URL="https://..."' >> ~/.zshrc
     echo 'export COGNIGY_API_BASE_URL="https://..."' >> ~/.zshrc
     echo 'export COGNIGY_API_KEY="..."' >> ~/.zshrc
     export COGNIGY_MCP_URL="https://..."
     export COGNIGY_API_BASE_URL="https://..."
     export COGNIGY_API_KEY="..."
     ```
4. Tell the user to fully restart Claude Code (a new terminal/process, not
   just `/mcp`, is required on Windows since `setx` doesn't affect already-running
   processes) for the change to take effect, then confirm with `/mcp` that the
   `cognigy` server shows as connected.

Never print the API key back to the user or log it anywhere. These
environment variables live locally on the user's machine only — never
committed to git, and untouched by reinstalling or updating the plugin.
