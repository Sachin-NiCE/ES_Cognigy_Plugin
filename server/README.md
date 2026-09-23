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

## Production deployment (Linux, Docker + your existing nginx)

**This server must never be reachable over plain HTTP** — Cognigy API keys
travel in every request's headers, so TLS termination in front of it is not
optional.

If you already run nginx on this host with corporate TLS certificates
configured (the common case), use that instead of running another nginx:

1. Start the container:
   ```
   docker compose up -d
   ```
   This runs just the `mcp` service, bound to `127.0.0.1:8000` on the host —
   not exposed externally on its own.

2. Add `nginx/cognigy-mcp.conf` to your existing nginx. It has two options:
   - **Option A** (you already have a `server { listen 443 ssl; ... }` block
     for this host, with your corporate cert already referenced there): copy
     just the `location /mcp { ... }` block from the file into it.
   - **Option B** (fresh dedicated site): copy the whole file into
     `/etc/nginx/conf.d/cognigy-mcp.conf` (or your distro's sites-available +
     symlink convention), and fill in `server_name` and your corporate
     certificate paths.

3. Reload nginx:
   ```
   sudo nginx -t && sudo systemctl reload nginx
   ```

No separate reverse-proxy container is needed — nginx on the host talks
straight to the container's published port. If you *don't* already have
nginx (or prefer a load balancer/API gateway instead), point that at
`127.0.0.1:8000/mcp` the same way; the container doesn't care what's in front
of it as long as it's `http://127.0.0.1:8000` from the host's perspective.

### Rebuilding after a code change

```
docker compose build mcp
docker compose up -d mcp
```

### Without Docker (systemd + uvicorn directly)

If you'd rather not use Docker:
1. Clone this repo on the server, e.g. to `/opt/cognigy-mcp`.
2. Set up the venv and install deps as in "Local development" above.
3. Use this systemd unit (`/etc/systemd/system/cognigy-mcp.service`):

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

```
sudo systemctl daemon-reload
sudo systemctl enable --now cognigy-mcp
```

Either way, give the resulting public URL (e.g.
`https://cognigy-mcp.internal.example.com/mcp`) to end users to put in their
plugin's `.mcp.json` (see `../plugin/README.md`).

## Known limitations

- `download_package`'s `output_path` and `upload_and_inspect_package`'s
  `file_path` are paths on **this server's filesystem**, not the end user's
  machine (see `tools/manage_packages.py`). Point them at a shared/mounted
  directory if users need access to the files, or extend these tools to
  transfer bytes over the wire.
- Endpoints marked TODO in `tools/*.py` (package list/delete, a settings GET,
  Speechmatics provider mapping) are unverified against a live tenant.

## Files

- `Dockerfile` / `.dockerignore` — container image for this server
- `../docker-compose.yml` — the `mcp` service, bound to `127.0.0.1:8000`
- `../nginx/cognigy-mcp.conf` — drop-in config for your existing nginx
  (both a location-block snippet and a full standalone server block)
- `app.py` — the FastMCP app (Streamable HTTP), one `@mcp.tool()` per
  operation, extracting credentials from headers via `Context.request_context.request`
- `cognigy_client.py` — shared Cognigy REST client (auth, RFC 7807 error
  parsing, async task polling)
- `tools/manage_snapshots.py` — project backup/restore
- `tools/manage_packages.py` — package export/import
- `tools/manage_settings.py` — voice preview & Knowledge AI settings
