"""Outbound email over SMTP.

Delivery is best-effort and lives at the edge of a flow, never inside its
transaction: a signup commits, *then* the verification email is sent, so a mail
server that is slow or down cannot roll back the account it was confirming. When
SMTP is not configured (local, test) the mailer is a no-op and says so.

Full delivery — templates, retries, bounces, per-tenant from-addresses — is the
notifications module's job later. This is the minimum a real verification flow
needs: send one message, now.
"""

from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import aiosmtplib

from verity.core.config import Settings, get_settings
from verity.core.logging import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class OutboundEmail:
    """One message. ``to`` is the recipient; it is never logged (it is PII)."""

    to: str
    subject: str
    text: str
    html: str | None = None


class Mailer(Protocol):
    async def send(self, message: OutboundEmail) -> bool:
        """Deliver ``message``; return whether it was sent. Never raises."""
        ...


class SmtpMailer:
    """Sends via ``settings.email`` over STARTTLS. A no-op when SMTP is unset."""

    def __init__(self, settings: Settings) -> None:
        self._cfg = settings.email

    async def send(self, message: OutboundEmail) -> bool:
        cfg = self._cfg
        if not cfg.enabled:
            # Not an error: local and test run without a mail server on purpose.
            logger.info("email.skipped", reason="smtp_not_configured", subject=message.subject)
            return False

        mail = EmailMessage()
        mail["From"] = f"{cfg.from_name} <{cfg.from_email}>"
        mail["To"] = message.to
        mail["Subject"] = message.subject
        mail.set_content(message.text)
        if message.html is not None:
            mail.add_alternative(message.html, subtype="html")

        try:
            await aiosmtplib.send(
                mail,
                hostname=cfg.host,
                port=cfg.port,
                username=cfg.user,
                password=cfg.password.get_secret_value() if cfg.password else None,
                start_tls=cfg.use_tls,
                timeout=cfg.timeout_seconds,
            )
        except (aiosmtplib.SMTPException, OSError, ValueError) as exc:
            # Delivery failure never fails the caller's flow; the user can resend.
            logger.warning("email.failed", subject=message.subject, error=type(exc).__name__)
            return False

        logger.info("email.sent", subject=message.subject)
        return True


@dataclass(frozen=True, slots=True)
class SmtpCredentials:
    """An explicit SMTP server to send through — a tenant's own, or any override."""

    host: str
    port: int
    username: str | None
    password: str | None
    from_name: str
    from_address: str
    use_tls: bool
    timeout_seconds: float = 15.0


async def send_with(creds: SmtpCredentials, message: OutboundEmail) -> tuple[bool, str]:
    """Send one message through an explicit SMTP server. Returns ``(ok, detail)``;
    ``detail`` carries the error class + message on failure so a self-service
    "send test email" can tell the tenant what to fix on *their* server. Never
    raises."""
    mail = EmailMessage()
    mail["From"] = f"{creds.from_name} <{creds.from_address}>"
    mail["To"] = message.to
    mail["Subject"] = message.subject
    mail.set_content(message.text)
    if message.html is not None:
        mail.add_alternative(message.html, subtype="html")
    try:
        await aiosmtplib.send(
            mail,
            hostname=creds.host,
            port=creds.port,
            username=creds.username,
            password=creds.password,
            start_tls=creds.use_tls,
            timeout=creds.timeout_seconds,
        )
    except (aiosmtplib.SMTPException, OSError, ValueError) as exc:
        logger.warning("email.test_failed", subject=message.subject, error=type(exc).__name__)
        return False, f"{type(exc).__name__}: {exc}"
    logger.info("email.test_sent", subject=message.subject)
    return True, "Sent"


@lru_cache(maxsize=1)
def get_mailer() -> SmtpMailer:
    return SmtpMailer(get_settings())


def reset_mailer_cache() -> None:
    get_mailer.cache_clear()
