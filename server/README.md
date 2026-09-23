# Cognigy MCP Server

A stateless MCP server exposing Cognigy.AI snapshot/package/settings tools over
**Streamable HTTP**. Deploy this once on a shared host (e.g. a Linux VM); every
Claude Code user then points their plugin at it.

## Why it's stateless

This server never stores a Cognigy API base URL or API key. Every tool call
must carry the caller's own credentials as request headers:

```
X-Cognigy-Base-Url: https://api-trial.cognigy.ai
X-Cognigy-Api-Key:  <caller's Cognigy API key>
```

The plugin's `.mcp.json` sends these on every request (see `../plugin/`).
Nothing is persisted to disk or logged here — if you add logging, be careful
not to log these headers.

## Local development

```
python -m venv .venv
source .venv/bin/activate      # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py --host 127.0.0.1 --port 8000
```

## Production deployment (Linux, systemd + uvicorn)

1. Clone this repo on the server, e.g. to `/opt/cognigy-mcp`.
2. Set up the venv and install deps as above.
3. Run behind a reverse proxy (nginx/Caddy) that terminates TLS — **this
   server should never be exposed directly over plain HTTP**, since Cognigy
   API keys travel in every request's headers.

Example systemd unit (`/etc/systemd/system/cognigy-mcp.service`):

```ini
[Unit]
Description=Cognigy MCP Server
After=network.target

[Service]
Type=simple
User=cognigy-mcp
WorkingDirectory=/opt/cognigy-mcp/server
ExecStart=/opt/cognigy-mcp/server/.venv/bin/uvicorn app:app --host 127.0.0.1 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Then:
```
sudo systemctl daemon-reload
sudo systemctl enable --now cognigy-mcp
```

Point your reverse proxy at `127.0.0.1:8000` and expose it publicly (or on
your internal network) at, e.g., `https://cognigy-mcp.internal.example.com/mcp`.
Give that URL to end users to put in their plugin's `.mcp.json` (see
`../plugin/README.md`).

## Known limitations

- `download_package`'s `output_path` and `upload_and_inspect_package`'s
  `file_path` are paths on **this server's filesystem**, not the end user's
  machine (see `tools/manage_packages.py`). Point them at a shared/mounted
  directory if users need access to the files, or extend these tools to
  transfer bytes over the wire.
- Endpoints marked TODO in `tools/*.py` (package list/delete, a settings GET,
  Speechmatics provider mapping) are unverified against a live tenant.

## Files

- `app.py` — the FastMCP app (Streamable HTTP), one `@mcp.tool()` per
  operation, extracting credentials from headers via `Context.request_context.request`
- `cognigy_client.py` — shared Cognigy REST client (auth, RFC 7807 error
  parsing, async task polling)
- `tools/manage_snapshots.py` — project backup/restore
- `tools/manage_packages.py` — package export/import
- `tools/manage_settings.py` — voice preview & Knowledge AI settings
