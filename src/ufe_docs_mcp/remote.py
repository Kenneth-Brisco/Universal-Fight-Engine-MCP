"""Streamable HTTP transport for shared or hosted deployments.

The same tools as the stdio server, behind an ASGI app with optional bearer
tokens, a per-client rate limit, and a health route. Authentication is a
static shared-token check: suitable for a private team endpoint or for gating a
public demo, not a per-user identity system.
"""
from __future__ import annotations

from collections import deque
import hmac
import ipaddress
import json
import logging
import os
from pathlib import Path
import threading
import time
from typing import Any, Iterable

from mcp.server.transport_security import TransportSecuritySettings
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import __version__
from .runtime import DEFAULT_REFRESH_HOURS
from .server import create_server

LOG = logging.getLogger("ufe_docs_mcp")
HEALTH_PATH = "/healthz"
DEFAULT_RATE_LIMIT = 120  # requests per client per minute
TOKENS_ENV = "UFE_DOCS_HTTP_TOKENS"


def is_loopback(host: str) -> bool:
    if host in ("localhost",):
        return True
    try:
        return ipaddress.ip_address(host.strip("[]")).is_loopback
    except ValueError:
        return False


def load_tokens(token_file: Path | None = None, environ: dict[str, str] | None = None) -> list[str]:
    """Read accepted bearer tokens from UFE_DOCS_HTTP_TOKENS and/or a file.

    Both hold tokens separated by commas or newlines. Blank entries are ignored.
    """
    environ = os.environ if environ is None else environ
    raw = [environ.get(TOKENS_ENV, "")]
    if token_file is not None:
        raw.append(Path(token_file).expanduser().read_text(encoding="utf-8"))
    tokens = [part.strip() for chunk in raw for part in chunk.replace("\n", ",").split(",")]
    tokens = [token for token in tokens if token]
    for token in tokens:
        if len(token) < 16:
            raise ValueError("Each HTTP access token must be at least 16 characters long.")
    return tokens


async def _send_json(send, status: int, payload: dict, headers: Iterable[tuple[bytes, bytes]] = ()) -> None:
    body = json.dumps(payload).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), *headers],
    })
    await send({"type": "http.response.body", "body": body})


class BearerTokenMiddleware:
    """Require one of a fixed set of bearer tokens on every route except health."""

    def __init__(self, app, tokens: list[str], *, exempt: tuple[str, ...] = (HEALTH_PATH,)):
        self.app = app
        self.tokens = [token.encode("utf-8") for token in tokens]
        self.exempt = exempt

    def _authorized(self, scope) -> bool:
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                scheme, _, credential = value.decode("latin-1").partition(" ")
                if scheme.lower() != "bearer":
                    return False
                candidate = credential.strip().encode("utf-8")
                # Compare against every token so timing does not reveal which one matched.
                return any([hmac.compare_digest(candidate, token) for token in self.tokens])
        return False

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in self.exempt or self._authorized(scope):
            await self.app(scope, receive, send)
            return
        await _send_json(send, 401, {
            "error": "unauthorized",
            "message": "Send 'Authorization: Bearer <token>' with an access token for this UFE Docs server.",
        }, [(b"www-authenticate", b'Bearer realm="ufe-docs"')])


class RateLimitMiddleware:
    """Sliding one-minute window per client address, kept in memory."""

    def __init__(self, app, per_minute: int, *, trust_proxy: bool = False,
                 exempt: tuple[str, ...] = (HEALTH_PATH,), clock=time.monotonic, max_clients: int = 10000):
        if per_minute < 1:
            raise ValueError("The rate limit must be at least one request per minute.")
        self.app = app
        self.per_minute = per_minute
        self.trust_proxy = trust_proxy
        self.exempt = exempt
        self.clock = clock
        self.max_clients = max_clients
        self.windows: dict[str, deque[float]] = {}
        self.lock = threading.Lock()

    def _client(self, scope) -> str:
        if self.trust_proxy:
            for name, value in scope.get("headers", []):
                if name == b"x-forwarded-for":
                    # The right-most entry was appended by the trusted proxy itself;
                    # earlier entries come from the client and can be forged.
                    last = value.decode("latin-1").split(",")[-1].strip()
                    if last:
                        return last
        client = scope.get("client")
        return client[0] if client else "unknown"

    def _admit(self, key: str) -> float | None:
        """Record a request; return seconds to wait when the client is over the limit."""
        now = self.clock()
        with self.lock:
            window = self.windows.get(key)
            if window is None:
                if len(self.windows) >= self.max_clients:
                    # Drop clients whose windows have fully expired before growing further.
                    for stale in [k for k, w in self.windows.items() if not w or now - w[-1] >= 60]:
                        del self.windows[stale]
                window = self.windows.setdefault(key, deque())
            while window and now - window[0] >= 60:
                window.popleft()
            if len(window) >= self.per_minute:
                return max(1.0, 60 - (now - window[0]))
            window.append(now)
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope.get("path") in self.exempt:
            await self.app(scope, receive, send)
            return
        wait = self._admit(self._client(scope))
        if wait is None:
            await self.app(scope, receive, send)
            return
        await _send_json(send, 429, {
            "error": "rate_limited",
            "message": f"Too many requests. Retry after {int(wait)} seconds.",
        }, [(b"retry-after", str(int(wait)).encode())])


def build_http_app(
    cache_dir: Path, *, host: str = "127.0.0.1", path: str = "/mcp",
    tokens: list[str] | None = None, allow_anonymous: bool = False,
    allowed_hosts: list[str] | None = None, rate_limit: int = DEFAULT_RATE_LIMIT,
    trust_proxy: bool = False, offline: bool = False,
    refresh_hours: float = DEFAULT_REFRESH_HOURS, auto_refresh: bool = True,
    remote_refresh: bool = False, stateless: bool = False,
) -> Any:
    """Return the ASGI app for `serve --transport http`.

    A server reachable beyond this machine must either check tokens or be
    explicitly opened with allow_anonymous; loopback binds may run without
    tokens for local testing.
    """
    tokens = list(tokens or [])
    if not tokens and not allow_anonymous and not is_loopback(host):
        raise ValueError(
            f"Refusing to serve on {host} without access tokens. Set {TOKENS_ENV} or --token-file, "
            "or pass --allow-anonymous to publish an open endpoint deliberately."
        )
    if not path.startswith("/") or path == HEALTH_PATH:
        raise ValueError("The MCP path must start with '/' and differ from the health route.")

    mcp = create_server(
        cache_dir, offline=offline, refresh_hours=refresh_hours,
        auto_refresh=auto_refresh, expose_refresh=remote_refresh,
    )

    @mcp.custom_route(HEALTH_PATH, methods=["GET"], include_in_schema=False)
    async def health(_request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok", "server": "ufe_docs", "version": __version__})

    security = None
    if allowed_hosts:
        origins = [f"https://{h}" for h in allowed_hosts] + [f"http://{h}" for h in allowed_hosts]
        security = TransportSecuritySettings(
            enable_dns_rebinding_protection=True, allowed_hosts=list(allowed_hosts), allowed_origins=origins,
        )
    app = mcp.streamable_http_app(
        streamable_http_path=path, transport_security=security, host=host, stateless_http=stateless,
    )
    if tokens:
        app = BearerTokenMiddleware(app, tokens)
    if rate_limit:
        # Outermost, so failed authentication attempts count against the limit too.
        app = RateLimitMiddleware(app, rate_limit, trust_proxy=trust_proxy)
    LOG.info(
        "UFE Docs MCP over HTTP: path=%s auth=%s rate_limit=%s/min refresh_tool=%s",
        path, "tokens" if tokens else "anonymous", rate_limit or "off", remote_refresh,
    )
    return app


def run_http(app: Any, *, host: str, port: int) -> None:
    import uvicorn

    uvicorn.run(app, host=host, port=port, log_level="warning", proxy_headers=False)
