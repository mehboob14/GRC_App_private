"""Suggestions from the company profile (guided onboarding CL-7, part 5 section 4).

Conditions use the one grammar of ``verity.shared.conditions`` (design 3.1). An answer of
"not sure", or no answer, makes a condition unknown, and an unknown condition never produces a
suggestion.

The rules are Python data reviewed like the step catalogue, not a sealed file: each one is a
proposal a person accepts or rejects, never a change made on its own (rule 11 in spirit; the
"Safe to automate" column of part 5 is binding). ``bulk_ok`` is False wherever that column says
"No" or asks for a check before accepting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Final, Literal

from verity.shared.conditions import holds

Kind = Literal["control_status", "iso_applicability", "soc2_category"]


def _is(fact: str, value: str) -> dict[str, Any]:
    return {"fact": fact, "op": "eq", "value": value}


@dataclass(frozen=True, slots=True)
class Rule:
    key: str
    when: dict[str, Any]
    kind: Kind
    subjects: tuple[str, ...]
    """Control codes, or ISO requirement codes."""
    because: str
    """The answer behind it, in the reader's words."""
    reason: str
    """Prefilled reason, edited by the person. ``{company}`` and ``{supplier}`` are filled."""
    payload: dict[str, Any] = field(default_factory=dict)
    bulk_ok: bool = True
    framework: str | None = None
    """The framework the suggestion needs active."""


_SUPPLIER = "Applicable. Operated by {supplier}. {company} relies on its independent assurance report or certificate, reviewed under PE-01, and keeps its own duties for access to these sites."  # noqa: E501
_NA = "Not applicable. {company} does not {activity}. Reassess if that changes."
_EXCLUDED = "Not applicable. {company} does not {activity} within the scope of its management system. No risk in the register calls for this control. Reassess if {trigger}."  # noqa: E501

RULES: Final[tuple[Rule, ...]] = (
    Rule(
        key="no_server_sites.controls",
        when=_is("own_server_sites", "no"),
        kind="control_status",
        subjects=("PE-03",),
        because="You run no data centre, server room or comms cabinet.",
        reason=_NA.format(
            company="{company}", activity="run a data centre, server room or comms cabinet"
        ),
        payload={"status": "not_applicable"},
        bulk_ok=False,  # a person confirms with the provider's report attached
    ),
    Rule(
        key="no_server_sites.iso",
        when=_is("own_server_sites", "no"),
        kind="iso_applicability",
        subjects=("A.7.5", "A.7.8", "A.7.11", "A.7.12", "A.7.13"),
        because="You run no data centre, server room or comms cabinet.",
        reason=_SUPPLIER,
        payload={"applicable": True, "provided_by": "supplier"},
        bulk_ok=False,
        framework="ISO27001",
    ),
    Rule(
        key="no_offices.controls",
        when=_is("offices", "none"),
        kind="control_status",
        subjects=("PE-02",),
        because="You have no offices.",
        reason=_NA.format(company="{company}", activity="have offices"),
        payload={"status": "not_applicable"},
    ),
    Rule(
        key="no_offices.iso",
        when=_is("offices", "none"),
        kind="iso_applicability",
        subjects=("A.7.1", "A.7.2", "A.7.3", "A.7.4", "A.7.6"),
        because="You have no offices.",
        reason=_SUPPLIER,
        payload={"applicable": True, "provided_by": "supplier"},
        framework="ISO27001",
    ),
    Rule(
        key="no_software.controls",
        when=_is("builds_software", "no"),
        kind="control_status",
        subjects=("SD-02", "SD-03", "SD-05", "SD-06", "SD-10", "SD-11", "SD-12", "DM-13", "DM-18"),
        because="You do not build software. Scripts, infrastructure code, websites and low code all count as building.",  # noqa: E501
        reason=_NA.format(company="{company}", activity="develop software in house"),
        payload={"status": "not_applicable"},
        bulk_ok=False,  # CC8.1 still needs a change control; decide each one
    ),
    Rule(
        key="no_software.iso",
        when=_is("builds_software", "no"),
        kind="iso_applicability",
        subjects=("A.8.4", "A.8.25", "A.8.27", "A.8.28", "A.8.29", "A.8.31", "A.8.33"),
        because="You do not build software. Scripts, infrastructure code, websites and low code all count as building.",  # noqa: E501
        reason=_EXCLUDED.format(
            company="{company}",
            activity="develop software",
            trigger="it starts building software in house",
        ),
        payload={"applicable": False, "provided_by": "organization"},
        bulk_ok=False,
        framework="ISO27001",
    ),
    Rule(
        key="no_outside_developers.iso",
        when=_is("outside_developers", "no"),
        kind="iso_applicability",
        subjects=("A.8.30",),
        because="You use no outside developers.",
        reason=_EXCLUDED.format(
            company="{company}",
            activity="outsource development",
            trigger="it engages an outside developer",
        ),
        payload={"applicable": False, "provided_by": "organization"},
        framework="ISO27001",
    ),
    Rule(
        key="employees_only.controls",
        when=_is("workforce_types", "employees"),
        kind="control_status",
        subjects=("HR-03",),
        because="Your workforce is employees only.",
        reason=_NA.format(company="{company}", activity="use contractors"),
        payload={"status": "not_applicable"},
    ),
    Rule(
        key="office_only.iso",
        when=_is("work_arrangement", "office"),
        kind="iso_applicability",
        subjects=("A.6.7",),
        because="Everyone works from an office. Exclude only if no device ever leaves it: on call from home and travel count.",  # noqa: E501
        reason=_EXCLUDED.format(
            company="{company}",
            activity="allow work away from its premises",
            trigger="anyone works from home, travels with a device or is on call",
        ),
        payload={"applicable": False, "provided_by": "organization"},
        bulk_ok=False,
        framework="ISO27001",
    ),
    Rule(
        key="no_subprocessors.controls",
        when=_is("shares_with_subprocessors", "no"),
        kind="control_status",
        subjects=("BC-06",),
        because="You share no customer data with subprocessors. Check your vendor register first.",
        reason=_NA.format(company="{company}", activity="share customer data with subprocessors"),
        payload={"status": "not_applicable"},
        bulk_ok=False,  # a vendor holding personal data contradicts the answer
    ),
    Rule(
        key="no_public_app.controls",
        when=_is("public_app", "no"),
        kind="control_status",
        subjects=("NS-10",),
        because="You run no application open to the internet.",
        reason=_NA.format(company="{company}", activity="run an application open to the internet"),
        payload={"status": "not_applicable"},
    ),
)

SOC2_CATEGORIES: Final[tuple[str, ...]] = (
    "Availability",
    "Confidentiality",
    "Processing Integrity",
    "Privacy",
)

_SUPPLIERS: Final[dict[str, str]] = {
    "aws": "AWS",
    "azure": "Microsoft Azure",
    "gcp": "Google Cloud",
}


def supplier_name(answers: dict[str, Any]) -> str:
    named = [_SUPPLIERS[h] for h in answers.get("hosting_providers") or [] if h in _SUPPLIERS]
    return " and ".join(named) if named else "your hosting and office providers"


def firing(answers: dict[str, Any], frameworks: set[str]) -> list[Rule]:
    """The rules whose condition holds for these answers and frameworks."""
    return [
        r
        for r in RULES
        if (r.framework is None or r.framework in frameworks) and holds(r.when, answers) is True
    ]


@dataclass(frozen=True, slots=True)
class GuidanceNote:
    """A note shown on a control for a company like this one (part 5 section 4, the rows that
    switch guidance rather than applicability). Shipped control text is not changed."""

    when: dict[str, Any]
    controls: tuple[str, ...]
    note: str


_CARD = ("BC-08", "PE-01", "PE-03", "IAM-06", "IAM-07", "IAM-09", "NS-06", "NS-07", "GOV-16",
         "GOV-23", "LM-11", "DM-18", "EP-07", "BC-05")  # fmt: skip

GUIDANCE: Final[tuple[GuidanceNote, ...]] = (
    GuidanceNote(
        {"fact": "device_model", "op": "eq", "value": "personal"},
        ("EP-01", "EP-02", "EP-03", "EP-04", "EP-05", "EP-06", "EP-07"),
        "Your staff use their own devices. Apply this control to every device that reaches "
        "company data, through enrolment or a browser only access policy.",
    ),
    GuidanceNote(
        {"fact": "sensitive_data", "op": "contains", "value": "card_stored"},
        _CARD,
        "You store card data, so the card data parts of this control apply in full and so "
        "does PCI DSS.",
    ),
    GuidanceNote(
        {"fact": "sensitive_data", "op": "contains", "value": "card_outsourced"},
        _CARD,
        "A payment provider handles card data for you. Keep its PCI attestation on file; the "
        "pages that send customers to it are still yours to protect.",
    ),
    GuidanceNote(
        {"fact": "sensitive_data", "op": "contains", "value": "health"},
        ("EP-01", "EP-07", "GOV-15", "HR-08", "IAM-03"),
        "You hold health data. Treat it as your most sensitive class of data here.",
    ),
    GuidanceNote(
        {"fact": "oversight_body", "op": "eq", "value": "executive_team"},
        ("GOV-02", "GOV-21"),
        "Oversight is by your executive team. Record who sits on it and when it meets; a "
        "record of independent members is not needed.",
    ),
    GuidanceNote(
        {"fact": "personal_data_role", "op": "eq", "value": "processor"},
        ("DM-03", "DM-07", "DM-15"),
        "You handle personal data for your customers. Your part is supporting them as the "
        "controller, as your contracts set out.",
    ),
    GuidanceNote(
        {"fact": "personal_data_role", "op": "eq", "value": "staff_only"},
        ("DM-03", "DM-05", "DM-11"),
        "You hold staff personal data only. Keep this for staff records; the customer data "
        "parts do not apply to you.",
    ),
    GuidanceNote(
        {"fact": "affects_customer_financial_reporting", "op": "eq", "value": "yes"},
        ("GOV-14", "IAM-09", "GOV-12", "SD-08", "SD-09"),
        "Your service affects customers' financial reporting, so they may ask for a SOC 1 "
        "report. See the SOC 1 guide.",
    ),
)


def notes_for(code: str, answers: dict[str, Any]) -> list[str]:
    return [
        g.note for g in GUIDANCE if g.note and code in g.controls and holds(g.when, answers) is True
    ]
