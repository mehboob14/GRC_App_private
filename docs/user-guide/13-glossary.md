# 13. Glossary

Words this platform uses, and what they mean here. Where a word has a general
industry meaning and a narrower Verity meaning, both are given.

**Acceptance.** A recorded decision to tolerate a risk or a finding rather than fix
it. Always has a justification, an approver who is not the requester, and an expiry
date. When the expiry passes, the thing reopens on its own.

**Acknowledgement campaign.** A targeted request for named people to read and sign a
published document. The record of who signed, and when, is the evidence that a
policy reached its audience.

**Approval gate.** A lifecycle stage that will not clear until specific conditions
are met. The vendor approval stage is one: open findings and unfinished earlier
stages block it.

**Asset.** Anything you run that processes, stores or carries something you care
about: an application, a server, a dataset, a cloud resource, a business service.

**Audit log.** The append only record of every state changing action. Cannot be
edited or deleted by anyone, including an administrator.

**Check.** One automatic test a connected system or a Verity module runs against a control,
for example "the default branch requires a review". Each check names what it collects, which
systems can run it, and how much of the control it proves. A control can have several, and
some of them can need different systems.

**CIA rating.** Confidentiality, integrity and availability, each rated 1 to 5. The
three inputs from which an asset's criticality is derived.

**Control.** Something your organisation does to keep a promise. A control answers
one or more framework criteria and is proven by evidence.

**Criterion.** A single requirement in a framework, for example SOC 2 CC6.1.

**Criticality tier.** Low, medium, high or critical. Derived for assets from the CIA
rating and exposure; derived for vendor engagements from the five tiering questions.

**Definition (vulnerability).** The weakness itself, for example a CVE. Distinct
from a finding, which is that weakness on one of your assets.

**Engagement.** One thing you use a vendor for. A vendor can have several, and each
is tiered and assessed separately.

**EPSS.** Exploit Prediction Scoring System: the probability that a given
vulnerability will be exploited in the wild in the next 30 days.

**Evidence.** An artefact that proves a control operates: a file Verity holds, or a
link to something that lives elsewhere.

**Finding (vendor).** A gap identified in a third party, with a severity, an owner
and a due date.

**Finding (vulnerability).** A weakness on one of your assets at one location.

**Framework.** A published set of criteria you are being measured against, for
example SOC 2.

**Freshness.** How current a piece of evidence is, against the renewal date its type
implies.

**Group.** A team of people in the workspace, usable as an assignee, an approver or
a campaign target.

**Inventory hygiene.** The completeness score on an asset: five checks on the record
plus a freshness clock on when a person last reviewed it.

**KEV.** The Known Exploited Vulnerabilities catalogue published by CISA. A
vulnerability on it is being exploited now, and Verity floors its priority
accordingly.

**Membership.** A person's place in one workspace. All ownership and assignment in
Verity points at a membership, never at a global user, so nobody can be attached to
a workspace they do not belong to.

**Out of date (check result).** A check result more than two days old. It replaces Passing
and Failing, because nothing known is current, and it blocks readiness until the checks run
again.

**Portal (vendor).** The unauthenticated page where a vendor answers a
questionnaire. Reached by a single use link that is shown once.

**Register.** The list view of a module: controls, risks, vendors, assets, findings,
tasks, documents.

**Residual risk.** What is left after your controls act. Contrast inherent risk,
which is the level before they do.

**Review cadence.** How often a record must be revisited. Set per criticality for
assets, per tier for vendors, per document for policies.

**Scope.** What is in and out of an audit, and why.

**Separation of duties.** The rule that the person who requests something cannot be
the person who approves it. Enforced on risk acceptance and the vendor approval
gate.

**Service level (SLA).** A promise about how quickly work of a given priority or
severity is completed. Breaches are visible and escalate.

**Shadow IT.** Software in use that never went through intake. Recorded as a
discovered app and triaged into a vendor, a link to an existing vendor, or ignored
with a reason.

**Soon.** A badge marking a screen that is not built yet. Nothing behind one holds
real data.

**Subprocessor.** A third party your vendor relies on. Your fourth party.

**Tiering.** The five question assessment that decides how much diligence a vendor
engagement earns.

**Trust Services Criteria.** The five SOC 2 categories: Security, Availability,
Processing Integrity, Confidentiality and Privacy.

**Workspace.** One organisation's sealed area of Verity. A person may belong to
several and sees one at a time.
