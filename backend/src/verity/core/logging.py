"""Structured logging, with secrets removed before anything is rendered.

Rule 6 in CLAUDE.md: secrets are never written to logs. A convention cannot deliver
that — someone will eventually pass a whole credential dict into a log call. So
redaction is a processor in the pipeline, applied to every event from every logger,
including the ones inside third-party libraries that route through stdlib logging.

Redaction is by key name, not by value, because the only reliable signal that a value
is a secret is what it was called.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from typing import Any, Final

import orjson
import structlog

from verity.core.config import Settings

REDACTED: Final = "***redacted***"
TRUNCATED: Final = "***truncated***"

# Substring match, lower-cased. Over-redaction is a cosmetic problem; under-redaction
# is an incident. Add to this list freely.
_SENSITIVE_FRAGMENTS: Final[frozenset[str]] = frozenset(
    {
        "access_key",
        "api_key",
        "apikey",
        "authorization",
        "client_secret",
        "cookie",
        "credential",
        "encryption_key",
        "master_key",
        "mfa",
        "passphrase",
        "password",
        "passwd",
        "private_key",
        "refresh_token",
        "secret",
        "session_key",
        "set-cookie",
        "signature",
        "totp",
        "_token",
        "token_",
    }
)

# Exact match, lower-cased, for names too short to match as a fragment safely.
_SENSITIVE_NAMES: Final[frozenset[str]] = frozenset(
    {"auth", "dek", "key", "keys", "otp", "pwd", "token"}
)

_MAX_REDACTION_DEPTH: Final = 6

_LOGGERS_WITHOUT_OWN_HANDLERS: Final = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "sqlalchemy.engine",
    "alembic",
    "celery",
)


def is_sensitive_key(key: str) -> bool:
    """Whether a field name suggests its value must not be logged."""
    lowered = key.lower()
    if lowered in _SENSITIVE_NAMES:
        return True
    return any(fragment in lowered for fragment in _SENSITIVE_FRAGMENTS)


def _redact(value: object, depth: int) -> object:
    if depth > _MAX_REDACTION_DEPTH:
        return TRUNCATED
    if isinstance(value, Mapping):
        return {
            key: REDACTED if is_sensitive_key(str(key)) else _redact(item, depth + 1)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_redact(item, depth + 1) for item in value]
    return value


def redact_sensitive(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: replace secret-named fields at any depth."""
    for key in list(event_dict):
        if is_sensitive_key(key):
            event_dict[key] = REDACTED
        else:
            event_dict[key] = _redact(event_dict[key], depth=1)
    return event_dict


def _orjson_dumps(obj: object, **_kwargs: object) -> str:
    # default=str so UUIDs, datetimes, Decimals, and Paths serialise rather than
    # raising inside a log call, which would turn a log line into a 500.
    return orjson.dumps(obj, default=str).decode()


def _build_renderer(log_format: str) -> Callable[..., Any]:
    if log_format == "json":
        return structlog.processors.JSONRenderer(serializer=_orjson_dumps)
    return structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())


def _shared_processors() -> Sequence[Any]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        redact_sensitive,
    ]


def configure_logging(settings: Settings) -> None:
    """Install the structlog pipeline and route stdlib logging through it.

    Idempotent: safe to call from both the app factory and a Celery worker's startup.
    """
    shared = _shared_processors()
    renderer = _build_renderer(settings.resolved_log_format)
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            # Events from libraries that never touched structlog get the same
            # timestamps, the same shape, and the same redaction.
            foreign_pre_chain=list(shared),
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )
    )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for name in _LOGGERS_WITHOUT_OWN_HANDLERS:
        library_logger = logging.getLogger(name)
        library_logger.handlers = []
        library_logger.propagate = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger. Prefer the module's ``__name__``."""
    logger: structlog.stdlib.BoundLogger = structlog.stdlib.get_logger(name)
    return logger
