"""Short descriptions for the shipped policy templates.

Each template's ``summary`` was the policy's own opening paragraph cut at 240
characters: long, full of ``{{placeholders}}``, and read as policy text rather
than a description. The picker card and the register's Description column now
show one plain sentence about what the policy covers.

Both places move together, following the control guidance rewrite:

* ``document_templates`` is global shipped content with no RLS, and is updated
  unconditionally to match the pack the application ships.
* ``documents`` copied the summary into ``description`` when a tenant started a
  draft from a template. Only rows whose description is still exactly the
  template's text are refreshed, so a description a person wrote is kept.
  ``documents`` carries ``FORCE ROW LEVEL SECURITY``, which filters the SELECT a
  migration runs as well as the UPDATE, so FORCE is lifted before the rows are
  captured and restored in the same transaction.

The unedited rows are captured *before* the templates move, because "unedited"
means equal to the template's previous text. ``downgrade`` restores the previous
text on the same basis.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "e5a9c3d17b42"
down_revision = "d2f7b0a1e94c"
branch_labels = None
depends_on = None

# (template key, old summary, new summary)
CONTENT: tuple[tuple[str, str, str], ...] = (
    (
        "access-control-policy",
        "To limit access to information and information processing systems, networks, and facilities to authorized parties in accordance with business objectives. Scope All {{company_name}} information systems that process, store, or transmit confid…",
        "Who can access which systems and data, and how access is granted, reviewed and removed.",
    ),
    (
        "asset-management-policy",
        "To identify organizational assets and define appropriate protection responsibilities. To ensure that information receives an appropriate level of protection in accordance with its importance to the organization. To prevent unauthorized disc…",
        "Keeps an inventory of company assets and gives each one an owner responsible for protecting it.",
    ),
    (
        "business-continuity-and-disaster-recovery-plan",
        "The purpose of this business continuity plan is to prepare {{company_name}} in the event of service outages caused by factors beyond our control (e.g., natural disasters, man-made events), and to restore services to the widest extent possib…",
        "How the business keeps running and restores systems and data after an outage or disaster.",
    ),
    (
        "code-of-conduct",
        "The primary goal of {{company_name}}’s Code of Conduct is to foster inclusive, collaborative and safe working conditions for all {{company_name}} staff. As such, {{company_name}} is committed to providing a friendly, safe and welcoming envi…",
        "The standards of behaviour expected from everyone who works for or with the company.",
    ),
    (
        "cryptography-policy",
        "To ensure proper and effective use of cryptography to protect the confidentiality, authenticity and/or integrity of information. This policy establishes requirements for the use and protection of cryptographic keys and cryptographic methods…",
        "When encryption must be used to protect data, and how encryption keys are managed.",
    ),
    (
        "data-management-policy",
        "To ensure that information is classified, protected, retained and securely disposed of in accordance with its importance to the organization. Scope All {{company_name}} data, information and information systems. Policy {{company_name}} clas…",
        "How data is classified, handled, kept and securely disposed of based on how sensitive it is.",
    ),
    (
        "human-resource-security-policy",
        "To ensure that employees and contractors meet security requirements, understand their responsibilities, and are suitable for their roles. Scope This policy applies to all employees of {{company_name}}, consultants, contractors and other thi…",
        "Security steps before, during and after employment, from background checks and training to offboarding.",
    ),
    (
        "incident-response-plan",
        "This document establishes the plan for managing information security incidents and events, and offers guidance for employees or incident responders who believe they have discovered, or are responding to, a security incident. Scope This poli…",
        "How security incidents are reported, investigated, contained and closed, and who is responsible for each step.",
    ),
    (
        "information-security-policy",
        "Overview This Information Security Policy is intended to protect {{company_name}}’s employees, partners and the company from illegal or damaging actions by individuals, either knowingly or unknowingly. Internet/Intranet/Extranet-related sys…",
        "The company's overall approach to protecting information and the security rules every employee follows.",
    ),
    (
        "information-security-roles-and-responsibilities",
        "Statement of Policy {{company_name}} is committed to conducting business in compliance with all applicable laws, regulations, and company policies. {{company_name}} has adopted this policy to outline the security measures required to protec…",
        "Who is responsible for information security and what each role is accountable for.",
    ),
    (
        "operations-security-policy",
        "To ensure the correct and secure operation of information processing systems and facilities. Scope All {{company_name}} information systems that are business critical and/or process, store, or transmit company data. This Policy applies to a…",
        "Keeps production systems running securely through change control, monitoring, backups and patching.",
    ),
    (
        "physical-security-policy",
        "To prevent unauthorized physical access or damage to the organization’s information and information processing facilities. Scope All {{company_name}} offices and locations. This Policy applies to all employees of {{company_name}}, and to al…",
        "Protects offices, equipment and facilities from unauthorised access, damage and theft.",
    ),
    (
        "risk-management-policy",
        "Risk Management Policy Policy Type: Risk Management Policy Company Name: {{company_name}} Policy Owners: &lt;Policy Owners Name and Job Title&gt; Phone: Effective Date: &lt;Date&gt; Date Revised: &lt;Date&gt; Last Review: &lt;Date&gt; Next…",
        "How security risks are identified, assessed, treated and reviewed on a regular schedule.",
    ),
    (
        "secure-development-policy",
        "To ensure that information security is designed and implemented within the development lifecycle for applications and information systems. Scope All {{company_name}} applications and information systems that are business critical and/or pro…",
        "Builds security into software development, from design and code review to testing and release.",
    ),
    (
        "third-party-management-policy",
        "To ensure protection of the organization's data and assets that are shared with, accessible to, or managed by suppliers, including external parties or third-party organizations such as service providers, vendors, and customers, and to maint…",
        "How vendors that handle company data or systems are assessed, contracted and monitored.",
    ),
)

_UNEDITED = sa.text(
    "CREATE TEMPORARY TABLE _unedited_documents ON COMMIT DROP AS "
    "SELECT d.id FROM documents d JOIN document_templates t ON d.template_key = t.key "
    "WHERE d.description IS NOT DISTINCT FROM t.summary"
)

_TEMPLATE = sa.text("UPDATE document_templates SET summary = :summary WHERE key = :key")

_PROPAGATE = sa.text(
    "UPDATE documents d SET description = t.summary "
    "FROM document_templates t "
    "WHERE d.template_key = t.key AND d.id IN (SELECT id FROM _unedited_documents)"
)


def _apply(index: int) -> None:
    bind = op.get_bind()
    # FORCE applies to the owner this migration runs as and filters SELECT too,
    # so it comes off before the read that captures the unedited rows.
    op.execute("ALTER TABLE documents NO FORCE ROW LEVEL SECURITY")
    try:
        bind.execute(_UNEDITED)
        for row in CONTENT:
            bind.execute(_TEMPLATE, {"key": row[0], "summary": row[index]})
        bind.execute(_PROPAGATE)
        bind.execute(sa.text("DROP TABLE _unedited_documents"))
    finally:
        op.execute("ALTER TABLE documents FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _apply(2)


def downgrade() -> None:
    _apply(1)
