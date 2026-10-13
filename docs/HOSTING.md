# Hosting UFE3D-MCP

Hosted mode serves the same UFE reference tools over Streamable HTTP for a client that supports a server URL and the configured authentication method. Local installation remains the primary distribution: each user runs the connector without a required hosting subscription. Your coding agent uses retrieved context while implementing and verifying requested changes with its own project tools.

The repository includes a Dockerfile and a Hugging Face Space template. It does not provision an endpoint automatically. A successful local HTTP check does not establish compatibility with every web connector, and shared bearer tokens are not an OAuth authorization server. The intended source and public home is `Kenneth-Brisco/Universal-Fight-Engine-MCP`, currently PR #3's `fix/public-release-readiness` branch. This candidate does not deploy a service. See [release parity and evidence](RELEASE-EXPORT.md) for provenance and remaining publication checks. See [README](../README.md) for preview instructions and [CHANGELOG](../CHANGELOG.md) for naming migration.

## What a host must provide

- **A Python server process.** Automatic refresh runs in that process. If a host pauses or stops it, the schedule stops too. A restart reuses a valid persistent cache and checks the source only when due; it does not necessarily download the manual again.
- **Writable storage.** The recorded index was about 1 MB, plus a lock file and update history. Set `UFE_DOCS_CACHE_DIR` to persistent storage to preserve it across restarts. If the cache is lost, the next online start bootstraps a new index; the recorded catalog bootstrap made four requests spaced by the publisher's crawl delay. Future source changes can alter that count.
- **Outbound HTTPS** to `www.ufe3d.com` for online synchronization.
- **HTTPS for remote clients.** Terminate TLS at a host proxy or another HTTPS frontend. Use `--trust-proxy` only when requests reach the server through a trusted proxy that appends the client address to `X-Forwarded-For`; otherwise keep it off. The supplied Docker command assumes such a proxy.

The default HTTP server uses in-memory sessions and rate-limit windows. Run a single replica. `--stateless` removes session affinity requirements, but each replica still has its own rate-limit window and potentially its own cache; replicas need a deliberate storage and refresh design.

## Deployment choices

| Option | Fit and operational tradeoff |
| --- | --- |
| Local installation | No shared hosting account is required. Each user maintains a local process and documentation cache. |
| Container host or VPS | Runs the included Docker image. Configure process lifetime, persistent storage, HTTPS, secrets, and provider usage limits. |
| Hugging Face Docker Space | The included image and template use port 7860 and user 1000. Check the selected Space's current sleep and storage policies; preserve the cache if restart continuity matters. |
| A host that scales to zero | Can serve requests after restarting, but cannot run the refresher while stopped. A preserved cache avoids unnecessary bootstrap downloads. |

Provider plans and prices are deliberately not fixed here. Check the chosen account's current compute, storage, traffic, and idle-process terms. This repository is a Python/ASGI container application; it does not include a Cloudflare Workers deployment or an adapter for Workers storage and scheduling.

## Access and privacy

The server refuses to bind beyond loopback without an explicit access policy:

- **Private or team endpoint:** set `UFE_DOCS_HTTP_TOKENS` to one or more long random tokens, comma-separated, as a host secret, or use `--token-file`. Clients send `Authorization: Bearer <token>`. To rotate a token, replace the accepted token set and restart or redeploy the process; tokens are read at startup. For a staged rotation, temporarily accept both old and new tokens, migrate clients, then remove the old token and restart again.
- **Open public endpoint:** set `UFE_DOCS_ALLOW_ANONYMOUS=1` deliberately. Keep the rate limit enabled. The four exposed tools are read-only; `ufe_refresh_docs` stays hidden unless `--remote-refresh` is passed. The server's automatic refresh still runs.

The default rate limit is 120 requests per client per minute. Shared tokens gate access but do not establish individual user identities. Match authentication to the client's supported configuration. A remote-only client needs the real deployed URL, not a GitHub URL or the operator's localhost address.

Both transports omit cache filesystem paths from normal MCP status and return safe operational errors. Local server logs, generated configuration, and refresh-state files can retain machine details and should not be published. Keep tokens out of source control, images, screenshots, and issue reports.

The MIT license covers this connector's original code. UFE documentation retains its publisher's ownership and terms. A hosted instance serves retrieved manual text to its clients; publishing connector code does not grant additional rights to that content.

## Hugging Face Space setup

1. Create a Docker Space and copy this repository's reviewed `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`, `src/`, and `Dockerfile` into it. Replace the Space's README with [deploy/huggingface/README.md](../deploy/huggingface/README.md), which contains the Space configuration header. Keep the project README under another name if desired.
2. In Space settings, add either the secret `UFE_DOCS_HTTP_TOKENS` or the variable `UFE_DOCS_ALLOW_ANONYMOUS=1`, according to the intended access policy.
3. If the host provides persistent storage, point `UFE_DOCS_CACHE_DIR` at its writable mount; `/data/ufe-docs-mcp` is an example, not a provisioned volume.
4. After building, check `https://<space-host>/healthz`. A healthy process may still be downloading its first index; use `ufe_docs_status` for documentation readiness.
5. Generate a client entry:

   ```bash
   uv run --frozen ufe-docs-mcp client-config --format claude-code --url https://<space-host>/mcp --token-env UFE_DOCS_TOKEN
   ```

The server's secret is `UFE_DOCS_HTTP_TOKENS`; the example client reads one accepted value from `UFE_DOCS_TOKEN`. Install the printed `UFE3D-MCP` entry and supply the variable securely. The generator does not configure secrets or connect the client.

**Antigravity exception:** `--token-env` produces a `Bearer <paste token>` placeholder because that client has no documented header-variable expansion for this format. Fill it privately through the client's supported configuration. Generic JSON requires a host supporting its printed syntax. A web client that accepts only OAuth cannot be assumed to accept shared tokens.

## Local authenticated rehearsal

This POSIX-shell example keeps the token in a protected temporary file and starts an **offline loopback** server. It checks transport, access control, and discovery without downloading documentation. Run from the checkout with Python, uv, and curl available:

```bash
uv sync --frozen --no-dev

UFE_DOCS_REHEARSAL_DIR="$(mktemp -d)"
chmod 700 "$UFE_DOCS_REHEARSAL_DIR"
(umask 077; python3 -c 'import secrets; print(secrets.token_urlsafe(32))' > "$UFE_DOCS_REHEARSAL_DIR/token")
export UFE_DOCS_TOKEN="$(cat "$UFE_DOCS_REHEARSAL_DIR/token")"

uv run --frozen ufe-docs-mcp serve --transport http --host 127.0.0.1 --port 7860 \
  --token-file "$UFE_DOCS_REHEARSAL_DIR/token" --offline \
  > "$UFE_DOCS_REHEARSAL_DIR/server.log" 2>&1 &
UFE_DOCS_REHEARSAL_PID=$!

curl --fail --silent --show-error --retry 10 --retry-connrefused --retry-delay 1 \
  http://127.0.0.1:7860/healthz
uv run --frozen python scripts/smoke_http.py http://127.0.0.1:7860

uv run --frozen ufe-docs-mcp client-config --format claude-code \
  --url http://127.0.0.1:7860/mcp --token-env UFE_DOCS_TOKEN
```

The smoke test checks unauthorized rejection, the `UFE3D-MCP` identity, four read tools, and an actual status call. An empty offline cache reports unavailable documentation, which is expected for this transport-only check. To include search, complete a normal sync first and use `--expect-index` against that cache.

For an assistant rehearsal, run the printed registration command and launch the client from the same shell so it inherits `UFE_DOCS_TOKEN`. A desktop app opened elsewhere may not inherit it; use its documented secret configuration. The generated entry does not contain the token value. Preserve existing connections and use the [setup guide](SETUP.md) for a safe migration from older names.

Stop the rehearsal server and remove its temporary secret and log when finished:

```bash
kill "$UFE_DOCS_REHEARSAL_PID"
wait "$UFE_DOCS_REHEARSAL_PID" 2>/dev/null || true
unset UFE_DOCS_TOKEN
rm -f "$UFE_DOCS_REHEARSAL_DIR/token" "$UFE_DOCS_REHEARSAL_DIR/server.log"
rmdir "$UFE_DOCS_REHEARSAL_DIR"
unset UFE_DOCS_REHEARSAL_DIR UFE_DOCS_REHEARSAL_PID
```

Replace/remove only the temporary UFE registration when changing to the final endpoint. For online operation, omit `--offline`; the server evaluates its saved cache and refresh policy at startup. These checks do not establish a deployed HTTPS endpoint, a new paid-model session, or a live session in an untested assistant.
