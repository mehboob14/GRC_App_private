"""The vendor questionnaire portal's HTTP surface — **unauthenticated by design**.

Every other router in this platform declares a permission and gets a principal.
This one cannot: the caller is a person at a third party who holds a link and has
no account. Read ``portal.py`` before changing anything here; the security
properties live in that service, and these handlers exist only to hand it the
token and the client address.

Four rules this router keeps, and each of them is load-bearing:

1. **The token is a path segment, and the access log redacts it.** A path is the
   lesser of two evils — a query string additionally leaks through referrer
   headers and browser history — but it is *not* free, because this application
   logs `scope["path"]` on every request. `core.middleware.safe_path` replaces the
   segment after `/vendor-portal/` before anything is written, in the access log
   and in all four exception handlers. Change either half and the live credential
   goes to disk on every request for the thirty days the link is valid.
2. **No route here takes an id that selects a tenant or a vendor.** The token
   selects them. Anything else in the path or body is scoped *within* what the
   token already resolved.
3. **The client address reaches the service** so failed resolves can be counted
   against it. A missing address is not a reason to skip the limit — those share
   one bucket. Note that behind the reverse proxy this address is the same for
   every caller, which is why the *lookup* limit is keyed on the token instead.
4. **Errors are flat.** The service raises one indistinguishable error for every
   way a link can fail, and nothing here adds detail to it.

Mounted without the API prefix's auth expectations but under the same versioned
path, so a reverse proxy can route or throttle ``/api/v1/vendor-portal`` as a
distinct surface.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, File, Path, Request, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from verity.modules.vendors.portal import PortalView, vendor_portal_service

vendor_portal_router = APIRouter(prefix="/vendor-portal", tags=["vendor portal"])

# 128 URL-safe characters is generous for a 32-byte token and still refuses an
# obviously absurd path segment before it reaches a hash.
_Token = Annotated[str, Path(min_length=20, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")]


class _Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _Response(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AnswerWrite(_Request):
    question_id: uuid.UUID
    answer: str
    implementation_notes: str | None = Field(default=None, max_length=8000)
    na_justification: str | None = Field(default=None, max_length=4000)


class PortalQuestionOut(_Response):
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


class PortalOut(_Response):
    """Deliberately narrow. A token shows one questionnaire and nothing else —
    no scores, no findings, no other vendors, no internal names."""

    assessment_id: uuid.UUID
    organisation: str
    vendor_name: str
    status: str
    due_date: object | None
    question_count: int
    answered_count: int
    submitted_at: object | None
    questions: list[PortalQuestionOut]


def _client_host(request: Request) -> str | None:
    return request.client.host if request.client else None


def _out(view: PortalView) -> PortalOut:
    return PortalOut.model_validate(view)


@vendor_portal_router.get("/{token}", response_model=PortalOut, summary="Open a questionnaire")
async def open_portal(request: Request, token: _Token) -> PortalOut:
    return _out(await vendor_portal_service.open_portal(token, client_host=_client_host(request)))


@vendor_portal_router.post("/{token}/answers", response_model=PortalOut, summary="Save one answer")
async def save_answer(request: Request, token: _Token, body: AnswerWrite) -> PortalOut:
    return _out(
        await vendor_portal_service.save_answer(
            token,
            client_host=_client_host(request),
            question_id=body.question_id,
            answer=body.answer,
            implementation_notes=body.implementation_notes,
            na_justification=body.na_justification,
        )
    )


@vendor_portal_router.post(
    "/{token}/answers/{question_id}/evidence",
    response_model=PortalOut,
    summary="Attach a supporting document",
)
async def attach_evidence(
    request: Request,
    token: _Token,
    question_id: uuid.UUID,
    file: Annotated[UploadFile, File()],
) -> PortalOut:
    """The bytes go straight to the shared store, which sniffs, caps and hashes.

    No validation happens in this handler on purpose: a second implementation of
    the allowlist is a second place for it to be wrong, and the store's version is
    the one every other upload in the platform already goes through.
    """
    return _out(
        await vendor_portal_service.attach_evidence(
            token,
            client_host=_client_host(request),
            question_id=question_id,
            filename=file.filename or "attachment",
            data=await file.read(),
        )
    )


@vendor_portal_router.post(
    "/{token}/submit", response_model=PortalOut, summary="Submit the questionnaire"
)
async def submit(request: Request, token: _Token) -> PortalOut:
    return _out(await vendor_portal_service.submit(token, client_host=_client_host(request)))
