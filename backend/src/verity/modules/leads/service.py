"""Demo requests: what a submission of the website's form does.

A request is stored and audited in one provider-plane transaction, and only after that
commits does any mail go out, so a slow or broken mail server can neither hold the
transaction open nor lose the request. The mail is the second half of the work and is
:meth:`LeadsService.deliver`, which the router runs after the response is sent: a
visitor never waits on SMTP, and a mail server that is down costs a lead nothing but a
notification.

Two mails, both best-effort:

* **the owner's notification** to ``settings.leads.notify_email``, whose ``Reply-To`` is
  the visitor, so a plain reply reaches them. Every value in it is the visitor's, so it
  is escaped in the HTML part and flattened to one line in the plain-text part.
* **the visitor's receipt**, which is deliberately generic. Anyone can type any address
  into the form, so nothing the sender wrote may reach a third party's inbox through it:
  no name, no message, no link. It goes out at most once per address per 24 hours.

Rules this file keeps, each of which has been got wrong somewhere:

* **No personal data in a log or the audit trail.** A log line carries a request's id
  and nothing else. The audit row carries the id and the three labels (source, interest,
  page) and never a name, an address or the message. The mailer logs a message by
  ``log_label`` instead of its subject, because the owner's subject names the visitor.
* **A driver error is not logged as it arrived.** SQLAlchemy puts the bound parameters
  into its message, and here the parameters are the visitor's details. The failure is
  logged by class name and re-raised as a plain 503.
* **A honeypot hit leaves no trace**: nothing stored, nothing sent, one nameless log line.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from html import escape
from typing import Final

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from verity.core.config import get_settings
from verity.core.db import provider_session_scope
from verity.core.email import Mailer, OutboundEmail, get_mailer, render_email
from verity.core.errors import ServiceUnavailable
from verity.core.logging import get_logger
from verity.modules.audit.service import AuditService, System, audit_service
from verity.modules.leads.models import DemoRequest
from verity.modules.leads.schemas import clean_line, clean_text
from verity.shared.ids import uuid7

logger = get_logger(__name__)

CONFIRMATION_COOLDOWN: Final = timedelta(hours=24)
"""One receipt per address in this long, however many requests it makes."""

SUBJECT_MAX_LENGTH: Final = 120

NOT_GIVEN: Final = "Not given"

_AUDITED_FIELDS: Final = ("id", "source", "interest", "page")
"""What the audit row says about a request. Never the name, address or message."""

_OWNER_FOOTER: Final = (
    "You received this because someone sent the demo request form on the Verity website."
)
_REQUESTER_FOOTER: Final = (
    "You received this because a demo request was made on the Verity website using this address."
)
_REQUESTER_SUBJECT: Final = "We received your Verity demo request"
_REQUESTER_BODY: Final = (
    "Thanks for asking about Verity. We received your demo request and will reply by "
    "email to find a time that suits you, usually within one business day. If you did "
    "not make this request you can ignore this email."
)


@dataclass(frozen=True, slots=True, repr=False)
class LeadInput:
    """One submission of the form, as the service takes it. ``website`` is the honeypot."""

    full_name: str
    email: str
    company: str
    message: str | None = None
    interest: str | None = None
    source: str | None = None
    page: str | None = None
    website: str | None = None

    def __repr__(self) -> str:
        # Every field is somebody's personal data, and this ends up in tracebacks.
        return "LeadInput(...)"


@dataclass(frozen=True, slots=True)
class Delivery:
    """What a stored request still owes: its mail. Holds the visitor's details in memory
    until they are sent, and is never persisted or logged."""

    lead_id: uuid.UUID
    received_at: datetime
    confirm: bool
    """Whether the visitor is owed a receipt: wanted by configuration, and not already
    sent one in the last day."""

    lead: LeadInput = field(repr=False)


# ---------------------------------------------------------------------------
# The two messages
# ---------------------------------------------------------------------------


def sanitise_subject(value: str) -> str:
    """A subject that cannot carry a second header: no control character or line break,
    whitespace collapsed, at most ``SUBJECT_MAX_LENGTH`` characters."""
    return clean_line(value)[:SUBJECT_MAX_LENGTH].rstrip()


def _html_lines(value: str) -> str:
    """Text as markup: escaped, with its line breaks kept."""
    return escape(value).replace("\n", "<br>")


def _html_fields(rows: tuple[tuple[str, str], ...]) -> str:
    """Label and value pairs as one block of markup, every value escaped."""
    return "<br>".join(f"<strong>{label}</strong>: {escape(value)}" for label, value in rows)


def owner_message(lead: LeadInput, *, to: str, received_at: datetime) -> OutboundEmail:
    """The notice that somebody asked for a demo.

    ``Reply-To`` is the visitor. Every value is the visitor's own and is treated as
    hostile: escaped in the HTML part, one flat line each in the text part, and
    sanitised in the subject.
    """
    name = clean_line(lead.full_name)
    company = clean_line(lead.company)
    email = clean_line(lead.email)
    message = clean_text(lead.message or "") or NOT_GIVEN
    # Who asked, then what they said, then where it came from: one reading order for
    # the text and the HTML part.
    contact = (
        ("Name", name),
        ("Email", email),
        ("Company", company),
        ("Interest", clean_line(lead.interest or "") or NOT_GIVEN),
    )
    context = (
        ("Source", clean_line(lead.source or "") or NOT_GIVEN),
        ("Page", clean_line(lead.page or "") or NOT_GIVEN),
        ("Received (UTC)", received_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M")),
    )
    reply_hint = "Reply to this email to answer them directly."

    text = "\n".join(
        [
            "New demo request",
            "",
            *(f"{label}: {value}" for label, value in contact),
            "",
            "Message:",
            message,
            "",
            *(f"{label}: {value}" for label, value in context),
            "",
            reply_hint,
        ]
    )
    html = render_email(
        heading="New demo request",
        paragraphs=(
            _html_fields(contact),
            f"<strong>Message</strong><br>{_html_lines(message)}",
            _html_fields(context),
        ),
        footnote=reply_hint,
        footer=_OWNER_FOOTER,
    )
    return OutboundEmail(
        to=to,
        subject=sanitise_subject(f"New demo request: {company} ({name})"),
        text=text,
        html=html,
        reply_to=email,
        log_label="demo_request_notification",
    )


def requester_message(*, to: str, reply_to: str) -> OutboundEmail:
    """The receipt. Generic on purpose: it says nothing the visitor typed, because the
    address it goes to may belong to somebody who never asked."""
    html = render_email(
        heading="Your demo request",
        paragraphs=(escape(_REQUESTER_BODY),),
        footer=_REQUESTER_FOOTER,
    )
    return OutboundEmail(
        to=to,
        subject=_REQUESTER_SUBJECT,
        text=f"Your demo request\n\n{_REQUESTER_BODY}",
        html=html,
        reply_to=reply_to,
        log_label="demo_request_receipt",
    )


# ---------------------------------------------------------------------------
# The service
# ---------------------------------------------------------------------------


class LeadsService:
    """Stores a demo request, audits it, and sends the two mails it owes."""

    def __init__(self, audit: AuditService | None = None, mailer: Mailer | None = None) -> None:
        self._audit = audit or audit_service
        # Resolved at send time when not given, so the cached SMTP mailer is never
        # captured before configuration is final.
        self._mailer = mailer

    @staticmethod
    def is_honeypot(lead: LeadInput) -> bool:
        """Whether the hidden field was filled in. Only a script does that."""
        return bool(lead.website and lead.website.strip())

    async def submit(self, lead: LeadInput) -> Delivery | None:
        """Store and audit one request in a single provider-plane transaction.

        Returns what is still owed (the mail), or ``None`` for a honeypot hit, which is
        neither stored nor answered any differently.

        Raises:
            ServiceUnavailable: the request could not be stored. Nothing about the
                driver's error is logged or returned, because it names the visitor.
        """
        if self.is_honeypot(lead):
            logger.info("leads.honeypot")
            return None

        received_at = datetime.now(UTC)
        email = lead.email.strip().lower()
        try:
            async with provider_session_scope() as session:
                row = DemoRequest(
                    id=uuid7(),
                    full_name=lead.full_name,
                    email=email,
                    company=lead.company,
                    message=lead.message,
                    interest=lead.interest,
                    source=lead.source,
                    page=lead.page,
                )
                session.add(row)
                await session.flush()
                await self._audit.record(
                    session,
                    action="create",
                    object_type="demo_request",
                    object_id=row.id,
                    actor=System(),
                    tenant_id=None,
                    after=AuditService.snapshot(row, fields=_AUDITED_FIELDS),
                )
                confirm = await self._receipt_due(session, email, received_at)
        except (SQLAlchemyError, OSError) as exc:
            # Not logger.exception: exc_info would print the driver message, which
            # carries the bound parameters, and they are the visitor's details.
            logger.error("leads.store_failed", error=type(exc).__name__)  # noqa: TRY400
            raise ServiceUnavailable(detail="demo request could not be stored") from None

        logger.info("leads.received", lead_id=str(row.id))
        return Delivery(lead_id=row.id, received_at=received_at, confirm=confirm, lead=lead)

    async def deliver(self, delivery: Delivery) -> None:
        """Send the mail a stored request owes. Never raises: it runs after the response,
        where nobody could be told, so a failure is logged by id and the row keeps
        ``notified_at`` NULL as the record that the owner was not told.

        With no owner address configured nothing is sent at all, the receipt included:
        it promises a reply, and with nobody notified there is nobody to give one.
        """
        owner = get_settings().leads.notify_email
        if owner is None:
            logger.info(
                "leads.mail_skipped", lead_id=str(delivery.lead_id), reason="no_owner_address"
            )
            return

        mailer = self._mailer or get_mailer()
        notice = owner_message(delivery.lead, to=owner, received_at=delivery.received_at)
        if await self._send(mailer, notice, delivery.lead_id):
            await self._mark(delivery.lead_id, DemoRequest.notified_at, "notified_at")

        if delivery.confirm:
            receipt = requester_message(to=delivery.lead.email.strip().lower(), reply_to=owner)
            if await self._send(mailer, receipt, delivery.lead_id):
                await self._mark(
                    delivery.lead_id, DemoRequest.confirmation_sent_at, "confirmation_sent_at"
                )

    async def _receipt_due(self, session: AsyncSession, email: str, now: datetime) -> bool:
        """Whether this visitor is owed a receipt: configured on, somebody to reply, and
        none sent to this address in the last day.

        ponytail: two requests for one address landing together can both find no recent
        receipt and both send one. The per address limit bounds that at three a day; claim
        the slot with an UPDATE ... RETURNING before sending if it ever matters.
        """
        cfg = get_settings().leads
        if not (cfg.confirm_requester and cfg.notify_email):
            return False
        recent = (
            select(DemoRequest.id)
            .where(
                DemoRequest.email == email,
                DemoRequest.confirmation_sent_at > now - CONFIRMATION_COOLDOWN,
            )
            .limit(1)
        )
        return (await session.execute(recent)).first() is None

    @staticmethod
    async def _send(mailer: Mailer, message: OutboundEmail, lead_id: uuid.UUID) -> bool:
        """One send, never raising. The mailer already swallows delivery errors; this
        also covers a message that could not be built."""
        try:
            sent = await mailer.send(message)
        except Exception as exc:
            logger.warning(
                "leads.mail_failed",
                lead_id=str(lead_id),
                label=message.log_subject,
                error=type(exc).__name__,
            )
            return False
        if not sent:
            logger.warning("leads.mail_not_sent", lead_id=str(lead_id), label=message.log_subject)
        return sent

    async def _mark(
        self,
        lead_id: uuid.UUID,
        column: InstrumentedAttribute[datetime | None],
        name: str,
    ) -> None:
        """Record, in a short transaction of its own, that a send succeeded.

        Audited like every state change (rule 5): the row says only which timestamp was
        set. The ``IS NULL`` guard makes it idempotent and the audit row exactly-once.
        """
        when = datetime.now(UTC)
        try:
            async with provider_session_scope() as session:
                marked = (
                    await session.execute(
                        update(DemoRequest)
                        .where(DemoRequest.id == lead_id, column.is_(None))
                        .values({name: when})
                        .returning(DemoRequest.id)
                    )
                ).scalar_one_or_none()
                if marked is not None:
                    await self._audit.record(
                        session,
                        action="update",
                        object_type="demo_request",
                        object_id=lead_id,
                        actor=System(),
                        tenant_id=None,
                        before={name: None},
                        after={name: when},
                    )
        except (SQLAlchemyError, OSError) as exc:
            logger.warning(
                "leads.mark_failed", lead_id=str(lead_id), field=name, error=type(exc).__name__
            )


leads_service: Final = LeadsService()
"""The shared instance the router calls. The class stays importable for tests that fake
the mailer."""
