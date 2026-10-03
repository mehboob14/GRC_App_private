"""Domain exceptions and the one place they become HTTP responses.

Two rules shape this file, both from docs/conventions/api.md:

Error responses carry a stable ``code`` the frontend switches on, a ``message`` safe
to show a person, and a ``correlation_id`` that ties to the log line holding the real
detail. Nothing else. No exception type, no driver message, no SQL, no stack trace.

A resource in another tenant is 404, never 403, because a 403 confirms it exists.
"""

from __future__ import annotations

from typing import Any, Final

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from verity.core.logging import get_logger
from verity.core.middleware import safe_path

logger = get_logger(__name__)

INTERNAL_ERROR_CODE: Final = "internal_error"
INTERNAL_ERROR_MESSAGE: Final = "An unexpected error occurred."


class VerityError(Exception):
    """Base for every error a service raises deliberately.

    Subclasses set ``code``, ``http_status``, and a default ``message``. ``detail`` is
    for the log only and is never serialised into a response — it is where a caller
    puts the identifier, the upstream status, or the reason that would be useful at
    three in the morning and dangerous in a response body.
    """

    code: str = INTERNAL_ERROR_CODE
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    message: str = INTERNAL_ERROR_MESSAGE

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        detail: str | None = None,
    ) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        self.detail = detail
        super().__init__(self.message)

    def __repr__(self) -> str:
        # Deliberately excludes message and detail. This object ends up in tracebacks
        # and log lines that are read by people who should not need to see either.
        return f"{type(self).__name__}(code={self.code!r}, http_status={self.http_status})"


class AuthenticationRequired(VerityError):
    code = "authentication_required"
    http_status = status.HTTP_401_UNAUTHORIZED
    message = "Authentication is required."


class InvalidToken(AuthenticationRequired):
    """A signed token failed validation — expired, tampered, wrong type, wrong plane.

    One code and one message for every failure mode. Which check failed belongs in
    ``detail`` for the log; telling the caller would let a client probe token
    structure one distinguishable error at a time.
    """

    code = "invalid_token"
    message = "The provided token is invalid or has expired."


class PermissionDenied(VerityError):
    code = "permission_denied"
    http_status = status.HTTP_403_FORBIDDEN
    message = "You do not have permission to perform this action."


class NotFound(VerityError):
    """Also the correct answer for a resource that belongs to another tenant."""

    code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND
    message = "The requested resource was not found."


class Conflict(VerityError):
    """A state-machine violation: the object cannot go from where it is to there."""

    code = "conflict"
    http_status = status.HTTP_409_CONFLICT
    message = "The request conflicts with the current state of the resource."


class InvalidInput(VerityError):
    code = "invalid_input"
    http_status = status.HTTP_422_UNPROCESSABLE_CONTENT
    message = "The request could not be processed as submitted."


class RateLimited(VerityError):
    code = "rate_limited"
    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    message = "Too many requests. Try again shortly."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        detail: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message, code=code, detail=detail)
        # Seconds until the bucket's window ends, sent as ``Retry-After``.
        self.retry_after_seconds = retry_after_seconds


class UpstreamUnavailable(VerityError):
    """A third party failed.

    Rule 7: this is ``error``, not ``fail``. A caller recording a compliance outcome
    from this must record it as an error state, never as a failed control.
    """

    code = "upstream_unavailable"
    http_status = status.HTTP_502_BAD_GATEWAY
    message = "An upstream service is unavailable."


class ServiceUnavailable(VerityError):
    code = "service_unavailable"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    message = "The service is temporarily unavailable."


_STATUS_CODES: Final[dict[int, tuple[str, str]]] = {
    status.HTTP_400_BAD_REQUEST: ("bad_request", "The request was malformed."),
    status.HTTP_401_UNAUTHORIZED: (
        AuthenticationRequired.code,
        AuthenticationRequired.message,
    ),
    status.HTTP_403_FORBIDDEN: (PermissionDenied.code, PermissionDenied.message),
    status.HTTP_404_NOT_FOUND: (NotFound.code, NotFound.message),
    status.HTTP_405_METHOD_NOT_ALLOWED: (
        "method_not_allowed",
        "That method is not allowed for this resource.",
    ),
    status.HTTP_409_CONFLICT: (Conflict.code, Conflict.message),
    status.HTTP_422_UNPROCESSABLE_CONTENT: ("validation_error", InvalidInput.message),
    status.HTTP_429_TOO_MANY_REQUESTS: (RateLimited.code, RateLimited.message),
    status.HTTP_503_SERVICE_UNAVAILABLE: (
        ServiceUnavailable.code,
        ServiceUnavailable.message,
    ),
}


def correlation_id_of(request: Request) -> str:
    """The correlation id the middleware put on this request."""
    value = getattr(request.state, "correlation_id", None)
    return str(value) if value else "unavailable"


def error_body(code: str, message: str, correlation_id: str) -> dict[str, Any]:
    """The one error envelope, defined in docs/conventions/api.md."""
    return {"error": {"code": code, "message": message, "correlation_id": correlation_id}}


def _response(
    request: Request,
    http_status: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content=error_body(code, message, correlation_id_of(request)),
        headers=headers,
    )


async def _handle_verity_error(request: Request, exc: Exception) -> JSONResponse:
    error = exc if isinstance(exc, VerityError) else VerityError()
    log = logger.bind(
        correlation_id=correlation_id_of(request),
        error_code=error.code,
        http_status=error.http_status,
        path=safe_path(request.url.path),
        method=request.method,
        detail=error.detail,
    )
    if error.http_status >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        log.error("request.failed", exc_info=error)
    else:
        log.info("request.rejected")
    headers = (
        {"Retry-After": str(error.retry_after_seconds)}
        if isinstance(error, RateLimited) and error.retry_after_seconds
        else None
    )
    return _response(request, error.http_status, error.code, error.message, headers)


def _redact_validation_errors(exc: RequestValidationError) -> list[dict[str, Any]]:
    """Field errors reduced to ``type``/``loc``/``msg`` — never the submitted value.

    Pydantic's ``input`` (and any value-bearing ``ctx``) is dropped so a rejected
    password or TOTP code cannot reach the logs.
    """
    return [
        {"type": error.get("type"), "loc": error.get("loc"), "msg": error.get("msg")}
        for error in exc.errors()
    ]


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    # The per-field location and message are genuinely useful and stay in the log. The
    # submitted value never does: Pydantic's error dicts carry the offending `input`
    # (and sometimes `ctx`), which for a route like /auth/mfa/verify is a live TOTP or
    # recovery code, and for a login is a password. Keep type/loc/msg only — user input
    # is never logged verbatim. The envelope in docs/conventions/api.md has no field for
    # this detail; widening it is an API convention change and belongs in its own spec.
    errors = _redact_validation_errors(exc) if isinstance(exc, RequestValidationError) else None
    logger.info(
        "request.invalid",
        correlation_id=correlation_id_of(request),
        path=safe_path(request.url.path),
        method=request.method,
        validation_errors=errors,
    )
    code, message = _STATUS_CODES[status.HTTP_422_UNPROCESSABLE_CONTENT]
    return _response(request, status.HTTP_422_UNPROCESSABLE_CONTENT, code, message)


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    http_status = (
        exc.status_code
        if isinstance(exc, StarletteHTTPException)
        else status.HTTP_500_INTERNAL_SERVER_ERROR
    )
    raw_detail = getattr(exc, "detail", None)
    code, message = _STATUS_CODES.get(http_status, (INTERNAL_ERROR_CODE, INTERNAL_ERROR_MESSAGE))
    # `detail` is whatever the raiser passed. It is logged, never returned: a route
    # that put an internal reason in there must not have it reach a client.
    logger.info(
        "request.rejected",
        correlation_id=correlation_id_of(request),
        http_status=http_status,
        path=safe_path(request.url.path),
        method=request.method,
        detail=str(raw_detail) if raw_detail is not None else None,
    )
    return _response(request, http_status, code, message)


async def _handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "request.unhandled",
        correlation_id=correlation_id_of(request),
        path=safe_path(request.url.path),
        method=request.method,
        exc_info=exc,
    )
    return _response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        INTERNAL_ERROR_CODE,
        INTERNAL_ERROR_MESSAGE,
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Register every handler. There is no other place an error becomes a response."""
    app.add_exception_handler(VerityError, _handle_verity_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected_error)
