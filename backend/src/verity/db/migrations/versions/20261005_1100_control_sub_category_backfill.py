"""Give the controls a workspace already adopted the Sub-type their template ships.

The signed spec gives every control a Type and a Sub-type. Type is the existing
``category``; Sub-type is ``sub_category``. ``d5c2e8a41f07`` added the column to
``control_templates`` and the content pack now authors a value for all 116 shipped
templates, so a workspace that adopted the library earlier holds controls with no
Sub-type. This fills them in.

Two planes move, as the earlier content migrations do:

* ``control_templates`` is global shipped content with no RLS. A template still
  without a Sub-type is given the one in ``SUB_TYPES`` below. The runbook runs
  migrations *before* ``seed-content``, so on a first deploy the column is still
  empty here and the controls would be copied from nothing. The snapshot is carried
  in the migration, a fixed record of what shipped rather than a read of a pack file
  that keeps moving, and only fills templates that are empty, so a vocabulary the
  loader has already refreshed is never rolled back. The loader later finds nothing
  to change.
* ``controls`` holds each tenant's adopted copy. A control whose Sub-type is empty is
  given its template's, so a value a person set is never overwritten, and only while
  the control still sits under the Type the template ships: a Sub-type refines its
  Type, and one that was moved elsewhere has no use for the old Type's areas.
  ``controls`` carries ``FORCE ROW LEVEL SECURITY``, which applies to the owner a
  migration runs as and filters SELECT as well as UPDATE, so a cross-tenant
  backfill matches nothing unless FORCE is lifted. It is lifted for the UPDATE and
  restored in the same transaction.

Re-running changes nothing: only empty values are written.

``downgrade`` is a documented no-op. Once filled, a copied Sub-type cannot be told
from one a person chose, and clearing every value that equals its template would
erase real choices. The template column goes with ``d5c2e8a41f07``; the controls
column predates both.

Revision ID: a3b9c7e15d68
Revises: d5c2e8a41f07
Create Date: 2026-10-05
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "a3b9c7e15d68"
down_revision: str | None = "d5c2e8a41f07"
branch_labels: str | None = None
depends_on: str | None = None

# Template code -> Sub-type, as the soc2 pack ships it at this revision.
# Proposed vocabulary (week2-decisions D1): the client has not confirmed it.
SUB_TYPES: dict[str, str] = {
    # Governance, Risk & Compliance
    "GOV-01": "Policies & Ethics",
    "GOV-02": "Governance & Accountability",
    "GOV-03": "Risk Management",
    "GOV-04": "Policies & Ethics",
    "GOV-05": "Compliance Management",
    "GOV-06": "Audit & Assurance",
    "GOV-07": "Risk Management",
    "GOV-08": "Audit & Assurance",
    "GOV-09": "Governance & Accountability",
    "GOV-10": "Governance & Accountability",
    "GOV-11": "Policies & Ethics",
    "GOV-12": "Risk Management",
    "GOV-13": "Audit & Assurance",
    "GOV-14": "Compliance Management",
    "GOV-15": "Governance & Accountability",
    "GOV-16": "Audit & Assurance",
    "GOV-17": "Policies & Ethics",
    "GOV-18": "Risk Management",
    "GOV-19": "Risk Management",
    "GOV-20": "Risk Management",
    "GOV-21": "Governance & Accountability",
    "GOV-22": "Compliance Management",
    # Communications & Collaboration Security
    "CS-01": "Customer Commitments",
    "CS-02": "Customer Commitments",
    "CS-03": "Reporting Channels",
    "CS-04": "Internal Communication",
    "CS-05": "Reporting Channels",
    # Human Resources & Personnel Security
    "HR-01": "Hiring & Screening",
    "HR-02": "Hiring & Screening",
    "HR-03": "Onboarding & Offboarding",
    "HR-04": "Training & Competence",
    "HR-05": "Onboarding & Offboarding",
    "HR-06": "Onboarding & Offboarding",
    "HR-07": "Training & Competence",
    "HR-08": "Training & Competence",
    # Identity & Access Management
    "IAM-01": "Access Lifecycle",
    "IAM-02": "Access Lifecycle",
    "IAM-03": "Authentication",
    "IAM-04": "Authentication",
    "IAM-05": "Authentication",
    "IAM-06": "Authentication",
    "IAM-07": "Privileged & Service Accounts",
    "IAM-08": "Authorization",
    "IAM-09": "Authorization",
    "IAM-10": "Privileged & Service Accounts",
    "IAM-11": "Authentication",
    "IAM-12": "Access Lifecycle",
    # Infrastructure & Network Security
    "NS-01": "Encryption & Secrets",
    "NS-02": "Encryption & Secrets",
    "NS-03": "Network & Perimeter",
    "NS-04": "Cloud",
    "NS-05": "Cloud",
    "NS-06": "Encryption & Secrets",
    "NS-07": "Network & Perimeter",
    "NS-08": "Network & Perimeter",
    "NS-09": "Encryption & Secrets",
    "NS-10": "Network & Perimeter",
    "NS-11": "Network & Perimeter",
    # Endpoint Security
    "EP-01": "Anti-Malware & XDR",
    "EP-02": "Device Hardening",
    "EP-03": "Device Management",
    "EP-04": "Patch Management",
    "EP-05": "Device Management",
    "EP-06": "Device Hardening",
    # Data Management & Privacy
    "DM-01": "Breach & Disclosure",
    "DM-02": "Breach & Disclosure",
    "DM-03": "Notice & Consent",
    "DM-04": "Data Lifecycle",
    "DM-05": "Individual Rights",
    "DM-06": "Data Lifecycle",
    "DM-07": "Data Handling",
    "DM-08": "Data Lifecycle",
    "DM-09": "Breach & Disclosure",
    "DM-10": "Vendor Agreements",
    "DM-11": "Individual Rights",
    "DM-12": "Data Handling",
    "DM-13": "Data Handling",
    "DM-14": "Individual Rights",
    "DM-15": "Notice & Consent",
    "DM-16": "Data Lifecycle",
    "DM-17": "Vendor Agreements",
    # Secure Development & Code Management
    "SD-01": "Change Management",
    "SD-02": "CI/CD",
    "SD-03": "Application Security",
    "SD-04": "Change Management",
    "SD-05": "Data Processing",
    "SD-06": "Code Review",
    "SD-07": "Data Processing",
    "SD-08": "Data Processing",
    "SD-09": "Data Processing",
    "SD-10": "Secure SDLC",
    "SD-11": "Application Security",
    "SD-12": "Secure SDLC",
    "SD-13": "CI/CD",
    "SD-14": "Change Management",
    # Logging, Monitoring & Incident Management
    "LM-01": "Assets & Vulnerabilities",
    "LM-02": "Security Tooling",
    "LM-03": "Security Tooling",
    "LM-04": "Incident Response",
    "LM-05": "Incident Recovery",
    "LM-06": "Incident Recovery",
    "LM-07": "Incident Response",
    "LM-08": "Incident Response",
    "LM-09": "Security Tooling",
    "LM-10": "Incident Response",
    "LM-11": "Assets & Vulnerabilities",
    # Business Continuity & Third-Party Management
    "BC-01": "Backup & Recovery",
    "BC-02": "Backup & Recovery",
    "BC-03": "Continuity & Capacity",
    "BC-04": "Continuity & Capacity",
    "BC-05": "Vendor Management",
    "BC-06": "Vendor Management",
    "BC-07": "Vendor Management",
    "BC-08": "Vendor Management",
    # Physical & Environmental Security
    "PE-01": "Cloud Providers",
    "PE-02": "Offices",
}

_FILL_TEMPLATE = sa.text(
    "UPDATE control_templates SET sub_category = :sub_category "
    "WHERE code = :code AND sub_category IS NULL"
)

_FILL_CONTROLS = sa.text(
    "UPDATE controls c SET sub_category = t.sub_category "
    "FROM control_templates t "
    "WHERE t.id = c.template_id AND t.sub_category IS NOT NULL "
    "AND c.category = t.category "
    "AND COALESCE(btrim(c.sub_category), '') = ''"
)


def backfill(bind: sa.Connection) -> int:
    """Fill the empty Sub-types; return how many controls were given one."""
    bind.execute(
        _FILL_TEMPLATE,
        [{"code": code, "sub_category": sub} for code, sub in SUB_TYPES.items()],
    )
    bind.execute(sa.text("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY"))
    try:
        filled = bind.execute(_FILL_CONTROLS).rowcount
    finally:
        bind.execute(sa.text("ALTER TABLE controls FORCE ROW LEVEL SECURITY"))
    return filled


def upgrade() -> None:
    backfill(op.get_bind())


def downgrade() -> None:
    """Nothing to undo: see the module docstring."""
