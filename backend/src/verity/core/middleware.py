"""ASGI middleware: correlation id, access log, security headers.

These are plain ASGI middleware rather than Starlette's ``BaseHTTPMiddleware`` on
purpose. ``BaseHTTPMiddleware`` runs the downstream application in a separate anyio
task, so a ``contextvar`` set inside it is not visible to the frames outside it — which
would mean the correlation id bound per request never reaches the exception handler
that has to return it.
"""

from __future__ import annotations

import re
import time
from collections.abc import Iterable
from typing import Final

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from verity.core.logging import get_logger
from verity.shared.ids import uuid7

logger = get_logger(__name__)

CORRELATION_ID_HEADER: Final = "x-correlation-id"

# A client-supplied id is echoed back and written into log lines, so it is accepted
# only in this shape. Anything else — notably a newline — is discarded and replaced,
# because a client that can inject a newline into a log line can forge log entries.
_SAFE_CORRELATION_ID: Final = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")

SECURITY_HEADERS: Final[tuple[tuple[str, str], ...]] = (
    ("x-content-type-options", "nosniff"),
    ("x-frame-options", "DENY"),
    ("referrer-policy", "no-referrer"),
    ("cross-origin-opener-policy", "same-origin"),
    ("permissions-policy", "geolocation=(), camera=(), microphone=()"),
    ("strict-transport-security", "max-age=31536000; includeSubDomains"),
)

# This is a JSON API: it renders nothing and loads nothing.
API_CONTENT_SECURITY_POLICY: Final = (
    "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
)


def _header(scope: Scope, name: str) -> str | None:
    target = name.encode("latin-1")
    headers: Iterable[tuple[bytes, bytes]] = scope.get("headers", ())
    for key, value in headers:
        if key.lower() == target:
            return value.decode("latin-1")
    return None


class CorrelationIdMiddleware:
    """Assigns every request a correlation id, binds it, and echoes it back.

    The id ties an error response to the log line holding the detail that response
    deliberately withholds (docs/conventions/api.md).
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, CORRELATION_ID_HEADER)
        correlation_id = (
            incoming if incoming and _SAFE_CORRELATION_ID.match(incoming) else str(uuid7())
        )

        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        async def send_with_header(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)[CORRELATION_ID_HEADER] = correlation_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_header)
        finally:
            structlog.contextvars.unbind_contextvars("correlation_id")


class AccessLogMiddleware:
    """One structured line per request, carrying the correlation id."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started = time.perf_counter()
        status_code = 500

        async def send_and_capture(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
            await send(message)

        try:
            await self.app(scope, receive, send_and_capture)
        finally:
            logger.info(
                "request.completed",
                method=scope.get("method"),
                path=safe_path(scope.get("path")),
                status=status_code,
                duration_ms=round((time.perf_counter() - started) * 1000, 2),
            )


# Paths whose next segment is a bearer credential rather than an identifier.
# The vendor portal puts its token in the path — a deliberate choice, because a
# query string leaks further — which makes the access log the one place it would
# otherwise be written in the clear, on every request, for the life of the link.
_CREDENTIAL_IN_PATH: Final[tuple[str, ...]] = ("/vendor-portal/",)

_REDACTED_SEGMENT: Final = "[redacted]"


def safe_path(path: str | None) -> str:
    """A request path with any credential segment removed.

    Returns the path unchanged unless it carries a known credential, in which
    case the segment after the marker is replaced. Everything else about the line
    — method, status, duration, the route shape — survives, so the log is still
    worth reading.

    Query strings are never logged at all; this closes the other half.
    """
    if not path:
        return ""
    for marker in _CREDENTIAL_IN_PATH:
        head, sep, tail = path.partition(marker)
        if not sep:
            continue
        rest = tail.split("/", 1)
        remainder = f"/{rest[1]}" if len(rest) > 1 else ""
        return f"{head}{marker}{_REDACTED_SEGMENT}{remainder}"
    return path


class SecurityHeadersMiddleware:
    """Applies the headers docs/security/baseline.md requires on every response."""

    def __init__(self, app: ASGIApp, *, csp_exempt_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        # The interactive docs load their bundle from a CDN, so the API's own
        # `default-src 'none'` would blank the page. Docs are served only outside
        # deployed environments; see main.create_app.
        self.csp_exempt_paths = csp_exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        apply_csp = scope.get("path") not in self.csp_exempt_paths

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for name, value in SECURITY_HEADERS:
                    headers[name] = value
                if apply_csp:
                    headers["content-security-policy"] = API_CONTENT_SECURITY_POLICY
            await send(message)

        await self.app(scope, receive, send_with_headers)
