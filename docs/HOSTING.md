# Hosting the UFE Docs MCP

The hosted mode serves the same tools over Streamable HTTP for assistants that only accept a server URL, such as claude.ai on the web, ChatGPT, or the Grok API, and for teams that want one shared instance. Local installation remains the primary way to use the connector and costs nothing to run.

Nothing in this repository deploys automatically. Decide on access and content permissions before publishing an endpoint.

## What a host must provide

- **An always-on process.** The server keeps its documentation snapshot current with an in-process schedule. Hosts that scale to zero stop that schedule, and the next cold start downloads the documentation again.
- **A small writable disk.** The index is about 1 MB, plus a lock file and update history. Point `UFE_DOCS_CACHE_DIR` at persistent storage to keep it across restarts. Without persistence, each restart performs one catalog download of about four requests, spaced by the publisher's crawl delay.
- **Outbound HTTPS** to `www.ufe3d.com`.
- **HTTPS in front of the server.** Container hosts terminate TLS at their proxy. Run the server with `--trust-proxy` there so rate limiting keys on the proxy-supplied client address.

The server runs as one process with in-memory sessions and rate-limit windows. Run a single replica, or add `--stateless` and accept per-replica rate limits.

## Options

Prices change; confirm on each provider's pricing page.

| Option | Approximate monthly cost | Notes |
| --- | --- | --- |
| Local install only | $0 | Primary distribution. Each user runs their own server. |
| Hugging Face Docker Space (free CPU) | $0; persistent storage is a paid add-on | The included `Dockerfile` matches Spaces' port 7860 and user 1000. Free Spaces sleep when idle, and the cache resets without persistent storage. |
| Small VPS (Hetzner, DigitalOcean) | about $4–6 | Full control; you maintain the OS and TLS. |
| Fly.io machine with a volume | about $3–7 | Usage-based; durable volume for the cache. |
| Render or Railway | about $5–8 | Git-based deploys. |
| Cloud Run and other scale-to-zero platforms | low when idle | The background schedule stops while scaled to zero. |

## Access policy

Pick one deliberately. The server refuses to listen beyond loopback until one is set.

- **Private or team endpoint:** set `UFE_DOCS_HTTP_TOKENS` to one or more long random tokens, comma-separated, as a host secret. Clients send `Authorization: Bearer <token>`. Rotate a token by adding the new one, updating clients, then removing the old one.
- **Open public endpoint:** set `UFE_DOCS_ALLOW_ANONYMOUS=1`. Keep the rate limit on. The tools are read-only, and `ufe_refresh_docs` stays hidden unless you pass `--remote-refresh`.

Bearer tokens are a shared-secret gate. They do not identify individual users, and they are not the OAuth flow that public connector directories expect.

## Content permissions

A hosted endpoint serves text from the publisher's manual to whoever connects. Local installs retrieve the documentation into each user's own cache. Confirm the publisher's permission before running a public endpoint or listing it in a connector directory, which also requires that the server's APIs belong to the operator or are legitimately proxied.

## Hugging Face Space checklist

Do not run these steps until hosting is approved.

1. Create a Docker Space and copy this repository's `pyproject.toml`, `uv.lock`, `README.md`, `LICENSE`, `src/`, and `Dockerfile` into it. Replace the Space's `README.md` with [deploy/huggingface/README.md](../deploy/huggingface/README.md), which carries the Space configuration header, and keep this project's README under another name if you want it in the Space.
2. In the Space settings, add either the secret `UFE_DOCS_HTTP_TOKENS` or the variable `UFE_DOCS_ALLOW_ANONYMOUS=1`.
3. Optional: attach persistent storage and set `UFE_DOCS_CACHE_DIR=/data/ufe-docs-mcp`.
4. After the build, check `https://<space-host>/healthz`, then connect a client to `https://<space-host>/mcp`:

   ```bash
   uv run --frozen ufe-docs-mcp client-config --format claude-code --url https://<space-host>/mcp --token-env UFE_DOCS_TOKEN
   ```

## Local rehearsal without Docker

The container steps can be rehearsed on a workstation:

```bash
uv sync --frozen --no-dev
UFE_DOCS_HTTP_TOKENS="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')" PORT=7860 uv run --frozen ufe-docs-mcp serve --transport http --port 7860
```

Connect clients to `http://127.0.0.1:7860/mcp` with the same token.
