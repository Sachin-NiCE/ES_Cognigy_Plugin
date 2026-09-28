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

## Production deployment (Linux, Docker — nginx bundled in the container)

**This server must never be reachable over plain HTTP** — Cognigy API keys
travel in every request's headers, so TLS termination is not optional.

nginx runs **inside this same container** alongside the app (managed by
supervisord — see `supervisord.conf`), terminating TLS and proxying `/mcp` to
uvicorn on loopback (`127.0.0.1:8000`, not exposed outside the container). No
separate nginx container, and no changes to any nginx you already run
elsewhere on the host.

The whole container runs as a non-root user. nginx listens on an
unprivileged port (8443) internally rather than 443, so it never needs root
to bind it — `docker-compose.yml`'s port mapping (`"${HTTPS_PORT:-443}:8443"`)
is what puts it on the real HTTPS port externally. Only HTTPS is published
(no plain-HTTP redirect exposed) since this is an API-only service.

1. Put your corporate certificate and key at:
   ```
   nginx/certs/fullchain.pem
   nginx/certs/privkey.pem
   ```
   (see `../nginx/certs/README.md`). These are mounted read-only into the
   container; the repo's `.gitignore` keeps the real files out of git.

2. Optionally set `SERVER_NAME` (defaults to `_`, nginx's catch-all) to your
   real hostname, e.g. in a `.env` file next to `docker-compose.yml`:
   ```
   SERVER_NAME=cognigy-mcp.internal.example.com
   ```

3. If port 443 is already taken on this host (common on a shared box running
   multiple stacks — check with `sudo ss -tlnp | grep :443`), set
   `HTTPS_PORT` to a free one instead, in the same `.env` file:
   ```
   HTTPS_PORT=8446
   ```

4. Build and start:
   ```
   docker compose up -d --build
   ```

5. Verify: `docker compose logs -f` should show both `uvicorn` and `nginx`
   started via supervisord; `curl -vk https://localhost:${HTTPS_PORT:-443}/mcp`
   should get a response (not a connection error or TLS failure).

### Rebuilding after a code or cert change

```
docker compose build
docker compose up -d
```
(cert files are just re-mounted, no rebuild needed if only they changed —
`docker compose restart mcp` is enough for a cert rotation)

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

- `Dockerfile` / `.dockerignore` — image with app + nginx + supervisor
- `supervisord.conf` — runs uvicorn and nginx as sibling processes, both
  under the container's non-root user (see Dockerfile's `USER mcp`)
- `entrypoint.sh` — renders `nginx/default.conf.template` with `SERVER_NAME`
  via `envsubst`, checks certs exist, then execs supervisord
- `nginx/default.conf.template` — TLS-terminating reverse proxy to
  `127.0.0.1:8000/mcp`, streaming-friendly (no buffering, long read timeout)
- `../docker-compose.yml` — builds/runs this container, publishes HTTPS
  (443 by default, override with `HTTPS_PORT`), mounts `../nginx/certs` read-only
- `../nginx/certs/` — put your corporate `fullchain.pem`/`privkey.pem` here
  (gitignored)
- `app.py` — the FastMCP app (Streamable HTTP), one `@mcp.tool()` per
  operation, extracting credentials from headers via `Context.request_context.request`
- `cognigy_client.py` — shared Cognigy REST client (auth, RFC 7807 error
  parsing, async task polling)
- `tools/manage_snapshots.py` — project backup/restore
- `tools/manage_packages.py` — package export/import
- `tools/manage_settings.py` — voice preview & Knowledge AI settings
