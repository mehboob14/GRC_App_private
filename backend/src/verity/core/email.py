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
from email.utils import formatdate, make_msgid
from functools import lru_cache
from html import escape
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
    reply_to: str | None = None
    """Where a human reply should land. Without it, a reply to an automated
    message disappears into whichever mailbox happened to send it."""
    log_label: str | None = None
    """What the mailer's log lines call this message in place of its subject. Set it
    when the subject carries personal data (a visitor's name and company), because the
    subject is otherwise logged on every send."""

    @property
    def log_subject(self) -> str:
        return self.log_label or self.subject


def _compose(
    message: OutboundEmail, from_header: str, *, sender_domain: str | None = None
) -> EmailMessage:
    """Build the MIME message both send paths share.

    ``Date`` is mandatory under RFC 5322 and ``Message-ID`` effectively so. The
    stdlib adds neither and aiosmtplib adds nothing at all — a submission relay
    usually stamps them on the way out, which is why their absence has not bitten
    yet. That masking disappears the moment mail goes through a provider, and
    every filter in between grades the header set. Minting the Message-ID here
    also names our own domain rather than the relay's.

    ``Auto-Submitted`` stops out-of-office responders replying to a machine,
    which otherwise fills the sending mailbox and erodes its reputation.
    """
    mail = EmailMessage()
    mail["From"] = from_header
    mail["To"] = message.to
    mail["Subject"] = message.subject
    mail["Date"] = formatdate(localtime=True)
    mail["Message-ID"] = make_msgid(domain=sender_domain) if sender_domain else make_msgid()
    mail["Auto-Submitted"] = "auto-generated"
    if message.reply_to:
        mail["Reply-To"] = message.reply_to
    mail.set_content(message.text)
    if message.html is not None:
        # Order matters: the last alternative is the preferred one, so the HTML
        # part is added after the plain-text body, never before.
        mail.add_alternative(message.html, subtype="html")
    return mail


def _domain_of(address: str) -> str | None:
    _, _, domain = address.rpartition("@")
    return domain or None


# --- Presentation -----------------------------------------------------------
#
# Email HTML is not web HTML: no external stylesheets, no webfonts, no CSS
# variables, no flexbox. Everything is a table with inline styles, because that
# is the intersection every mail client renders alike. The colours are the design
# system's own tokens resolved to hex, since `var()` does not survive the trip.
#
# There is deliberately no logo: the only brand asset in the repo is a
# placeholder that belongs to another company (see components/ui/brand-mark.tsx),
# and a remote image would be blocked by default anyway. A styled wordmark is
# what the app itself pairs with the mark, and it always renders.

_BRAND = "#0369A1"  # action-primary — button fills and links
_INK = "#101828"  # text-primary
_BODY = "#475467"  # text-secondary
_MUTED = "#667085"  # text-subtle — the contrast floor for text that must be read
_PAGE = "#F4F5F7"  # surface-page
_CARD = "#FFFFFF"  # surface-primary
_LINE = "#E4E7EC"  # border-default
_FONT = "'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"


_DEFAULT_FOOTER = "You received this because this address was used on Verity."


def render_email(
    *,
    heading: str,
    paragraphs: tuple[str, ...],
    action: tuple[str, str] | None = None,
    footnote: str | None = None,
    footer: str | None = None,
) -> str:
    """One layout for every message the platform sends: wordmark, card, at most
    one call to action, footer. ``action`` is ``(label, url)``.

    The URL is repeated as readable text beneath the button on purpose. Clients
    that block or rewrite links still leave the address legible, and a recipient
    who distrusts a button can see where it goes before clicking — which matters
    more in a compliance product than a tidy layout does.

    ``footer`` replaces the line saying why the recipient got the message, for the
    mail that is *not* sent to someone with a Verity account: the default is wrong
    for the team notice about a website visitor. It is plain text, escaped here,
    unlike ``paragraphs`` and ``footnote``, which are markup the caller has made safe.
    """
    blocks = "".join(
        f'<p style="margin:0 0 16px;font-size:15px;line-height:24px;color:{_BODY};">{p}</p>'
        for p in paragraphs
    )

    button = ""
    if action is not None:
        label, url = action
        safe = escape(url, quote=True)
        button = (
            f'<table role="presentation" cellpadding="0" cellspacing="0" border="0"'
            f' style="margin:24px 0 12px;"><tr><td bgcolor="{_BRAND}"'
            f' style="border-radius:8px;"><a href="{safe}"'
            f' style="display:inline-block;padding:12px 26px;font-family:{_FONT};'
            f"font-size:15px;font-weight:600;color:#FFFFFF;text-decoration:none;"
            f'border-radius:8px;">{escape(label)}</a></td></tr></table>'
            f'<p style="margin:0;font-size:13px;line-height:20px;color:{_MUTED};">'
            f"Or paste this into your browser:<br>"
            f'<span style="color:{_BRAND};word-break:break-all;">{safe}</span></p>'
        )

    tail = (
        f'<p style="margin:20px 0 0;font-size:13px;line-height:20px;color:{_MUTED};">{footnote}</p>'
        if footnote
        else ""
    )

    return f"""<!doctype html>
<html><body style="margin:0;padding:0;background-color:{_PAGE};">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
       style="background-color:{_PAGE};padding:32px 16px;">
  <tr><td align="center">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"
           style="max-width:520px;font-family:{_FONT};">
      <tr><td style="padding:0 0 20px;">
        <span style="font-size:19px;font-weight:800;letter-spacing:-0.2px;
                     color:{_INK};">Verity</span>
      </td></tr>
      <tr><td style="background-color:{_CARD};border:1px solid {_LINE};
                     border-radius:12px;padding:32px;">
        <h1 style="margin:0 0 16px;font-size:20px;line-height:28px;font-weight:700;
                   letter-spacing:-0.3px;color:{_INK};">{escape(heading)}</h1>
        {blocks}{button}{tail}
      </td></tr>
      <tr><td style="padding:20px 4px 0;font-size:12px;line-height:18px;color:{_MUTED};">
        Verity &middot; SOC 2 compliance automation<br>
        {escape(footer) if footer is not None else _DEFAULT_FOOTER}
      </td></tr>
    </table>
  </td></tr>
</table>
</body></html>"""


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
            logger.info("email.skipped", reason="smtp_not_configured", subject=message.log_subject)
            return False

        mail = _compose(
            message,
            f"{cfg.from_name} <{cfg.from_email}>",
            sender_domain=_domain_of(cfg.from_email or ""),
        )

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
            logger.warning("email.failed", subject=message.log_subject, error=type(exc).__name__)
            return False

        logger.info("email.sent", subject=message.log_subject)
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
    mail = _compose(
        message,
        f"{creds.from_name} <{creds.from_address}>",
        sender_domain=_domain_of(creds.from_address),
    )
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
