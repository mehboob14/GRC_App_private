"""The vendor questionnaire portal — the platform's only unauthenticated write path.

Everything in this file is written on the assumption that the caller is hostile
until the token says otherwise, because there is no session, no principal and no
permission check upstream of it.

**The sequence is fixed, and the order is the security property.**

1. **Rate-limit before touching the database.** Two buckets: every resolve is
   counted against the *token*, and only a failed one is counted against the
   *caller*. Keying the first on the caller would be the obvious choice and the
   wrong one — behind the reverse proxy every request shares one address, so that
   bucket would be global and a few hundred junk requests would take the portal
   down for every tenant.
2. **Hash and look up in ``vendor_portal_tokens``**, in a short transaction with
   **no tenant bound**, which then *closes*. That table is on the global plane and
   has no policy — see its model for why it must be, and why it holds nothing but
   a hash and the pair it resolves to.
3. **Open the real unit of work with the resolved tenant bound.** Only now does any
   tenant-owned row become reachable, and every query still filters ``tenant_id``
   explicitly: row-level security is the second wall, never the mechanism.
4. **Re-check the token inside that transaction** — expiry, revocation, and the
   assessment's own state. Step 2 proved the token exists; step 4 proves it is
   still allowed to do this, and the two are not the same question.
5. **Audit as the vendor contact**, not as the system. Rule 5 wants an actor, and
   "who answered this question" is the first thing an auditor asks about a vendor
   questionnaire.

**The two transactions are never merged.** ``provider_session_scope`` is the
nearest-looking precedent in this codebase and is the trap: it binds a second
setting that widens every dual-plane policy, and doing that on a request driven by
an externally supplied token would make ``audit_log`` readable across every tenant
for the life of the transaction. This module never touches the provider plane.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Final

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.core import ratelimit
from verity.core.db import session_scope
from verity.core.errors import InvalidInput, NotFound
from verity.core.rls import require_tenant_context
from verity.modules.audit.service import AuditService, System, VendorContact, audit_service
from verity.modules.vendors.models import (
    ANSWER_VALUES,
    RISK_DOMAIN_LABELS,
    VendorAssessment,
    VendorAssessmentResponse,
    VendorPortalToken,
)

logger: Final = structlog.get_logger(__name__)

# One flat message for every way a token can fail to work. Deliberately identical
# for "no such token", "expired", "revoked" and "already submitted": an
# unauthenticated caller learns whether a token exists from a message that
# distinguishes them, and there is nothing they can do with any of the four
# answers that they cannot do with one.
_LINK_UNUSABLE: Final = (
    "This questionnaire link is not valid. It may have expired, been replaced by a "
    "newer link, or the review may already be complete. Contact whoever sent it to you."
)

# Answers that assert the control exists, and therefore owe evidence when the
# question demands it. "no" and "na" claim nothing, so they owe nothing.
_CLAIMS_A_CONTROL: Final[frozenset[str]] = frozenset(("yes", "partial"))

# Statuses in which the portal will accept a write.
_OPEN_STATUSES: Final[frozenset[str]] = frozenset(("pending", "in_progress"))


@dataclass(frozen=True, slots=True)
class _Resolved:
    """What step 2 learned, before any tenant was bound."""

    tenant_id: uuid.UUID
    assessment_id: uuid.UUID
    token_hash: str


@dataclass(frozen=True, slots=True)
class PortalQuestion:
    """One question as the vendor sees it.

    Note what is absent: ``weight``, ``critical_control`` and ``non_negotiable``.
    Those are how *we* score the answer, and showing them would tell a vendor
    exactly which questions to answer generously.
    """

    id: uuid.UUID
    code: str
    body: str
    domain: str
    domain_label: str
    answer_type: str
    evidence_required: bool
    answer: str | None
    implementation_notes: str | None
    na_justification: str | None
    has_evidence: bool


@dataclass(frozen=True, slots=True)
class PortalView:
    """The whole of what a token grants sight of: one questionnaire.

    No vendor list, no other assessments, no scores, no findings, no internal
    names. A contact who holds a token can see the questions they were asked and
    the answers they have given, and nothing else in the tenant.
    """

    assessment_id: uuid.UUID
    organisation: str
    vendor_name: str
    status: str
    due_date: date | None
    question_count: int
    answered_count: int
    submitted_at: datetime | None
    questions: list[PortalQuestion]


class VendorPortalService:
    """Token-authenticated, session-less access to exactly one questionnaire."""

    def __init__(self, audit: AuditService | None = None) -> None:
        self._audit = audit or audit_service

    # -- resolution ------------------------------------------------------------

    async def _resolve(self, token: str, *, client_host: str | None) -> _Resolved:
        """Turn a token into (tenant, assessment), or refuse.

        Runs in its own transaction with no tenant bound, and that transaction is
        closed before the caller opens the tenant-bound one.
        """
        # Two buckets, and which one a request consumes is the point. Every
        # resolve costs a lookup; only a *failed* one costs a guess. Charging
        # successes to the brute-force bucket would lock a vendor out of their own
        # questionnaire partway through answering it.
        caller = ratelimit.client_identity(client_host)
        token_hash = ratelimit.hash_token(token)
        # Keyed on the token, not the caller: behind the reverse proxy every
        # request shares one address, so a per-address bucket here would be one
        # global bucket and a few hundred junk requests would take the portal down
        # for every tenant. Guessing is bounded by the failure bucket below.
        await ratelimit.check(
            "portal_lookup", ratelimit.token_identity(token_hash), ratelimit.PORTAL_LOOKUPS
        )
        now = datetime.now(UTC)
        async with session_scope(None) as session:
            row = (
                await session.execute(
                    select(VendorPortalToken).where(VendorPortalToken.token_hash == token_hash)
                )
            ).scalar_one_or_none()
            if row is None or row.revoked_at is not None or row.expires_at <= now:
                logger.info(
                    "portal.token_rejected",
                    fingerprint=ratelimit.token_fingerprint(token),
                    reason="unknown" if row is None else "revoked_or_expired",
                )
                await ratelimit.check("portal_failures", caller, ratelimit.PORTAL_TOKEN_FAILURES)
                raise NotFound(_LINK_UNUSABLE, detail="portal token unusable")
            resolved = _Resolved(
                tenant_id=row.tenant_id, assessment_id=row.assessment_id, token_hash=token_hash
            )
            row.last_used_at = now
        return resolved

    async def _assessment(
        self, session: AsyncSession, resolved: _Resolved, *, for_write: bool
    ) -> VendorAssessment:
        """Load the one assessment this token may see, re-checking it can be used.

        Asserts the wall is up first. An unbound session returns zero rows rather
        than raising, so a missing bind would look like a clean 404 and nothing
        would ever catch it.
        """
        bound = await require_tenant_context(session)
        if bound != resolved.tenant_id:
            raise NotFound(_LINK_UNUSABLE, detail="portal tenant binding mismatch")

        assessment = (
            await session.execute(
                select(VendorAssessment)
                .where(VendorAssessment.tenant_id == resolved.tenant_id)
                .where(VendorAssessment.id == resolved.assessment_id)
            )
        ).scalar_one_or_none()
        if assessment is None:
            raise NotFound(_LINK_UNUSABLE, detail="portal assessment gone")
        if for_write and assessment.status not in _OPEN_STATUSES:
            raise NotFound(_LINK_UNUSABLE, detail=f"assessment is {assessment.status}")
        return assessment

    @staticmethod
    def _actor(assessment: VendorAssessment) -> VendorContact:
        """Who the audit row names. Never optional.

        Rule 5 wants an actor on every state change, and an assessment always has
        a contact by construction — ``issue_questionnaire`` refuses to mint a token
        without one. If that ever stops being true this fails loudly rather than
        writing an unattributed row: an audit trail with a silent gap in it is
        worse than one that stopped.
        """
        if assessment.portal_contact_id is None:
            raise NotFound(_LINK_UNUSABLE, detail=f"assessment {assessment.id} has no contact")
        return VendorContact(assessment.portal_contact_id)

    # -- reads -----------------------------------------------------------------

    async def open_portal(self, token: str, *, client_host: str | None) -> PortalView:
        resolved = await self._resolve(token, client_host=client_host)
        async with session_scope(resolved.tenant_id) as session:
            assessment = await self._assessment(session, resolved, for_write=False)
            if assessment.status == "pending":
                # First visit. Recorded so "sent but never opened" and "opened and
                # abandoned" are different things on the internal screen — and
                # audited, because it is a state change and rule 5 has no exception
                # for small ones.
                assessment.status = "in_progress"
                await self._audit.record(
                    session,
                    action="update",
                    object_type="vendor_assessment",
                    object_id=assessment.id,
                    actor=self._actor(assessment),
                    tenant_id=resolved.tenant_id,
                    before={"status": "pending"},
                    after={"status": "in_progress", "event": "portal_first_opened"},
                )
            return await self._view(session, resolved, assessment)

    async def _view(
        self, session: AsyncSession, resolved: _Resolved, assessment: VendorAssessment
    ) -> PortalView:
        from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

        rows = await vendor_service.answers_with_questions(
            session, tenant_id=resolved.tenant_id, assessment_id=assessment.id
        )
        vendor = await vendor_service.get_ref(
            session, tenant_id=resolved.tenant_id, vendor_id=assessment.vendor_id
        )
        return PortalView(
            assessment_id=assessment.id,
            organisation=await vendor_service.tenant_display_name(
                session, tenant_id=resolved.tenant_id
            ),
            vendor_name=vendor.name,
            status=assessment.status,
            due_date=assessment.due_date,
            question_count=len(rows),
            answered_count=sum(1 for r, _ in rows if r.answer),
            submitted_at=assessment.submitted_at,
            questions=[
                PortalQuestion(
                    id=question.id,
                    code=question.code,
                    body=question.body,
                    domain=question.domain,
                    domain_label=RISK_DOMAIN_LABELS[question.domain],
                    answer_type=question.answer_type,
                    evidence_required=question.evidence_required,
                    answer=response.answer,
                    implementation_notes=response.implementation_notes,
                    na_justification=response.na_justification,
                    has_evidence=response.evidence_id is not None,
                )
                for response, question in rows
            ],
        )

    # -- writes ----------------------------------------------------------------

    async def save_answer(  # noqa: PLR0913
        self,
        token: str,
        *,
        client_host: str | None,
        question_id: uuid.UUID,
        answer: str,
        implementation_notes: str | None = None,
        na_justification: str | None = None,
    ) -> PortalView:
        resolved = await self._resolve(token, client_host=client_host)
        await ratelimit.check(
            "portal_write", ratelimit.token_identity(resolved.token_hash), ratelimit.PORTAL_WRITES
        )
        if answer not in ANSWER_VALUES:
            raise InvalidInput(
                "That is not one of the available answers.",
                detail=f"answer={answer!r} not in {ANSWER_VALUES}",
            )
        if answer == "na" and not (na_justification or "").strip():
            raise InvalidInput(
                "Tell us why this does not apply. An unexplained 'not applicable' "
                "cannot be reviewed.",
                detail="na without a justification",
            )

        async with session_scope(resolved.tenant_id) as session:
            assessment = await self._assessment(session, resolved, for_write=True)
            response = await self._response(session, resolved, assessment, question_id)
            before = AuditService.snapshot(response, fields=("answer", "na_justification"))
            response.answer = answer
            response.implementation_notes = (implementation_notes or "").strip() or None
            response.na_justification = (na_justification or "").strip() or None
            response.answered_at = datetime.now(UTC)
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_assessment_response",
                object_id=response.id,
                actor=self._actor(assessment),
                tenant_id=resolved.tenant_id,
                before=before,
                after={"answer": answer, "na_justification": response.na_justification},
            )
            await session.flush()
            return await self._view(session, resolved, assessment)

    async def _response(
        self,
        session: AsyncSession,
        resolved: _Resolved,
        assessment: VendorAssessment,
        question_id: uuid.UUID,
    ) -> VendorAssessmentResponse:
        """The row for this question **on this assessment**, or nothing.

        Scoped to the assessment the token resolved to, so a token cannot be used
        to write an answer onto a different review by supplying its question id.
        Rows are created at dispatch, so a question that was never asked has no
        row and cannot be answered into existence.
        """
        response = (
            await session.execute(
                select(VendorAssessmentResponse)
                .where(VendorAssessmentResponse.tenant_id == resolved.tenant_id)
                .where(VendorAssessmentResponse.assessment_id == assessment.id)
                .where(VendorAssessmentResponse.question_id == question_id)
            )
        ).scalar_one_or_none()
        if response is None:
            raise NotFound(
                "That question is not part of this questionnaire.",
                detail=f"question {question_id} not on assessment {assessment.id}",
            )
        return response

    async def attach_evidence(
        self,
        token: str,
        *,
        client_host: str | None,
        question_id: uuid.UUID,
        filename: str,
        data: bytes,
    ) -> PortalView:
        """Accept a file from an unauthenticated party, through the one validator.

        No new upload path. ``evidence_service.add_file`` goes through
        ``core.storage``, which sniffs magic bytes against an allowlist, refuses
        markup masquerading as text, caps the size while streaming and hashes what
        it wrote. Re-implementing any of that here would be a second, weaker copy
        of the same guarantee.
        """
        resolved = await self._resolve(token, client_host=client_host)
        await ratelimit.check(
            "portal_upload", ratelimit.token_identity(resolved.token_hash), ratelimit.PORTAL_UPLOADS
        )
        async with session_scope(resolved.tenant_id) as session:
            assessment = await self._assessment(session, resolved, for_write=True)
            response = await self._response(session, resolved, assessment, question_id)
            actor = self._actor(assessment)

            from verity.modules.evidence.service import evidence_service  # noqa: PLC0415

            evidence = await evidence_service.add_file(
                session,
                tenant_id=resolved.tenant_id,
                actor=actor,
                title=f"Vendor questionnaire response: {filename}",
                filename=filename,
                data=data,
                evidence_type="other",
                collected_at=datetime.now(UTC).date(),
                source_label="vendor portal",
            )
            replaced = response.evidence_id
            response.evidence_id = evidence.id
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_assessment_response",
                object_id=response.id,
                actor=actor,
                tenant_id=resolved.tenant_id,
                before={"evidence_id": str(replaced) if replaced else None},
                # The replaced id is kept in the trail rather than only the new
                # one: re-uploading detaches the previous file, and an auditor
                # asking "what did they first send us" needs somewhere to look.
                after={"evidence_id": str(evidence.id), "filename": filename},
            )
            await session.flush()
            return await self._view(session, resolved, assessment)

    async def submit(self, token: str, *, client_host: str | None) -> PortalView:
        """Hand the questionnaire back, and score it.

        Refuses while questions are unanswered, because a partial submission that
        scores is worse than no score: it produces a residual number that looks
        like a review and is not one.
        """
        resolved = await self._resolve(token, client_host=client_host)
        await ratelimit.check(
            "portal_write", ratelimit.token_identity(resolved.token_hash), ratelimit.PORTAL_WRITES
        )
        async with session_scope(resolved.tenant_id) as session:
            assessment = await self._assessment(session, resolved, for_write=True)

            from verity.modules.vendors.service import vendor_service  # noqa: PLC0415

            rows = await vendor_service.answers_with_questions(
                session, tenant_id=resolved.tenant_id, assessment_id=assessment.id
            )
            unanswered = [q.code for r, q in rows if not r.answer]
            if unanswered:
                raise InvalidInput(
                    f"{len(unanswered)} question(s) still need an answer before you can submit.",
                    detail=f"unanswered: {unanswered[:5]}",
                )
            # Any positive claim needs its proof, not only an unqualified yes. A
            # "partial" is still an assertion that the control exists in some form,
            # and enforcing this against "yes" alone would let a vendor buy a
            # scored review by downgrading every answer one notch.
            missing = [
                q.code
                for r, q in rows
                if q.evidence_required and r.answer in _CLAIMS_A_CONTROL and not r.evidence_id
            ]
            if missing:
                raise InvalidInput(
                    f"{len(missing)} answer(s) need a supporting document attached before "
                    "you can submit.",
                    detail=f"missing evidence: {missing[:5]}",
                )

            now = datetime.now(UTC)
            # Read before the write. A hardcoded before-snapshot is a trail that
            # says what the code assumed rather than what the row held.
            was = assessment.status
            assessment.status = "submitted"
            assessment.submitted_at = now
            await self._audit.record(
                session,
                action="update",
                object_type="vendor_assessment",
                object_id=assessment.id,
                actor=self._actor(assessment),
                tenant_id=resolved.tenant_id,
                before={"status": was},
                after={"status": "submitted", "answered": len(rows)},
            )
            await session.flush()

            # Scoring runs immediately, so an internal reviewer opens the record
            # and finds the score and its findings waiting rather than a queue item
            # somebody has to remember to process.
            #
            # As System, not as the contact: the vendor submitted answers, the
            # platform computed a number from them. Attributing the score to the
            # vendor would put their name on our arithmetic, and on the findings
            # it raises against them.
            await vendor_service.score_assessment(
                session,
                tenant_id=resolved.tenant_id,
                actor=System(),
                assessment_id=assessment.id,
            )
            await session.flush()
            return await self._view(session, resolved, assessment)


vendor_portal_service = VendorPortalService()
