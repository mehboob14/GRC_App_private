"""Owner functions: who in the company owns each family of controls (guided onboarding CL-8, OW-1).

Eight functions, mapped to members once; every control gets a proposed owner from its function.
The rule is by control family with named exceptions, from part 5, section 5 of the plan. It is
kept here as one reviewed table instead of a field on 133 shipped templates; a unit test checks
that every shipped control code resolves to a function.
"""

from __future__ import annotations

from typing import Final

FUNCTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("executive_sponsor", "Executive sponsor"),
    ("security_lead", "Security lead"),
    ("engineering_lead", "Engineering lead"),
    ("it_lead", "IT lead"),
    ("hr_lead", "HR lead"),
    ("legal_privacy_lead", "Legal or privacy lead"),
    ("vendor_lead", "Vendor or procurement lead"),
    ("finance_lead", "Finance lead"),
)
FUNCTION_KEYS: Final[frozenset[str]] = frozenset(key for key, _ in FUNCTIONS)

_FAMILY: Final[dict[str, str]] = {
    "GOV": "security_lead",
    "IAM": "it_lead",
    "HR": "hr_lead",
    "SD": "engineering_lead",
    "LM": "engineering_lead",
    "DM": "legal_privacy_lead",
    "NS": "engineering_lead",
    "EP": "it_lead",
    "PE": "it_lead",
    "BC": "engineering_lead",
    "CS": "security_lead",
}

_EXCEPTIONS: Final[dict[str, str]] = {
    # Governance: oversight and objectives sit with the sponsor; people matters with HR.
    "GOV-02": "executive_sponsor",
    "GOV-10": "executive_sponsor",
    "GOV-15": "executive_sponsor",
    "GOV-26": "executive_sponsor",
    # The internal audit must not be owned by the person who owns what it audits.
    "GOV-13": "executive_sponsor",
    "GOV-04": "hr_lead",
    "GOV-11": "hr_lead",
    "GOV-21": "hr_lead",
    "GOV-05": "legal_privacy_lead",
    "GOV-12": "finance_lead",
    "GOV-14": "it_lead",
    "IAM-07": "engineering_lead",
    "IAM-10": "engineering_lead",
    "IAM-09": "finance_lead",
    "HR-08": "security_lead",
    "HR-09": "security_lead",
    "HR-03": "vendor_lead",
    "LM-01": "it_lead",
    "LM-04": "security_lead",
    "LM-05": "security_lead",
    "LM-07": "security_lead",
    "LM-10": "security_lead",
    "LM-11": "security_lead",
    "LM-12": "security_lead",
    "DM-04": "security_lead",
    "DM-06": "engineering_lead",
    "DM-13": "engineering_lead",
    "DM-16": "engineering_lead",
    "DM-18": "engineering_lead",
    "DM-19": "it_lead",
    "NS-11": "it_lead",
    "PE-01": "vendor_lead",
    "BC-05": "it_lead",
    "BC-06": "legal_privacy_lead",
    "BC-07": "vendor_lead",
    "BC-08": "vendor_lead",
    "CS-01": "legal_privacy_lead",
    "CS-02": "legal_privacy_lead",
    "CS-05": "hr_lead",
}


def function_for(code: str) -> str | None:
    """The owner function for a control code; None for a workspace's own control outside the
    shipped families, which keeps whatever owner a person gave it."""
    if code in _EXCEPTIONS:
        return _EXCEPTIONS[code]
    return _FAMILY.get(code.split("-", 1)[0])
