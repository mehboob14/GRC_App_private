"""HTTP for the website's demo-request form, **unauthenticated by design**.

Every management router in this platform declares a permission and gets a principal.
This one cannot: the caller is a prospect reading the marketing site, who has no account
and no session. That is the same footing as ``auth_router`` and ``vendor_portal_router``,
and it is declared the same way: there is no permission dependency on this route because
there is nobody to hold one, and this docstring plus the comment where ``main.py`` mounts
the router are the record that the omission is deliberate (the repository has no
automated route audit to register it with). What stands in for the permission:

1. **Rate limits before any write**, by caller address, by requester address and for the
   whole platform per day (``core.ratelimit.limit_demo_request``). They fail closed.
2. **Strict validation** at the boundary (``schemas.py``): unknown fields refused,
   every field bounded, control characters removed before they reach a database or a
   mail header.
3. **A honeypot** field, answered exactly like a real request and never stored or mailed.
4. **No read path.** The route writes a row and says ``received``; nothing about any
   stored request, or whether an address is already known, is ever returned.
5. **A provider-plane table behind forced row-level security**, so the request handler
   can touch nothing else even if it were wrong.

CORS for this route alone is not decided here: the website is another origin, and
``core.middleware.ScopedCorsMiddleware`` (installed in ``main.create_app`` from
``settings.leads.allowed_origins``) gives exactly this path its policy, errors included.
"""

from __future__ import annotations

from typing import Final

from fastapi import APIRouter, BackgroundTasks, Request, status

from verity.core import ratelimit
from verity.modules.leads.schemas import DemoRequestAccepted, DemoRequestIn
from verity.modules.leads.service import LeadInput, leads_service

_PREFIX: Final = "/public"
_ROUTE: Final = "/demo-requests"

DEMO_REQUESTS_PATH: Final = _PREFIX + _ROUTE
"""The route's path under the API prefix, which is the path its CORS policy is keyed on.
A test asserts the app really serves it here, so a rename cannot quietly drop the CORS."""

leads_router = APIRouter(prefix=_PREFIX, tags=["public"])


@leads_router.post(
    _ROUTE,
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DemoRequestAccepted,
    summary="Ask for a demo (public, no login)",
)
async def create_demo_request(
    body: DemoRequestIn, request: Request, background: BackgroundTasks
) -> DemoRequestAccepted:
    lead = LeadInput(**body.model_dump())
    # A script that filled the hidden field is answered like anyone else and costs
    # nothing: it must not spend the day's ceiling, or an innocent address's allowance.
    if not leads_service.is_honeypot(lead):
        await ratelimit.limit_demo_request(request, lead.email)
    delivery = await leads_service.submit(lead)
    if delivery is not None:
        # After the response, so a visitor never waits on a mail server.
        background.add_task(leads_service.deliver, delivery)
    return DemoRequestAccepted()
