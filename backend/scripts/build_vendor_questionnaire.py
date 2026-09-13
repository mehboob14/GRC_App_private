"""Build the Verity vendor questionnaire pack from the authored bank below.

Run: ``python scripts/build_vendor_questionnaire.py`` from ``backend/``. Writes
``src/verity/seed/content/vendor_questionnaire/`` — the JSON the seed loader
reads — plus its MANIFEST. The bank is authored here and generated there, the
same way the SOC 2 and policy packs are built.

**V13.** SIG, CAIQ and HECVAT question text belongs to Shared Assessments, CSA and
EDUCAUSE respectively, and none of it is reproduced here. This bank is written for
Verity and covers the same ground; ``framework_refs`` names the SOC 2 criteria and
ISO 27001 Annex A controls each question speaks to **by identifier only**, so an
auditor recognises the coverage without any licensed wording being copied.

**V8.** The ten risk domains the ER refers to and names nowhere.

Three scope levels size the questionnaire to the tier (spec ¶82):

- ``lite``   — every vendor answers these. Low tier stops here.
- ``core``   — medium and above.
- ``detail`` — critical and high only.

``critical_control`` is the small set whose ``no`` floors the residual score at
"high" no matter how good the rest of the answers are (V7). ``non_negotiable`` is
the smaller set whose ``no`` raises a **blocking** finding, which the approval gate
will not pass. Every question key is stable and is what a response row references,
so a later version of the bank can add and retire questions without orphaning a
single historical answer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final, NamedTuple

BANK_KEY: Final = "verity-core"
BANK_VERSION: Final = "2026.1"
BANK_NAME: Final = "Verity third-party security review"

FRAMEWORK_MAPPINGS: Final[tuple[str, ...]] = ("SOC2", "ISO27001")


class Question(NamedTuple):
    key: str
    domain: str
    scope_level: str
    body: str
    weight: float = 1.0
    answer_type: str = "yes_no_na"
    critical_control: bool = False
    non_negotiable: bool = False
    evidence_required: bool = False
    framework_refs: tuple[str, ...] = ()
    # Choices for a question that is not yes/partial/no/na. Only the builder reads
    # these, when a tenant copies the question; the portal's older rows ignore them.
    options: tuple[dict[str, object], ...] = ()


Q: Final[tuple[Question, ...]] = (
    # -- information security programme ---------------------------------------
    Question(
        key="is.policy.approved",
        domain="information_security",
        scope_level="lite",
        body="Do you maintain an information security policy that is approved by "
        "management and reviewed at least annually?",
        weight=2.0,
        evidence_required=True,
        framework_refs=("SOC2:CC1.1", "SOC2:CC5.3", "ISO27001:A.5.1"),
    ),
    Question(
        key="is.owner.named",
        domain="information_security",
        scope_level="lite",
        body="Is there a named individual accountable for information security at "
        "your organisation?",
        framework_refs=("SOC2:CC1.3", "ISO27001:A.5.2"),
    ),
    Question(
        key="is.risk.assessment",
        domain="information_security",
        scope_level="core",
        body="Do you carry out a documented information security risk assessment at "
        "least annually?",
        weight=1.5,
        framework_refs=("SOC2:CC3.2", "ISO27001:A.5.7"),
    ),
    Question(
        key="is.independent.audit",
        domain="information_security",
        scope_level="core",
        body="Have you completed an independent security audit or certification in "
        "the last 12 months (SOC 2, ISO 27001, or equivalent)?",
        weight=2.5,
        evidence_required=True,
        framework_refs=("SOC2:CC9.2",),
    ),
    Question(
        key="is.asset.inventory",
        domain="information_security",
        scope_level="core",
        body="Do you maintain an inventory of the systems and data assets used to "
        "deliver this service?",
        framework_refs=("SOC2:CC6.1", "ISO27001:A.5.9"),
    ),
    Question(
        key="is.metrics.reported",
        domain="information_security",
        scope_level="detail",
        body="Are security metrics reported to executive management on a regular cadence?",
        weight=0.8,
        framework_refs=("SOC2:CC4.2",),
    ),
    Question(
        key="is.exception.process",
        domain="information_security",
        scope_level="detail",
        body="Is there a documented process for granting, time-boxing and reviewing "
        "exceptions to security policy?",
        framework_refs=("SOC2:CC5.3",),
    ),
    # -- access control --------------------------------------------------------
    Question(
        key="ac.mfa.admin",
        domain="access_control",
        scope_level="lite",
        body="Is multi-factor authentication enforced for all administrative and "
        "privileged access to the systems handling our data?",
        weight=3.0,
        critical_control=True,
        non_negotiable=True,
        evidence_required=True,
        framework_refs=("SOC2:CC6.1", "SOC2:CC6.6", "ISO27001:A.5.17"),
    ),
    Question(
        key="ac.revocation.termination",
        domain="access_control",
        scope_level="lite",
        body="Is access revoked within one business day when a member of staff "
        "leaves or changes role?",
        weight=3.0,
        critical_control=True,
        framework_refs=("SOC2:CC6.2", "SOC2:CC6.3", "ISO27001:A.5.18"),
    ),
    Question(
        key="ac.least.privilege",
        domain="access_control",
        scope_level="core",
        body="Is access to customer data granted on a least-privilege basis and "
        "approved by a named owner?",
        weight=2.0,
        framework_refs=("SOC2:CC6.1", "SOC2:CC6.3"),
    ),
    Question(
        key="ac.access.review",
        domain="access_control",
        scope_level="core",
        body="Do you review user access rights at least quarterly and record the outcome?",
        weight=1.5,
        evidence_required=True,
        framework_refs=("SOC2:CC6.2", "ISO27001:A.5.18"),
    ),
    Question(
        key="ac.shared.accounts",
        domain="access_control",
        scope_level="core",
        body="Are shared or generic accounts prohibited, or individually attributable "
        "where they cannot be avoided?",
        framework_refs=("SOC2:CC6.1",),
    ),
    Question(
        key="ac.sso.supported",
        domain="access_control",
        scope_level="detail",
        body="Do you support SAML or OIDC single sign-on for customer administrators?",
        weight=0.8,
        framework_refs=("SOC2:CC6.1",),
    ),
    Question(
        key="ac.privileged.session",
        domain="access_control",
        scope_level="detail",
        body="Are privileged sessions logged and the logs retained for at least 12 months?",
        weight=1.5,
        framework_refs=("SOC2:CC6.1", "SOC2:CC7.2"),
    ),
    # -- data protection and privacy -------------------------------------------
    Question(
        key="dp.encryption.transit",
        domain="data_protection_privacy",
        scope_level="lite",
        body="Is customer data encrypted in transit using TLS 1.2 or higher?",
        weight=3.0,
        critical_control=True,
        non_negotiable=True,
        framework_refs=("SOC2:CC6.7", "ISO27001:A.8.24"),
    ),
    Question(
        key="dp.encryption.rest",
        domain="data_protection_privacy",
        scope_level="lite",
        body="Is customer data encrypted at rest?",
        weight=3.0,
        critical_control=True,
        framework_refs=("SOC2:CC6.7", "ISO27001:A.8.24"),
    ),
    Question(
        key="dp.data.location",
        domain="data_protection_privacy",
        scope_level="lite",
        body="Can you state every country in which our data is stored or processed?",
        weight=2.0,
        answer_type="text",
        framework_refs=("SOC2:CC6.1", "ISO27001:A.5.34"),
    ),
    Question(
        key="dp.deletion.on.exit",
        domain="data_protection_privacy",
        scope_level="core",
        body="Will you return or securely destroy all customer data within 30 days of "
        "contract termination, and certify that you have done so?",
        weight=2.5,
        critical_control=True,
        framework_refs=("SOC2:CC6.5", "ISO27001:A.5.10"),
    ),
    Question(
        key="dp.retention.defined",
        domain="data_protection_privacy",
        scope_level="core",
        body="Do you have documented data retention periods for the data we share with you?",
        framework_refs=("SOC2:CC6.5", "ISO27001:A.5.33"),
    ),
    Question(
        key="dp.dsr.support",
        domain="data_protection_privacy",
        scope_level="core",
        body="Can you support data subject access, correction and erasure requests "
        "within statutory timeframes?",
        weight=1.5,
        framework_refs=("SOC2:P5.1", "SOC2:P6.1"),
    ),
    Question(
        key="dp.key.management",
        domain="data_protection_privacy",
        scope_level="detail",
        body="Are encryption keys managed in a dedicated key management service with "
        "documented rotation?",
        weight=1.5,
        framework_refs=("SOC2:CC6.7", "ISO27001:A.8.24"),
    ),
    Question(
        key="dp.segregation",
        domain="data_protection_privacy",
        scope_level="detail",
        body="Is customer data logically or physically segregated from that of other customers?",
        weight=2.0,
        framework_refs=("SOC2:CC6.1",),
    ),
    # -- business continuity and resilience ------------------------------------
    Question(
        key="bc.plan.documented",
        domain="business_continuity",
        scope_level="lite",
        body="Do you maintain a documented business continuity and disaster recovery "
        "plan for this service?",
        weight=1.5,
        evidence_required=True,
        framework_refs=("SOC2:A1.2", "ISO27001:A.5.29"),
    ),
    Question(
        key="bc.backup.tested",
        domain="business_continuity",
        scope_level="core",
        body="Are backups taken at least daily and restore-tested at least annually?",
        weight=2.5,
        critical_control=True,
        framework_refs=("SOC2:A1.2", "ISO27001:A.8.13"),
    ),
    Question(
        key="bc.rto.rpo",
        domain="business_continuity",
        scope_level="core",
        body="Can you state a recovery time objective and recovery point objective "
        "for this service?",
        answer_type="text",
        framework_refs=("SOC2:A1.2",),
    ),
    Question(
        key="bc.dr.exercise",
        domain="business_continuity",
        scope_level="detail",
        body="Have you exercised your disaster recovery plan in the last 12 months?",
        weight=1.5,
        evidence_required=True,
        framework_refs=("SOC2:A1.3", "ISO27001:A.5.30"),
    ),
    Question(
        key="bc.redundancy",
        domain="business_continuity",
        scope_level="detail",
        body="Is the service deployed across more than one availability zone or data centre?",
        framework_refs=("SOC2:A1.2",),
    ),
    # -- incident response ------------------------------------------------------
    Question(
        key="ir.plan.documented",
        domain="incident_response",
        scope_level="lite",
        body="Do you have a documented security incident response plan with named roles?",
        weight=1.5,
        framework_refs=("SOC2:CC7.3", "ISO27001:A.5.24"),
    ),
    Question(
        key="ir.breach.notification",
        domain="incident_response",
        scope_level="lite",
        body="Will you notify us of a security incident affecting our data within "
        "72 hours of becoming aware of it?",
        weight=3.0,
        critical_control=True,
        non_negotiable=True,
        framework_refs=("SOC2:CC7.4", "SOC2:CC7.5", "ISO27001:A.5.26"),
    ),
    Question(
        key="ir.logging.monitoring",
        domain="incident_response",
        scope_level="core",
        body="Are security events centrally logged and monitored for the systems "
        "handling our data?",
        weight=2.0,
        framework_refs=("SOC2:CC7.2", "ISO27001:A.8.15"),
    ),
    Question(
        key="ir.tabletop",
        domain="incident_response",
        scope_level="core",
        body="Have you run an incident response exercise in the last 12 months?",
        framework_refs=("SOC2:CC7.3",),
    ),
    Question(
        key="ir.breaches.disclosed",
        domain="incident_response",
        scope_level="core",
        body="Have you suffered a security breach affecting customer data in the last 24 months?",
        weight=2.0,
        answer_type="text",
        framework_refs=("SOC2:CC7.4",),
        options=(
            {"key": "no", "label": "No", "score": 100},
            {
                "key": "yes",
                "label": "Yes",
                "score": 0,
                "flag": True,
                "comment_required": True,
            },
        ),
    ),
    Question(
        key="ir.forensics.retained",
        domain="incident_response",
        scope_level="detail",
        body="Do you retain forensic evidence and provide incident reports to affected "
        "customers on request?",
        framework_refs=("SOC2:CC7.4", "ISO27001:A.5.28"),
    ),
    # -- secure development -----------------------------------------------------
    Question(
        key="sd.sdlc.documented",
        domain="secure_development",
        scope_level="lite",
        body="Do you follow a documented secure software development lifecycle?",
        framework_refs=("SOC2:CC8.1", "ISO27001:A.8.25"),
    ),
    Question(
        key="sd.code.review",
        domain="secure_development",
        scope_level="core",
        body="Is every production code change peer-reviewed before release?",
        weight=1.5,
        framework_refs=("SOC2:CC8.1", "ISO27001:A.8.32"),
    ),
    Question(
        key="sd.env.separation",
        domain="secure_development",
        scope_level="core",
        body="Are development, test and production environments separated, with no "
        "production customer data used in test?",
        weight=2.0,
        framework_refs=("SOC2:CC8.1", "ISO27001:A.8.31"),
    ),
    Question(
        key="sd.dependency.scanning",
        domain="secure_development",
        scope_level="core",
        body="Do you scan third-party dependencies for known vulnerabilities on every build?",
        framework_refs=("SOC2:CC7.1", "ISO27001:A.8.8"),
    ),
    Question(
        key="sd.pentest.annual",
        domain="secure_development",
        scope_level="detail",
        body="Is an independent penetration test performed at least annually, with "
        "findings remediated?",
        weight=2.0,
        evidence_required=True,
        framework_refs=("SOC2:CC4.1", "ISO27001:A.8.29"),
    ),
    Question(
        key="sd.secrets.management",
        domain="secure_development",
        scope_level="detail",
        body="Are application secrets held in a secrets manager rather than in source "
        "code or configuration files?",
        weight=1.5,
        framework_refs=("SOC2:CC6.1", "ISO27001:A.8.24"),
    ),
    # -- infrastructure and cloud ----------------------------------------------
    Question(
        key="ic.patching.sla",
        domain="infrastructure_cloud",
        scope_level="lite",
        body="Do you patch critical vulnerabilities in production within 30 days of disclosure?",
        weight=2.5,
        critical_control=True,
        framework_refs=("SOC2:CC7.1", "ISO27001:A.8.8"),
    ),
    Question(
        key="ic.vuln.scanning",
        domain="infrastructure_cloud",
        scope_level="core",
        body="Are infrastructure vulnerability scans run at least monthly?",
        weight=1.5,
        framework_refs=("SOC2:CC7.1", "ISO27001:A.8.8"),
    ),
    Question(
        key="ic.endpoint.protection",
        domain="infrastructure_cloud",
        scope_level="core",
        body="Is endpoint protection deployed and centrally managed on systems with "
        "access to customer data?",
        framework_refs=("SOC2:CC6.8", "ISO27001:A.8.7"),
    ),
    Question(
        key="ic.network.segmentation",
        domain="infrastructure_cloud",
        scope_level="detail",
        body="Is the environment holding customer data network-segmented from corporate systems?",
        weight=1.5,
        framework_refs=("SOC2:CC6.6", "ISO27001:A.8.22"),
    ),
    Question(
        key="ic.iac.reviewed",
        domain="infrastructure_cloud",
        scope_level="detail",
        body="Is infrastructure defined as code, version-controlled and reviewed "
        "before deployment?",
        weight=0.8,
        framework_refs=("SOC2:CC8.1",),
    ),
    Question(
        key="ic.cloud.provider",
        domain="infrastructure_cloud",
        scope_level="core",
        body="Which cloud providers or data centres host this service?",
        answer_type="text",
        framework_refs=("SOC2:CC9.2",),
    ),
    # -- personnel security -----------------------------------------------------
    Question(
        key="ps.background.checks",
        domain="personnel_security",
        scope_level="lite",
        body="Are background checks performed on staff with access to customer data, "
        "where local law permits?",
        weight=1.5,
        framework_refs=("SOC2:CC1.4", "ISO27001:A.6.1"),
    ),
    Question(
        key="ps.security.training",
        domain="personnel_security",
        scope_level="core",
        body="Do all staff complete security awareness training at induction and at "
        "least annually?",
        framework_refs=("SOC2:CC1.4", "ISO27001:A.6.3"),
    ),
    Question(
        key="ps.confidentiality.agreements",
        domain="personnel_security",
        scope_level="core",
        body="Are staff bound by confidentiality agreements covering customer data?",
        framework_refs=("SOC2:CC1.1", "ISO27001:A.6.6"),
    ),
    Question(
        key="ps.phishing.simulation",
        domain="personnel_security",
        scope_level="detail",
        body="Do you run phishing simulations and remediate with additional training?",
        weight=0.8,
        framework_refs=("SOC2:CC1.4",),
    ),
    # -- compliance and legal ---------------------------------------------------
    Question(
        key="cl.dpa.willing",
        domain="compliance_legal",
        scope_level="lite",
        body="Will you enter into a data processing agreement covering the personal data we share?",
        weight=2.0,
        non_negotiable=True,
        framework_refs=("SOC2:P4.2", "ISO27001:A.5.34"),
    ),
    Question(
        key="cl.right.to.audit",
        domain="compliance_legal",
        scope_level="core",
        body="Will you accept a contractual right for us to audit your controls, or "
        "provide an independent report in lieu?",
        weight=1.5,
        framework_refs=("SOC2:CC9.2",),
    ),
    Question(
        key="cl.regulatory.scope",
        domain="compliance_legal",
        scope_level="core",
        body="Which regulatory regimes apply to your handling of our data (GDPR, "
        "HIPAA, PCI DSS, other)?",
        answer_type="multi_select",
        framework_refs=("SOC2:CC2.3",),
        options=(
            {"key": "gdpr", "label": "GDPR", "score": 0},
            {"key": "hipaa", "label": "HIPAA", "score": 0},
            {"key": "pci_dss", "label": "PCI DSS", "score": 0},
            {"key": "sox", "label": "SOX", "score": 0},
            {"key": "ccpa", "label": "CCPA or CPRA", "score": 0},
            {"key": "none", "label": "None of these", "score": 0},
            {"key": "other", "label": "Other", "score": 0, "comment_required": True},
        ),
    ),
    Question(
        key="cl.insurance.cyber",
        domain="compliance_legal",
        scope_level="detail",
        body="Do you carry cyber liability insurance, and can you evidence the cover?",
        weight=0.8,
        evidence_required=True,
        framework_refs=("SOC2:CC9.1",),
    ),
    Question(
        key="cl.sanctions.screening",
        domain="compliance_legal",
        scope_level="detail",
        body="Do you screen your organisation and principals against sanctions lists?",
        weight=0.8,
        framework_refs=("SOC2:CC2.3",),
    ),
    # -- fourth-party management ------------------------------------------------
    Question(
        key="fp.subprocessors.disclosed",
        domain="fourth_party_management",
        scope_level="lite",
        body="Can you provide a current list of the subprocessors who will handle our data?",
        weight=2.5,
        critical_control=True,
        framework_refs=("SOC2:CC9.2", "ISO27001:A.5.21"),
    ),
    Question(
        key="fp.change.notification",
        domain="fourth_party_management",
        scope_level="core",
        body="Will you notify us before adding or changing a subprocessor that handles our data?",
        weight=2.0,
        framework_refs=("SOC2:CC9.2", "ISO27001:A.5.22"),
    ),
    Question(
        key="fp.due.diligence",
        domain="fourth_party_management",
        scope_level="core",
        body="Do you perform security due diligence on your own suppliers before onboarding them?",
        weight=1.5,
        framework_refs=("SOC2:CC9.2", "ISO27001:A.5.19"),
    ),
    Question(
        key="fp.flow.down",
        domain="fourth_party_management",
        scope_level="detail",
        body="Are your security and privacy obligations to us flowed down "
        "contractually to your subprocessors?",
        weight=1.5,
        framework_refs=("SOC2:CC9.2", "ISO27001:A.5.20"),
    ),
    Question(
        key="fp.concentration",
        domain="fourth_party_management",
        scope_level="detail",
        body="Have you assessed the concentration risk of your critical suppliers?",
        weight=0.8,
        framework_refs=("SOC2:CC9.2",),
    ),
)

# Which questions each tier is asked (spec ¶82: the tier right-sizes the depth).
BUNDLE_BY_TIER: Final[dict[str, tuple[str, ...]]] = {
    "critical": ("lite", "core", "detail"),
    "high": ("lite", "core", "detail"),
    "medium": ("lite", "core"),
    "low": ("lite",),
}


def build() -> None:
    """Write the pack. Deterministic: the same bank produces byte-identical JSON."""
    out = Path(__file__).resolve().parent.parent / "src/verity/seed/content/vendor_questionnaire"
    out.mkdir(parents=True, exist_ok=True)

    template = {
        "code": BANK_KEY,
        "name": BANK_NAME,
        "version": BANK_VERSION,
        "description": (
            "Verity's own third-party security review. Covers the same ground as the "
            "industry questionnaires and reproduces none of their text; framework_refs "
            "names the criteria each question speaks to by identifier."
        ),
        "suggested_tiers": ["critical", "high", "medium", "low"],
        "framework_mappings": list(FRAMEWORK_MAPPINGS),
        "built_in": True,
        "is_current": True,
        "purpose": "due_diligence",
    }
    questions = [
        {
            "code": q.key,
            "position": index,
            "body": q.body,
            "domain": q.domain,
            "scope_level": q.scope_level,
            "answer_type": q.answer_type,
            "weight": q.weight,
            "critical_control": q.critical_control,
            "non_negotiable": q.non_negotiable,
            "evidence_required": q.evidence_required,
            "framework_refs": list(q.framework_refs),
            "options": [dict(option) for option in q.options],
        }
        for index, q in enumerate(Q)
    ]
    payload = {"template": template, "questions": questions}

    body = json.dumps(payload, indent=2, ensure_ascii=False) + chr(10)
    (out / "questionnaire_bank.json").write_text(body, encoding="utf-8")

    manifest = {
        "pack": "vendor_questionnaire",
        "source": "Authored for Verity. No SIG, CAIQ or HECVAT text is reproduced (V13).",
        "bank": BANK_KEY,
        "version": BANK_VERSION,
        "questions": len(questions),
        "by_scope_level": {
            level: sum(1 for q in Q if q.scope_level == level)
            for level in ("lite", "core", "detail")
        },
        "critical_controls": sum(1 for q in Q if q.critical_control),
        "non_negotiable": sum(1 for q in Q if q.non_negotiable),
        "sha256": {"questionnaire_bank.json": hashlib.sha256(body.encode("utf-8")).hexdigest()},
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + chr(10), encoding="utf-8")
    print(f"wrote {len(questions)} questions to {out}")


if __name__ == "__main__":
    build()
