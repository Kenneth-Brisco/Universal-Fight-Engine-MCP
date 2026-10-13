# UFE Docs MCP over Streamable HTTP.
# Works as a Hugging Face Docker Space (port 7860, user 1000) or any container host.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.8 /uv /usr/local/bin/uv

RUN useradd --create-home --uid 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/app/.venv/bin:$PATH \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PORT=7860 \
    UFE_DOCS_CACHE_DIR=/home/user/cache
WORKDIR /home/user/app

COPY --chown=user pyproject.toml uv.lock README.md LICENSE ./
COPY --chown=user src ./src
RUN uv sync --frozen --no-dev

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/healthz', timeout=4)"

# Access is decided at deploy time, never baked into the image:
#   UFE_DOCS_HTTP_TOKENS=<token>[,<token>]  private endpoint (store as a secret)
#   UFE_DOCS_ALLOW_ANONYMOUS=1              open public endpoint
# With neither set, the server refuses to start on 0.0.0.0.
# Mount persistent storage and point UFE_DOCS_CACHE_DIR at it (for example
# /data/ufe-docs-mcp) to keep the index across restarts.
CMD ["ufe-docs-mcp", "serve", "--transport", "http", "--host", "0.0.0.0", "--trust-proxy"]
