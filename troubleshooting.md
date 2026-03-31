# Troubleshooting

## Server hangs on shutdown (`Waiting for connections to close`)

When you run mcpdoc with `--transport sse`, clients (including MCP hosts and the MCP Inspector) often keep a **long-lived connection** to the `/sse` endpoint. After you press **Ctrl+C**, Uvicorn starts shutting down and may log:

```text
INFO:     Shutting down
INFO:     Waiting for connections to close. (CTRL+C to force quit)
```

That wait is normal until every open connection closes.

### What to do

1. **Graceful:** Disconnect the client (close the Inspector tab, disconnect the MCP host, or stop using the server URL) so connections drop, then stop the server again.

2. **Force quit from the same terminal:** Press **Ctrl+C** a **second** time. Uvicorn prompts for this explicitly.

3. **Force quit from another terminal (Windows PowerShell):** Find the process listening on your port (default examples use **8082**) and stop it:

   ```powershell
   Get-NetTCPConnection -LocalPort 8082 -ErrorAction SilentlyContinue |
     Select-Object -ExpandProperty OwningProcess -Unique |
     ForEach-Object { Stop-Process -Id $_ -Force }
   ```

   Replace `8082` if you use a different `--port`.

4. **Alternative:** After noting the PID from the log line `Started server process [PID]`, run:

   ```powershell
   taskkill /PID <PID> /F
   ```

On Unix-like systems you can use `lsof -i :8082` (or `ss -tlnp`) to find the listener, then `kill -9 <pid>`.

## MCP Inspector: use the full SSE URL

Point the Inspector at **`http://<host>:<port>/sse`**, not only `http://<host>:<port>/`.

Example: `--port 8082` and `--host localhost` → `http://localhost:8082/sse`.

If you open only the origin in a browser, you may see **`GET /`** in the logs. That path is not the MCP stream; behavior depends on your mcpdoc version (recent builds respond on `/` with a short hint; older builds may return **404**, which is harmless for MCP as long as `/sse` works).

## `fetch_docs` fails when `url` is empty

Calling `tools/call` with `fetch_docs` and **`"url": ""`** (or whitespace only) triggers an error. An empty string is not treated as `http:` / `https:`, so the server interprets it as a **local file path**. After normalization, that becomes the process **current working directory**, which is not in your allowed local files list, so you get a **`ValueError`** (for example: local file not allowed, with the resolved path and allowed files).

### What to do

1. Call **`list_doc_sources`** and pass a real **URL or allowed path** from the response (for example the `llms.txt` URL).
2. For follow-up fetches, pass a **concrete documentation URL** taken from that `llms.txt`, still within your configured allowlist.

Do not invoke `fetch_docs` with a blank `url`.

## `OPTIONS /sse` returns `405 Method Not Allowed`

Browser-based tools send a CORS preflight (`OPTIONS`) to `/sse`. Builds without SSE CORS support answer **`405`**.

### What to do

1. **Prefer a current install:** Upgrade the published package, or run from this repository:

   ```bash
   uv sync
   uv run mcpdoc ... --transport sse --port 8082 --host localhost
   ```

2. **`uvx --from mcpdoc`** only includes CORS fixes **after** they appear in the PyPI release you install. If `405` persists with `uvx`, use `uv run` from a checkout of this repo until PyPI catches up.

3. **Restrict origins (optional):** If a client runs on a fixed origin (e.g. the Inspector), you can pass explicit allowed origins:

   ```bash
   mcpdoc ... --transport sse --port 8082 --host localhost \
     --cors-origins "http://127.0.0.1:6274" "http://localhost:6274"
   ```

   Adjust host, port, and scheme to match what the browser shows for the Inspector. Default behavior allows any origin (`*`).

See **SSE and MCP Inspector (CORS)** in the [README](README.md).

## `GET /` returns `404 Not Found`

Something requested the **site root** (`/`), not **`/sse`**. That often happens when a browser loads `http://localhost:8082/` by habit.

- **For MCP:** connect to **`/sse`**; a **404** on `/` does not break SSE.
- **To remove the noise:** use a build that defines a root handler (current `mcpdoc` from this repo), then fully restart the server so the new code is loaded.

If you still see **404** on `/` after a restart, confirm you are not running an older wheel or another copy of the project without that route.

## Command-line: do not paste literal `...`

In docs, `...` means “put your real arguments here” (e.g. `--urls`, config flags). The shell will treat `...` as a real token and argparse will fail with **unrecognized arguments**.

## Port already in use

If startup fails because the port is taken, either stop the other process on that port (same PowerShell snippet as in *Server hangs on shutdown*, with your `--port`) or choose a different `--port` for mcpdoc.

## `VIRTUAL_ENV` does not match the project environment (`uv` warning)

If `uv` warns that `VIRTUAL_ENV` points elsewhere, either deactivate the other venv before `uv run`, or use `uv run` without relying on a mismatched `VIRTUAL_ENV`. See `uv` docs for `--active` if you intend to target the currently activated environment.
