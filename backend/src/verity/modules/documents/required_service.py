"""The Required documents list (guided onboarding RD-1 to RD-7).

Rows come from ``required_documents.REQUIRED``; which rows a workspace sees depends on the
frameworks it runs and its profile answers. Each row's state is computed from the workspace's own
documents: a draft, a document in review, an approved or published one, or nothing yet. A generated
or imported draft never counts as approved (RD-2). Rows the profile hides are listed with the
answer behind them, so nothing disappears without a reason.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Final

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from verity.modules.documents.models import Document, DocumentTemplate
from verity.modules.documents.required_documents import REQUIRED, RequiredDocument

_RANK: Final[dict[str, int]] = {
    "draft": 1,
    "needs_approval": 2,
    "approved": 3,
    "published": 3,
    "expired": 1,
}

_HIDDEN_BECAUSE: Final[dict[str, str]] = {
    "offices": "You said you have no offices.",
    "own_sites": "You said you run no data centre, server room or comms cabinet.",
    "remote": "You said everyone works from an office.",
    "personal_data": "You hold only staff personal data and Privacy is not in your SOC 2 scope.",
    "processing_integrity": "Processing integrity is not in your SOC 2 scope.",
    "builds_software": "You said you do not build software.",
    "availability_or_iso": "Availability is not in your SOC 2 scope and ISO 27001 is not active.",
    "existing_only": "Only shown when you already keep one.",
}


@dataclass(frozen=True, slots=True)
class RequiredRow:
    number: int
    title: str
    kind: str
    template: str | None
    template_available: bool
    product: str | None
    frameworks: list[str]
    controls: list[str]
    acknowledge: bool
    state: str
    """not_started, draft, in_review, approved, review_overdue, in_product, guidance, part_of."""
    document_id: uuid.UUID | None
    owner_membership_id: uuid.UUID | None


@dataclass(frozen=True, slots=True)
class HiddenRow:
    number: int
    title: str
    because: str


@dataclass(frozen=True, slots=True)
class RequiredView:
    rows: list[RequiredRow]
    hidden: list[HiddenRow]
    counted: int
    approved: int
    in_review: int


def _needed(when: str | None, answers: dict[str, Any], facts: dict[str, Any]) -> bool:  # noqa: PLR0911
    """Whether a conditional row applies. An unanswered question keeps the row (conservative)."""
    if when is None:
        return True
    if when == "offices":
        return answers.get("offices") != "none"
    if when == "own_sites":
        return answers.get("own_server_sites") in {"yes", "not_sure", None}
    if when == "remote":
        return answers.get("work_arrangement") != "office"
    if when == "personal_data":
        role = answers.get("personal_data_role")
        return role != "staff_only" or "privacy" in facts["soc2_categories"]
    if when == "processing_integrity":
        return "processing_integrity" in facts["soc2_categories"]
    if when == "builds_software":
        return answers.get("builds_software") != "no"
    if when == "availability_or_iso":
        return "ISO27001" in facts["frameworks"] or "availability" in facts["soc2_categories"]
    if when == "existing_only":
        return bool(facts["has_template"])
    return True


class RequiredDocumentsService:
    async def view(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        answers: dict[str, Any],
        frameworks: set[str],
        soc2_categories: set[str],
    ) -> RequiredView:
        """The list for one workspace. The caller supplies the profile answers, the active
        framework codes and the SOC 2 categories, so this module reads only its own tables."""
        facts: dict[str, Any] = {"frameworks": frameworks, "soc2_categories": soc2_categories}
        docs = list(
            (
                await session.execute(
                    select(Document).where(
                        Document.tenant_id == tenant_id,
                        Document.template_key.is_not(None),
                        Document.archived_at.is_(None),
                    )
                )
            ).scalars()
        )
        best: dict[str, Document] = {}
        for d in docs:
            key = d.template_key or ""
            if key not in best or _RANK.get(d.lifecycle, 0) > _RANK.get(best[key].lifecycle, 0):
                best[key] = d
        shipped = set((await session.execute(select(DocumentTemplate.key))).scalars())
        today = datetime.now(UTC).date()
        rows: list[RequiredRow] = []
        hidden: list[HiddenRow] = []
        for item in REQUIRED:
            if not set(item.frameworks) & facts["frameworks"] and item.frameworks:
                continue
            facts["has_template"] = item.template in best if item.template else False
            if not _needed(item.when, answers, facts):
                hidden.append(
                    HiddenRow(item.number, item.title, _HIDDEN_BECAUSE.get(item.when or "", ""))
                )
                continue
            rows.append(self._row(item, best, shipped, today))
        counted = [r for r in rows if r.kind == "template"]
        return RequiredView(
            rows=rows,
            hidden=hidden,
            counted=len(counted),
            approved=sum(1 for r in counted if r.state == "approved"),
            in_review=sum(1 for r in counted if r.state == "in_review"),
        )

    @staticmethod
    def _row(
        item: RequiredDocument, best: dict[str, Document], shipped: set[str], today: date
    ) -> RequiredRow:
        doc = best.get(item.template) if item.template else None
        if item.kind == "product":
            state = "in_product"
        elif item.kind == "guidance":
            state = "guidance"
        elif item.kind == "part_of":
            state = "part_of"
        elif doc is None:
            state = "not_started"
        elif doc.lifecycle in {"approved", "published"}:
            state = (
                "review_overdue"
                if doc.renewal_date is not None and doc.renewal_date < today
                else "approved"
            )
        elif doc.lifecycle == "needs_approval":
            state = "in_review"
        else:
            state = "draft"
        return RequiredRow(
            number=item.number,
            title=item.title,
            kind=item.kind,
            template=item.template,
            template_available=bool(item.template and item.template in shipped),
            product=item.product,
            frameworks=list(item.frameworks),
            controls=list(item.controls),
            acknowledge=item.acknowledge,
            state=state,
            document_id=doc.id if doc else None,
            owner_membership_id=doc.owner_membership_id if doc else None,
        )


required_documents_service = RequiredDocumentsService()
