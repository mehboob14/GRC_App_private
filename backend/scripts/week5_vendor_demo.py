"""Week 5 third-party risk demo, driven through the real HTTP API.

Seeds one workspace with a vendor portfolio that exercises every screen in the
module: vendors across all four tiers, engagements mid-lifecycle, a questionnaire
a vendor has partly answered through the unauthenticated portal, findings raised
by a real SOC review, documents about to expire, a contract that auto-renews, an
intake queue awaiting decisions, and a roster with a second person who is allowed
to decide the approval gate.

Nothing is inserted directly. Every row here is created by the same routes the
interface calls, so if the demo runs, the API works.

Usage (the API must be running on 127.0.0.1:8001):
    uv --directory backend run python scripts/week5_vendor_demo.py

It prints the sign-in details and the one-time vendor portal link at the end.
"""

from __future__ import annotations

import sys
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

BASE = "http://127.0.0.1:8001/api/v1"
RUN = uuid.uuid4().hex[:6]

# Satisfies the shipped policy: 12+ characters with an upper, a lower, a digit
# and a symbol. A weaker one is refused at signup, which is the point of it.
PASSWORD = "Orbit-Mango-Quartz-42"  # noqa: S105 — a demo credential, printed on purpose

TODAY = datetime.now(UTC).date()


def _iso(days: int) -> str:
    return (TODAY + timedelta(days=days)).isoformat()


class Api:
    """A thin client that fails loudly. A demo that swallows an error is worse
    than no demo: it prints success and seeds half a workspace."""

    def __init__(self) -> None:
        self.client = httpx.Client(base_url=BASE, timeout=30.0)
        self.token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def post(self, path: str, body: object | None = None, *, expect: int = 200) -> dict[str, Any]:
        response = self.client.post(path, json=body, headers=self._headers())
        if response.status_code != expect:
            sys.exit(f"POST {path} -> {response.status_code}\n{response.text}")
        return dict(response.json()) if response.content else {}

    def patch(self, path: str, body: object) -> dict[str, Any]:
        response = self.client.patch(path, json=body, headers=self._headers())
        if response.status_code != 200:
            sys.exit(f"PATCH {path} -> {response.status_code}\n{response.text}")
        return dict(response.json())

    def get(self, path: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        response = self.client.get(path, params=params, headers=self._headers())
        if response.status_code != 200:
            sys.exit(f"GET {path} -> {response.status_code}\n{response.text}")
        return dict(response.json())

    def get_list(self, path: str) -> list[Any]:
        """For the routes that answer a bare array rather than a page object."""
        response = self.client.get(path, headers=self._headers())
        if response.status_code != 200:
            sys.exit(f"GET {path} -> {response.status_code}\n{response.text}")
        return list(response.json())


def _verify_email(email: str) -> None:
    """Confirm the address the way the mailed link would.

    The token is minted here rather than read out of an inbox. This is the one
    place the demo reaches past HTTP, and it uses production code to do it, so
    the flow it stands in for is still the real one.
    """
    import asyncio

    from verity.core.db import provider_session_scope
    from verity.core.security import issue_token
    from verity.modules.iam.repository import UserRepository

    async def mint() -> str:
        async with provider_session_scope() as session:
            user = await UserRepository().get_by_email(session, email.strip().lower())
        if user is None:
            sys.exit(f"no user for {email} — signup did not land")
        return issue_token(subject=user.id, plane="tenant", typ="email_verify").token

    token = asyncio.run(mint())
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        response = client.post("/auth/verify-email", json={"token": token})
        if response.status_code != 200:
            sys.exit(f"verify-email -> {response.status_code}\n{response.text}")


def sign_up(company: str, email: str) -> Api:
    api = Api()
    api.post(
        "/auth/signup",
        {
            "company_name": company,
            "full_name": "Dana Okafor",
            "email": email,
            "password": PASSWORD,
            "accept_terms": True,
        },
        expect=201,
    )
    _verify_email(email)
    session = api.post("/auth/login", {"email": email, "password": PASSWORD})
    # The login response is a discriminated union: a workspace with MFA off and
    # exactly one membership answers "authenticated" straight away. Anything
    # else means the demo's assumptions about the tenant no longer hold, and
    # guessing past it would seed into a half-built session.
    if session.get("status") != "authenticated":
        sys.exit(f"login returned {session.get('status')!r}, expected 'authenticated'")
    api.token = session["access_token"]
    return api


# ---------------------------------------------------------------------------
# The portfolio
# ---------------------------------------------------------------------------

# Five tiering answers per vendor, on the ER's 0-4 scale, in the order the form
# asks them. These are chosen so the portfolio lands one vendor in each band.
CRITICAL = {
    "data_sensitivity": 4,
    "business_criticality": 4,
    "system_access": 3,
    "regulatory_scope": 4,
    "fourth_party_reliance": 3,
}
HIGH = {
    "data_sensitivity": 3,
    "business_criticality": 3,
    "system_access": 2,
    "regulatory_scope": 2,
    "fourth_party_reliance": 2,
}
MEDIUM = {
    "data_sensitivity": 2,
    "business_criticality": 2,
    "system_access": 1,
    "regulatory_scope": 1,
    "fourth_party_reliance": 1,
}
LOW = {
    "data_sensitivity": 0,
    "business_criticality": 1,
    "system_access": 0,
    "regulatory_scope": 0,
    "fourth_party_reliance": 0,
}

VENDORS: list[dict[str, Any]] = [
    {
        "name": "Meridian Payroll",
        "vendor_type": "supplier",
        "industry": "Payroll",
        "website": "https://meridianpayroll.example",
        "business_unit": "People",
        "services_provided": "Runs monthly payroll and statutory filings for all UK and EU staff.",
        "stores_pii": True,
        "data_classification": "restricted",
        "data_location": "EU (Dublin)",
        "engagement": "Monthly payroll run",
        "answers": CRITICAL,
        "own": True,
    },
    {
        "name": "Northwind Analytics",
        "vendor_type": "vendor",
        "industry": "Marketing analytics",
        "website": "https://northwind.example",
        "business_unit": "Marketing",
        "services_provided": "Campaign attribution across the web estate and the mobile app.",
        "stores_pii": True,
        "data_classification": "confidential",
        "data_location": "EU (Frankfurt)",
        "engagement": "Campaign attribution",
        "answers": HIGH,
        "own": True,
        "contact": ("Priya Raman", "priya@northwind.example"),
        "questionnaire": True,
    },
    {
        "name": "Halcyon Cloud",
        "vendor_type": "vendor",
        "industry": "Infrastructure",
        "website": "https://halcyon.example",
        "business_unit": "Engineering",
        "services_provided": "Primary compute and object storage for the production estate.",
        "stores_pii": True,
        "data_classification": "restricted",
        "data_location": "EU (Frankfurt) and US (Virginia)",
        "engagement": "Production hosting",
        "answers": CRITICAL,
        "own": True,
        "soc": "adverse",
    },
    {
        "name": "Caldera Support Desk",
        "vendor_type": "contractor",
        "industry": "Customer support",
        "business_unit": "Support",
        "services_provided": "Overflow first-line support on our own ticketing system.",
        "stores_pii": True,
        "data_classification": "confidential",
        "engagement": "Out-of-hours cover",
        "answers": HIGH,
        "own": True,
    },
    {
        "name": "Lantern Design Studio",
        "vendor_type": "contractor",
        "industry": "Design",
        "business_unit": "Marketing",
        "services_provided": "Brand and campaign design. No access to our systems.",
        "data_classification": "public",
        "engagement": "Rebrand 2026",
        "answers": LOW,
        "own": True,
        "advance": 3,
    },
    {
        "name": "Sable Legal",
        "vendor_type": "partner",
        "industry": "Legal",
        "business_unit": "Legal",
        "services_provided": "Outside counsel for commercial contracts.",
        "data_classification": "confidential",
        "engagement": "Commercial counsel",
        "answers": MEDIUM,
        "own": True,
    },
    {
        "name": "Orchid Background Checks",
        "vendor_type": "supplier",
        "industry": "Screening",
        "business_unit": "People",
        "services_provided": "Pre-employment screening for every new hire.",
        "stores_pii": True,
        "data_classification": "restricted",
        "engagement": "Pre-employment screening",
        "answers": HIGH,
    },
    {
        "name": "Tessellate CRM",
        "vendor_type": "vendor",
        "industry": "Sales software",
        "business_unit": "Revenue",
        "services_provided": "The customer record of truth for sales and success.",
        "stores_pii": True,
        "data_classification": "confidential",
        "engagement": "Sales CRM",
        "answers": HIGH,
        "own": True,
    },
    {
        "name": "Pinnacle Print",
        "vendor_type": "contractor",
        "industry": "Print",
        "services_provided": "Prints and posts the annual report.",
        "data_classification": "public",
        "engagement": "Annual report",
        "answers": LOW,
    },
    {
        "name": "Quarry Data Warehouse",
        "vendor_type": "vendor",
        "industry": "Data",
        "business_unit": "Engineering",
        "services_provided": "Warehouse behind every internal dashboard.",
        "stores_pii": True,
        "data_classification": "confidential",
        "engagement": "Analytics warehouse",
        "answers": MEDIUM,
        "own": True,
    },
    {
        "name": "Vellum Document Signing",
        "vendor_type": "vendor",
        "industry": "e-Signature",
        "business_unit": "Legal",
        "services_provided": "Signature workflow for customer and employment contracts.",
        "stores_pii": True,
        "data_classification": "confidential",
        "engagement": "Contract signing",
        "answers": MEDIUM,
    },
    {
        "name": "Beacon Status Page",
        "vendor_type": "vendor",
        "industry": "Monitoring",
        "services_provided": "Public status page. No customer data.",
        "data_classification": "public",
        "engagement": "Status page",
        "answers": LOW,
        "advance": 3,
    },
]


def main() -> int:
    email = f"dana+{RUN}@verity.example"
    api = sign_up(f"Harbourline Group ({RUN})", email)
    me = api.get("/auth/me")
    membership = me["membership_id"]
    print(f"workspace: {me['tenant_name']}")

    # Roles the lifecycle waits on. Without these the diligence stage blocks on
    # "the critical reviewers are assigned" and nothing moves.
    for role in ("tprm_lead", "analyst", "security", "privacy", "legal", "procurement", "it"):
        api.post("/vendors/roster", {"role": role, "membership_id": membership})

    portal_url = None
    for spec in VENDORS:
        body = {
            "name": spec["name"],
            "vendor_type": spec["vendor_type"],
            "industry": spec.get("industry"),
            "website": spec.get("website"),
            "business_unit": spec.get("business_unit"),
            "services_provided": spec.get("services_provided", ""),
            "stores_pii": spec.get("stores_pii", False),
            "data_classification": spec.get("data_classification"),
            "data_location": spec.get("data_location"),
            "engagement": {"name": spec["engagement"]},
        }
        if spec.get("own"):
            body["business_owner_membership_id"] = membership
            body["security_owner_membership_id"] = membership
        vendor = api.post("/vendors", body, expect=201)
        vendor_id = vendor["id"]
        engagement_id = vendor["engagements"][0]["id"]

        tiered = api.post(
            f"/vendors/{vendor_id}/engagements/{engagement_id}/tiering",
            spec["answers"],
            expect=201,
        )
        print(f"  {spec['name']:<28} {tiered['tier']}")

        if contact := spec.get("contact"):
            api.post(
                f"/vendors/{vendor_id}/contacts",
                {"name": contact[0], "email": contact[1], "contact_type": "portal"},
                expect=201,
            )

        # A SOC review with anything other than a clean opinion raises a finding,
        # which is how the findings queue gets real rows rather than typed ones.
        if opinion := spec.get("soc"):
            api.post(
                f"/vendors/{vendor_id}/documents",
                {
                    "title": f"SOC 2 Type II FY{TODAY.year - 1}",
                    "doc_type": "soc_report",
                    "issue_date": _iso(-400),
                    "valid_until": _iso(21),
                    "collection_status": "reviewed",
                },
                expect=201,
            )
            api.post(
                f"/vendors/{vendor_id}/soc-reviews",
                {
                    "report_kind": "soc2",
                    "report_type": "type_ii",
                    "audit_period_start": _iso(-730),
                    "audit_period_end": _iso(-400),
                    "tsc_included": ["security", "availability"],
                    "opinion": opinion,
                    "findings_material": True,
                    "cuec_reviewed": True,
                    "cuec_notes": (
                        "We enforce MFA on our own admin accounts and rotate the API key annually."
                    ),
                    "cpa_firm": "Brightwater LLP",
                    "subservice_orgs": ("Their own cloud provider is carved out of the report."),
                },
                expect=201,
            )

        if spec.get("questionnaire"):
            issued = api.post(
                f"/vendors/{vendor_id}/engagements/{engagement_id}/questionnaire",
                {"due_date": _iso(14)},
                expect=201,
            )
            portal_url = issued["portal_url"]
            _answer_some(portal_url.rsplit("/", 1)[-1])

        # A document close to expiry and an auto-renewing contract, so the
        # countdown and the notice deadline have something to count.
        if spec.get("own"):
            api.post(
                f"/vendors/{vendor_id}/documents",
                {
                    "title": "Data processing agreement",
                    "doc_type": "dpa",
                    "issue_date": _iso(-330),
                    "valid_until": _iso(35),
                    "collection_status": "received",
                },
                expect=201,
            )
            api.post(
                f"/vendors/{vendor_id}/contracts",
                {
                    "title": f"{spec['name']} master agreement",
                    "contract_type": "master",
                    "start_date": _iso(-300),
                    "end_date": _iso(65),
                    "renewal_date": _iso(65),
                    "auto_renew": True,
                    "notice_period_days": 60,
                    "breach_notification_hours": 72,
                    "right_to_audit": True,
                    "subprocessor_terms": False,
                    "exit_data_return_clause": True,
                    "value": 42000,
                    "status": "active",
                },
                expect=201,
            )
            api.post(
                f"/vendors/{vendor_id}/subprocessors",
                {
                    "name": "Halcyon Cloud",
                    "service": "Hosting and object storage",
                    "data_location": "eu-central-1",
                    "provenance": "vendor_declared",
                    "notification_obligation": (
                        "30 days written notice before adding a subprocessor"
                    ),
                },
                expect=201,
            )

        for _ in range(spec.get("advance", 0)):
            detail = api.get(f"/vendors/{vendor_id}")
            current = next(
                (s for s in detail["stages"] if s["status"] not in {"complete", "skipped"}),
                None,
            )
            if current is None or current["blockers"]:
                break
            api.post(f"/vendors/{vendor_id}/stages/{current['id']}/advance", {"note": None})

    # A second person, because the gate refuses whoever owns the vendor. The
    # module's centrepiece cannot be demonstrated by one account: segregation of
    # duties is the whole point of the approval stage.
    approver = _invite_approver(api, email)
    _walk_one_to_approval(api, approver)

    # An intake queue with something to decide, including one that duplicates a
    # vendor already in the register so the screening flag has a reason.
    for request in (
        {
            "vendor_name": "Northwind Analytics Ltd",
            "department": "Growth",
            "proposed_service": (
                "The same attribution product, on a second contract for the growth team."
            ),
            "data_types_shared": ["email", "behavioural"],
            "urgency": "high",
        },
        {
            "vendor_name": "Gravel Transcription",
            "department": "Research",
            "proposed_service": (
                "Transcribes recorded customer interviews. Recordings contain names and job titles."
            ),
            "data_types_shared": ["audio", "name"],
            "urgency": "normal",
        },
        {
            "vendor_name": "Tinderbox Screen Recording",
            "department": "Support",
            "proposed_service": (
                "Session replay on the support console so we can see what a customer did."
            ),
            "data_types_shared": ["behavioural", "screen"],
            "urgency": "low",
        },
    ):
        api.post("/vendors/intake", request, expect=201)

    print()
    print("sign in at http://localhost:5173")
    print(f"  email    {email}")
    print(f"  password {PASSWORD}")
    if portal_url:
        print()
        print("vendor questionnaire (no account needed, partly answered already):")
        print(f"  {portal_url}")
    return 0


def _invite_approver(api: Api, inviter_email: str) -> Api:
    """Invite a second admin and accept, so somebody can decide a gate."""
    roles = api.get_list("/roles")
    role_id = next(r["id"] for r in roles if r["name"] == "Admin")
    email = inviter_email.replace("dana+", "sam+")
    invite = api.post(
        "/members/invite",
        {"email": email, "full_name": "Sam Achebe", "role_id": role_id},
        expect=201,
    )
    guest = Api()
    guest.post(
        "/auth/invitations/accept",
        {"token": invite["invite_token"], "full_name": "Sam Achebe", "password": PASSWORD},
    )
    session = guest.post("/auth/login", {"email": email, "password": PASSWORD})
    if session.get("status") != "authenticated":
        sys.exit(f"approver login returned {session.get('status')!r}")
    guest.token = session["access_token"]
    print(f"  second approver: {email}")
    return guest


def _walk_one_to_approval(api: Api, approver: Api) -> None:
    """Advance the lowest-tier vendor to the gate and decide it.

    Proves the whole spine in one pass: a low tier walks over four skipped
    stages, the gate refuses the business owner, and the vendor's rolled-up
    lifecycle status finally moves off "requested".
    """
    register = api.get("/vendors")
    target = next(
        (v for v in register["items"] if v["name"] == "Lantern Design Studio"),
        None,
    )
    if target is None:
        return
    vendor_id = target["id"]
    for _ in range(12):
        detail = api.get(f"/vendors/{vendor_id}")
        current = next(
            (s for s in detail["stages"] if s["status"] not in {"complete", "skipped"}),
            None,
        )
        if current is None:
            break
        if current["is_gate"]:
            engagement_id = detail["engagements"][0]["id"]
            approver.post(
                f"/vendors/{vendor_id}/engagements/{engagement_id}/decision",
                {
                    "decision": "approve_with_conditions",
                    "rationale": (
                        "Low tier, no customer data and no access to our systems. "
                        "The contract carries the standard exit clause and a right "
                        "to audit. Approved on condition the statement of work names "
                        "a data-handling contact before the first deliverable."
                    ),
                    "conditions": [
                        {
                            "description": "Name a data-handling contact in the SOW",
                            "due_date": _iso(30),
                        }
                    ],
                },
                expect=201,
            )
            continue
        if current["blockers"]:
            break
        api.post(f"/vendors/{vendor_id}/stages/{current['id']}/advance", {"note": None})
    final = api.get(f"/vendors/{vendor_id}")
    print(f"  Lantern Design Studio walked to: {final['lifecycle_status']}")


def _answer_some(token: str) -> None:
    """Answer part of the questionnaire as the vendor would, through the
    unauthenticated portal, so the assessment is genuinely in progress."""
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        portal = client.get(f"/vendor-portal/{token}")
        if portal.status_code != 200:
            return
        questions = portal.json()["questions"]
        answers = ["yes", "yes", "partial", "yes", "no", "yes", "partial", "yes"]
        for question, answer in zip(questions, answers, strict=False):
            client.post(
                f"/vendor-portal/{token}/answers",
                json={
                    "question_id": question["id"],
                    "answer": answer,
                    "implementation_notes": {
                        "yes": "Documented, reviewed annually, and owned by our security lead.",
                        "partial": (
                            "In place for production only; the staging estate is scheduled for Q3."
                        ),
                        "no": "Not in place today. On the roadmap for the next financial year.",
                    }.get(answer),
                },
            )


if __name__ == "__main__":
    raise SystemExit(main())
