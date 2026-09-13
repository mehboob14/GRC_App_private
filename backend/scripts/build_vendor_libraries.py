"""Build the two questionnaire libraries the builder copies from, beside the core bank.

Run: ``python scripts/build_vendor_libraries.py`` from ``backend/``. Writes
``src/verity/seed/content/vendor_tiering/`` and ``.../vendor_profile/``, one bank
each, in the shape the seed loader already reads for ``vendor_questionnaire``.

**Tiering is not due diligence.** The tiering library is what our own business
owner answers about how we use a vendor: what data, what access, how much depends
on it. Its option scores measure exposure, and a high total means a high tier. The
vendor never sees it. The core bank and the vendor profile are what the vendor
answers about themselves, and their option scores measure control strength.

The tiering library's ``lite`` level is the five factors of spec paragraph 82 with
V6's weights (30, 25, 20, 15, 10) and its 0 to 4 scale, so a tenant that starts
from "Standard" tiers exactly as the platform did before questionnaires existed.
``core`` adds the questions a fuller intake asks. Weights are relative: the score
is points over the most points the answered questions could have given, times 100.

Authored for Verity. No SIG, CAIQ or HECVAT text is reproduced (V13).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Final

CONTENT: Final = Path(__file__).resolve().parent.parent / "src/verity/seed/content"


def _scale(*labels: str) -> list[dict[str, Any]]:
    """A 0 to 4 exposure scale, one option per step, keyed by position."""
    return [
        {"key": f"level_{score}", "label": label, "score": score}
        for score, label in enumerate(labels)
    ]


def _option(key: str, label: str, score: float, **extra: object) -> dict[str, Any]:
    return {"key": key, "label": label, "score": score, **extra}


# -- tiering ------------------------------------------------------------------

TIERING_TEMPLATE: Final[dict[str, Any]] = {
    "code": "verity-inherent-risk",
    "name": "Inherent risk",
    "version": "2026.1",
    "description": "Answered by your team about how you use a vendor. Sets the tier.",
    "suggested_tiers": [],
    "framework_mappings": [],
    "built_in": True,
    # The legacy dispatch path picks the current due diligence bank; a tiering
    # library must never be a candidate for it.
    "is_current": False,
    "purpose": "tiering",
}

TIERING_QUESTIONS: Final[list[dict[str, Any]]] = [
    # -- lite: spec paragraph 82's five factors, V6's weights ---------------------
    {
        "code": "tier.data.sensitivity",
        "section": "Data",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "What is the most sensitive data this vendor will store, process or access?",
        "help_text": "Pick the most sensitive kind, even if it is a small share of what they hold.",
        "weight": 30,
        "options": _scale(
            "No data is shared",
            "Public or non identifying data",
            "Internal business data",
            "Personal data",
            "Special category, health or payment data",
        ),
    },
    {
        "code": "tier.business.criticality",
        "section": "Operations",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "How much of the business depends on this service?",
        "weight": 25,
        "options": _scale(
            "Nothing depends on them",
            "A convenience, work continues without them",
            "A team is degraded within days",
            "A revenue or delivery process stops",
            "The business stops",
        ),
    },
    {
        "code": "tier.system.access",
        "section": "Access",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "What access will the vendor have to our systems?",
        "weight": 20,
        "options": _scale(
            "No access to our systems",
            "Read only access to one system",
            "Write access to one system",
            "Access across several systems",
            "Privileged or administrative access",
        ),
    },
    {
        "code": "tier.regulatory.scope",
        "section": "Compliance",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "How far does this engagement reach into regulated or audited scope?",
        "weight": 15,
        "options": _scale(
            "Out of scope for everything",
            "Internal policy only",
            "In scope for one framework",
            "In scope for several frameworks",
            "Named in a regulatory filing or audit",
        ),
    },
    {
        "code": "tier.fourth.party",
        "section": "Fourth parties",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "How well do we know who they rely on to deliver this service?",
        "weight": 10,
        "options": _scale(
            "No subprocessors",
            "One known subprocessor",
            "Several, all declared",
            "Several, some undeclared",
            "Unknown or unmanaged chain",
        ),
    },
    # -- core: a fuller intake ----------------------------------------------------
    {
        "code": "tier.data.types",
        "section": "Data",
        "scope_level": "core",
        "answer_type": "multi_choice",
        "body": "Which kinds of data are involved?",
        "help_text": "Select all that apply. The riskiest pick is what counts.",
        "weight": 10,
        "options": [
            _option("none", "None", 0),
            _option("customer_personal", "Customer personal data", 3),
            _option("employee", "Employee or HR data", 3),
            _option("source_code", "Source code or intellectual property", 3),
            _option("payment", "Payment card or bank data", 4, min_tier="high"),
            _option("health", "Health data", 4, min_tier="high"),
            _option("secrets", "Credentials, keys or secrets", 4, min_tier="high"),
        ],
    },
    {
        "code": "tier.data.volume",
        "section": "Data",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "Roughly how many people's records will they hold?",
        "weight": 10,
        "options": [
            _option("none", "None", 0),
            _option("thousand", "Fewer than 1,000", 1),
            _option("hundred_thousand", "1,000 to 100,000", 2),
            _option("million", "100,000 to 1 million", 3),
            _option("more", "More than 1 million", 4),
        ],
    },
    {
        "code": "tier.data.location",
        "section": "Data",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "Where will our data be stored or processed?",
        "weight": 5,
        "options": [
            _option("not_stored", "It is not stored", 0),
            _option("approved", "Only in regions we have approved", 1),
            _option("unapproved", "Outside the regions we have approved", 3),
            _option("unknown", "Unknown", 4),
        ],
    },
    {
        "code": "tier.access.method",
        "section": "Access",
        "scope_level": "core",
        "answer_type": "multi_choice",
        "body": "How will they connect to us?",
        "help_text": "Select all that apply.",
        "weight": 10,
        "options": [
            _option("none", "No connection", 0),
            _option("sso", "Our staff sign in to their app", 1),
            _option("api", "API or data integration", 2),
            _option("network", "Network or VPN access", 3),
            _option("production", "Access to production infrastructure", 4, min_tier="high"),
        ],
    },
    {
        "code": "tier.ops.outage",
        "section": "Operations",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "If the service stopped, how soon would we feel it?",
        "weight": 10,
        "options": [
            _option("never", "No noticeable impact", 0),
            _option("week", "After more than a week", 1),
            _option("days", "Within a few days", 2),
            _option("day", "Within a day", 3),
            _option("now", "Immediately", 4),
        ],
    },
    {
        "code": "tier.ops.substitute",
        "section": "Operations",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "How hard would they be to replace?",
        "weight": 5,
        "options": [
            _option("easy", "Easy, there are several alternatives", 0),
            _option("month", "Possible within a month", 2),
            _option("hard", "Hard, a long migration", 3),
            _option("sole", "Not possible, they are the only source", 4),
        ],
    },
    {
        "code": "tier.ops.spend",
        "section": "Operations",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "What is the expected annual spend?",
        "weight": 5,
        "options": [
            _option("small", "Under 10,000", 0),
            _option("modest", "10,000 to 50,000", 1),
            _option("medium", "50,000 to 250,000", 2),
            _option("large", "250,000 to 1 million", 3),
            _option("major", "Over 1 million", 4),
        ],
    },
    {
        "code": "tier.tech.ai",
        "section": "Technology",
        "scope_level": "core",
        "answer_type": "single_choice",
        "body": "Will the vendor use AI on our data?",
        "weight": 5,
        "options": [
            _option("no", "No", 0),
            _option("inference", "Yes, without training on our data", 2),
            _option("training", "Yes, and they train models on our data", 4, min_tier="medium"),
        ],
    },
    {
        "code": "tier.context.notes",
        "section": "Context",
        "scope_level": "core",
        "answer_type": "paragraph",
        "body": "Anything else a reviewer should know about this engagement?",
        "required": False,
        "weight": 1,
    },
]

# -- vendor profile (due diligence) ---------------------------------------------

PROFILE_TEMPLATE: Final[dict[str, Any]] = {
    "code": "verity-vendor-profile",
    "name": "Vendor profile and assurance",
    "version": "2026.1",
    "description": "Company details, attestations and the reports behind them.",
    "suggested_tiers": ["critical", "high", "medium", "low"],
    "framework_mappings": ["SOC2", "ISO27001"],
    "built_in": True,
    "is_current": False,
    "purpose": "due_diligence",
}

PROFILE_QUESTIONS: Final[list[dict[str, Any]]] = [
    {
        "code": "vp.company.legal_name",
        "section": "Company",
        "domain": "compliance_legal",
        "scope_level": "lite",
        "answer_type": "text",
        "body": "Legal name of the company providing the service",
    },
    {
        "code": "vp.company.country",
        "section": "Company",
        "domain": "compliance_legal",
        "scope_level": "lite",
        "answer_type": "text",
        "body": "Country where the company is incorporated",
    },
    {
        "code": "vp.company.employees",
        "section": "Company",
        "domain": "personnel_security",
        "scope_level": "lite",
        "answer_type": "number",
        "body": "How many employees does the company have?",
    },
    {
        "code": "vp.company.security_contact",
        "section": "Company",
        "domain": "incident_response",
        "scope_level": "lite",
        "answer_type": "text",
        "body": "Email address we should use for security matters",
    },
    {
        "code": "vp.assurance.attestations",
        "section": "Assurance",
        "domain": "information_security",
        "scope_level": "lite",
        "answer_type": "multi_choice",
        "body": "Which independent attestations do you currently hold?",
        "help_text": "Select all that are current today.",
        "weight": 2.0,
        "options": [
            _option("soc2_type2", "SOC 2 Type II", 100),
            _option("soc2_type1", "SOC 2 Type I", 60),
            _option("iso27001", "ISO 27001", 100),
            _option("pci_dss", "PCI DSS", 100),
            _option("none", "None", 0, flag=True),
        ],
        "framework_refs": ["SOC2:CC2.3", "ISO27001:A.5.35"],
    },
    {
        "code": "vp.assurance.soc2_report",
        "section": "Assurance",
        "domain": "information_security",
        "scope_level": "lite",
        "answer_type": "file",
        "body": "Upload your most recent SOC 2 report",
        "condition": {
            "question_code": "vp.assurance.attestations",
            "option_keys": ["soc2_type2", "soc2_type1"],
        },
    },
    {
        "code": "vp.assurance.iso_certificate",
        "section": "Assurance",
        "domain": "information_security",
        "scope_level": "lite",
        "answer_type": "file",
        "body": "Upload your ISO 27001 certificate",
        "condition": {"question_code": "vp.assurance.attestations", "option_keys": ["iso27001"]},
    },
    {
        "code": "vp.assurance.pentest_date",
        "section": "Assurance",
        "domain": "secure_development",
        "scope_level": "lite",
        "answer_type": "date",
        "body": "When was your last independent penetration test?",
    },
    {
        "code": "vp.assurance.pentest_summary",
        "section": "Assurance",
        "domain": "secure_development",
        "scope_level": "lite",
        "answer_type": "file",
        "body": "Upload the executive summary of that test",
        "required": False,
    },
    {
        "code": "vp.insurance.cyber",
        "section": "Insurance",
        "domain": "compliance_legal",
        "scope_level": "lite",
        "answer_type": "single_choice",
        "body": "Do you carry cyber liability insurance?",
        "options": [
            _option("yes", "Yes", 100),
            _option("no", "No", 0, flag=True),
        ],
    },
    {
        "code": "vp.insurance.cover",
        "section": "Insurance",
        "domain": "compliance_legal",
        "scope_level": "lite",
        "answer_type": "number",
        "body": "Amount of cyber cover, in your currency",
        "required": False,
        "condition": {"question_code": "vp.insurance.cyber", "option_keys": ["yes"]},
    },
]


def _row(index: int, question: dict[str, Any]) -> dict[str, Any]:
    """Fill every column the loader writes, so the JSON is the whole row."""
    return {
        "code": question["code"],
        "position": index,
        "body": question["body"],
        "section": question.get("section"),
        "help_text": question.get("help_text"),
        "domain": question.get("domain"),
        "scope_level": question["scope_level"],
        "answer_type": question["answer_type"],
        "options": question.get("options", []),
        "required": question.get("required", True),
        "weight": float(question.get("weight", 1.0)),
        "critical_control": question.get("critical_control", False),
        "non_negotiable": question.get("non_negotiable", False),
        "evidence_required": question.get("evidence_required", False),
        "framework_refs": question.get("framework_refs", []),
        # The bank's own branching columns: the loader resolves parent_code to
        # parent_question_id once every question in the pack has an id.
        "parent_code": question["condition"]["question_code"] if "condition" in question else None,
        "trigger_condition": question["condition"]["option_keys"]
        if "condition" in question
        else [],
    }


def _write(pack: str, template: dict[str, Any], questions: list[dict[str, Any]]) -> None:
    out = CONTENT / pack
    out.mkdir(parents=True, exist_ok=True)
    payload = {"template": template, "questions": [_row(i, q) for i, q in enumerate(questions)]}
    body = json.dumps(payload, indent=2, ensure_ascii=False) + chr(10)
    (out / "questionnaire_bank.json").write_text(body, encoding="utf-8")
    manifest = {
        "pack": pack,
        "source": "Authored for Verity. No SIG, CAIQ or HECVAT text is reproduced (V13).",
        "bank": template["code"],
        "version": template["version"],
        "purpose": template["purpose"],
        "questions": len(questions),
        "sha256": {"questionnaire_bank.json": hashlib.sha256(body.encode("utf-8")).hexdigest()},
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + chr(10), encoding="utf-8")
    print(f"wrote {len(questions)} questions to {out}")


if __name__ == "__main__":
    _write("vendor_tiering", TIERING_TEMPLATE, TIERING_QUESTIONS)
    _write("vendor_profile", PROFILE_TEMPLATE, PROFILE_QUESTIONS)
