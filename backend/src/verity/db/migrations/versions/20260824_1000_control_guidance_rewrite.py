"""Rewrite every shipped control's statement and implementation guidance.

The library shipped with a one-line statement and a single-sentence guidance for
almost every control (111 of 114 had guidance under 160 characters), and a later
import left some entries in a casual second-person voice. Both fields are now
written to a consistent professional depth: the statement explains why the
control exists, and the guidance is four concrete implementation steps separated
by newlines, which the UI renders as a list.

Both planes move together, the same way the GOV re-code did:

* ``control_templates`` is global shipped content with no RLS, and is updated
  unconditionally: it must match the pack the application ships.
* ``controls`` holds each tenant's adopted copy. Only rows still identical to
  their template are refreshed, so a tenant that edited its own copy keeps that
  edit. ``controls`` carries ``FORCE ROW LEVEL SECURITY``, which applies to the
  owner a migration runs as, so a cross-tenant UPDATE matches zero rows unless
  FORCE is lifted; it is lifted for the backfill and restored in the same
  transaction.

Ordering matters. The set of unedited rows is captured *before* the templates
move, because "unedited" is defined as equal to the template's previous text.

``downgrade`` restores the previous text on the same basis.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a4c81f37b902"
down_revision = "f3b6d20c48a1"
branch_labels = None
depends_on = None

# (code, old_description, old_guidance, new_description, new_guidance)
CONTENT: tuple[tuple[str, str, str, str, str], ...] = (
    (
        "IAM-01",
        "Every account should have an authorization trail before credentials are issued.",
        "Require documented approval for access requests, especially privileged access, via ticket or workflow.",
        "Access granted without a recorded authorization cannot be shown to be appropriate, and it is the point at which least privilege is either enforced or quietly abandoned. The approval record is what an auditor samples to test the control.",
        "Require a documented request and approval before any account or entitlement is created.\nRoute approval to the system or data owner rather than to the requester's manager alone for privileged access.\nCapture the business justification, so the grant can be re-evaluated at the next access review.\nProvision only after approval is recorded, and reject retrospective approvals as a matter of process.",
    ),
    (
        "IAM-02",
        "Recertifying access catches privilege creep and missed removals.",
        "Run access-review campaigns (quarterly for critical systems) where owners certify each user, and verify revocations execute.",
        "Access accumulates. People change roles, projects end and temporary grants become permanent, so entitlements that were appropriate when issued drift out of alignment with duties. Periodic recertification is what corrects that drift.",
        "Run access reviews at least annually, and quarterly for production, financial and administrative systems.\nHave the system or data owner certify each user individually rather than approving a list in bulk.\nRevoke access that is not affirmatively certified, and verify the revocation actually executed.\nRetain the review record, the decisions and the evidence of resulting changes.",
    ),
    (
        "GOV-01",
        "Stale policies are a top audit exception; policies must match practice.",
        "Review and re-approve every policy at least annually, tracking review dates and version history.",
        "Policies that no longer describe how the organization actually operates are among the most common audit exceptions. An annual review forces each policy to be read against current practice, re-approved by an accountable owner, and corrected where the two have drifted apart.",
        "Review every policy at least annually, and sooner after a material change to the business or environment.\nRecord the reviewer, the review date and the outcome, even where the outcome is no change.\nRe-approve through the documented approval path rather than editing in place.\nRetain superseded versions so the version history can be traced at audit.",
    ),
    (
        "LM-01",
        "You cannot secure or monitor what you have not inventoried.",
        "Maintain a current inventory of systems and assets, ideally collected automatically from cloud APIs.",
        "Controls apply to systems that are known. An incomplete inventory means some portion of the estate is unpatched, unmonitored and unreviewed, and nobody can say which portion.",
        "Maintain an inventory of systems, cloud resources, endpoints and applications with owner and classification.\nCollect it automatically from cloud and identity APIs where possible, as manual inventories decay quickly.\nReconcile it against billing, DNS and identity records to find unregistered systems.\nReview the inventory periodically and remove decommissioned assets.",
    ),
    (
        "BC-01",
        "Recoverable backups are the foundation of availability and resilience.",
        "Enable automated encrypted backups on every data store with retention aligned to RPO and alert on failures.",
        "Backups are the last defence against ransomware, accidental deletion and regional failure. Automation removes reliance on anyone remembering to run them, and monitoring ensures a silent failure is not discovered during an incident.",
        "Enable automated backups on every production data store, with frequency and retention aligned to the documented RPO.\nEncrypt backups at rest and restrict restore permissions to a small, reviewed group.\nAlert on backup failure and on jobs that have not completed within the expected window.\nKeep at least one copy in a separate region or account, so a single compromise cannot destroy both data and backups.",
    ),
    (
        "HR-01",
        "Background screening reduces the risk of granting access to unsuitable individuals.",
        "Run background checks (where legally permitted) before granting production access, and retain completion records.",
        "Background screening is the control that applies before trust is extended. Once someone holds production access, the opportunity to verify suitability has already passed.",
        "Run background checks, where legally permitted, before granting access to production or customer data.\nDefine the check scope by role, applying deeper screening to privileged and finance-facing positions.\nApply the same standard to contractors who receive equivalent access.\nRetain evidence that the check was completed and cleared, without retaining unnecessary personal detail.",
    ),
    (
        "BC-02",
        "A backup that has never been restored is only a hypothesis.",
        "Test recovery at least annually by restoring a backup and validating data against RTO/RPO.",
        "A backup that has never been restored is an assumption, not a control. Restore testing is what converts it into a demonstrated recovery capability and surfaces the gaps before they matter.",
        "Perform a full restore test at least annually, and after significant changes to the data platform.\nRestore into an isolated environment and validate data completeness and integrity, not just job success.\nMeasure actual restore time against the documented RTO and RPO.\nRecord the test date, scope, result and any corrective actions.",
    ),
    (
        "BC-03",
        "Disruptions must be planned for with defined recovery objectives.",
        "Maintain a BC/DR plan with RTO/RPO targets, key dependencies and workarounds, reviewed annually.",
        "Outages, regional failures and destructive incidents will occur. A plan prepared in advance is what allows recovery within committed timeframes instead of improvising while customers are down.",
        "Maintain a business continuity and disaster recovery plan with defined RTO and RPO per critical service.\nIdentify critical dependencies, including third parties, and document workarounds for each.\nDefine activation criteria, roles and communication procedures for customers and staff.\nReview the plan annually, test it, and update it after significant architectural change.",
    ),
    (
        "GOV-02",
        "Independent oversight of the security program is a core governance expectation.",
        "Put security posture, incidents and risk on the board or oversight-body agenda at least annually and document the meetings.",
        "SOC 2 expects a governing body independent of management to oversee the security programme. Without a documented record of that oversight there is no evidence that leadership exercised the accountability the criteria require.",
        "Put security posture, material incidents, risk assessment results and remediation progress on the board or oversight-body agenda at least annually, and quarterly where practical.\nProvide a written pack rather than a verbal update, so the information given to the body is itself evidence.\nRetain agendas, packs and minutes recording what was discussed and decided.\nRecord any resourcing or risk-acceptance decisions the body makes.",
    ),
    (
        "CS-01",
        "Contractual breach-notification promises must be defined and honoured.",
        "Document breach-notification timeframes to customers and ensure the incident process triggers them.",
        "Breach-notification commitments made in customer contracts are binding and time-bound. If those timeframes are not known to the people running an incident, they will be missed.",
        "Document the breach-notification timeframes committed to customers, including any variation by contract.\nMake the shortest applicable commitment the operating standard for the incident process.\nBuild the customer notification decision into the incident-response plan as an explicit step with an owner.\nMaintain current notification contacts for each customer and verify them periodically.",
    ),
    (
        "DM-01",
        "Regulators and affected parties must be notified as law and contract require.",
        "Build notification criteria, jurisdiction matrices and templates into the incident-response plan.",
        "Breach notification is time-bound by law and by contract, often within 72 hours. Those deadlines cannot be met if the criteria, recipients and templates are decided while an incident is running.",
        "Define the criteria that make an incident notifiable, separately for regulators, customers and data subjects.\nMaintain a jurisdiction matrix covering each applicable regime and its deadline.\nPre-approve notification templates with legal so drafting is not on the critical path.\nBuild the notification decision into the incident-response plan as an explicit step with an owner.",
    ),
    (
        "DM-02",
        "Detected breaches and near-misses must be recorded with PI impact.",
        "Record privacy incidents in the incident register with data affected, subject count and root cause.",
        "The privacy criteria require a record of unauthorized disclosures, not only of incidents that met a notification threshold. Near misses and contained events carry the analysis that prevents the next one.",
        "Record every privacy incident and near miss in the incident register, including those judged not notifiable.\nCapture the data categories affected, the number of subjects, the root cause and the containment action.\nRecord the notification decision and its rationale, including decisions not to notify.\nReview the register periodically for patterns rather than treating entries as closed items.",
    ),
    (
        "BC-04",
        "Availability commitments require capacity to be monitored ahead of demand.",
        "Monitor utilization with thresholds below failure points and use autoscaling where possible.",
        "Availability commitments are broken by capacity limits reached without warning. Monitoring demand against capacity is what turns a future outage into a planned expansion.",
        "Monitor utilization of compute, storage, database connections, quotas and rate limits.\nSet alert thresholds below the point of failure, leaving time to act.\nUse autoscaling where the workload supports it, and test that it engages under load.\nReview capacity trends and provider quotas periodically against forecast growth.",
    ),
    (
        "LM-02",
        "Reliable logs are the raw material for detection and investigation.",
        "Centralize security-relevant logs (audit, auth, application) with retention of at least one year.",
        "Logs are the raw material for detection, investigation and evidence. If they are scattered, short-lived or absent, an incident cannot be reconstructed and the operating history cannot be shown.",
        "Centralize security-relevant logs, including authentication, authorization, administrative action, and application audit events.\nRetain at least twelve months, with recent data immediately searchable.\nProtect logs against modification and restrict who can delete them.\nMonitor for logging gaps, as a source that stops sending is itself a signal.",
    ),
    (
        "SD-01",
        "Changes must be authorized, tested and approved before implementation.",
        "Require documented authorization and approval for production changes, including database and config changes.",
        "Unauthorized change is the most common cause of both outages and security regressions. Requiring changes to be authorized, tested and approved before they reach production is the core of the change-management criterion.",
        "Require every production change to carry a recorded authorization and approval before deployment.\nApply the same requirement to database migrations, configuration and infrastructure changes, not only application code.\nLink the deployment to the approved change record so the two can be reconciled at audit.\nDetect and investigate deployments that reach production without a corresponding approval.",
    ),
    (
        "GOV-03",
        "Significant changes can introduce new risks that must be assessed out of cycle.",
        "Define triggers (new subprocessor, major architecture change, new data type) that force a documented mini risk review.",
        "Risk assessed once a year goes stale as soon as the environment changes. A new subprocessor, a new data type or a major architectural shift can introduce risk that the annual cycle will not surface for months.",
        "Define the triggers that force an out-of-cycle risk review: onboarding a subprocessor that touches customer data, a major architecture or hosting change, a new data type or jurisdiction, or significant organizational change.\nRequire the triggered review before the change goes live, not after.\nDocument each review, its conclusion and any new risks added to the register.\nReview the trigger list annually so it keeps pace with the business.",
    ),
    (
        "SD-02",
        "Automated tests gate defects and validate processing logic before release.",
        "Run automated tests as merge gates and require them to pass before deploy.",
        "Automated tests running as a merge gate catch defects while they are cheap and provide repeatable evidence that processing logic behaves as specified. Tests that can be skipped provide neither.",
        "Run the automated test suite on every pull request and require it to pass before merge.\nEnforce the gate through branch protection so it cannot be bypassed by individual choice.\nInclude tests that validate processing accuracy and completeness where the system processes customer data.\nRetain build results, as they are the operating evidence that the gate ran.",
    ),
    (
        "PE-01",
        "Cloud data-center physical security is inherited and must be reviewed, not assumed.",
        "Obtain and review the cloud provider's SOC 2 report annually and disclose the carve-out in the system description.",
        "Where infrastructure runs in a cloud provider, physical security is performed by that provider and carved out of your audit. Reviewing their report is what makes that reliance a verified control rather than an assumption.",
        "Obtain the provider's current SOC 2 or ISO 27001 report at least annually.\nReview the exceptions and the complementary user entity controls, and confirm you operate the controls the provider expects of you.\nDisclose the subservice organization and the carve-out in the system description.\nRecord the review, the reviewer and any issues identified.",
    ),
    (
        "GOV-04",
        "A documented, acknowledged code of conduct sets the tone for integrity and ethical behaviour across the organization.",
        "Publish a code of conduct covering ethics, acceptable use and confidentiality, and require every employee and contractor to sign it at hire and annually.",
        "The control environment criteria begin with demonstrated commitment to integrity and ethical values. A documented, acknowledged code of conduct is the artifact auditors look for as evidence that expectations were set and accepted rather than assumed.",
        "Publish a code of conduct covering ethical behaviour, acceptable use, conflicts of interest and confidentiality.\nRequire every employee and contractor to acknowledge it at hire and annually thereafter.\nTrack acknowledgement centrally so completion can be evidenced per person.\nRoute non-completion through the disciplinary process rather than leaving it open.",
    ),
    (
        "GOV-05",
        "Knowing your legal, regulatory and contractual commitments is a prerequisite to meeting them.",
        "Maintain a register of applicable obligations and map them to the controls that satisfy each.",
        "Obligations arrive from contracts, regulation and certification commitments, and each changes independently of the others. A single register turns a scattered set of promises into a managed list, so an obligation is not discovered only when it has been breached.",
        "Maintain a register of every applicable legal, regulatory and contractual obligation with its source, owner and review date.\nMap each obligation to the controls that satisfy it, so coverage gaps are visible.\nReview the register at least annually and whenever entering a new market or signing commitments with new requirements.\nAssign a named owner to each obligation rather than to the register as a whole.",
    ),
    (
        "HR-02",
        "Contractual confidentiality obligations protect customer and company information.",
        "Require signed confidentiality and IP agreements from all employees and contractors.",
        "Confidentiality agreements make the obligation to protect customer and company information legally binding and enforceable, rather than a matter of expectation.",
        "Require a signed confidentiality and intellectual property agreement from every employee and contractor before access is granted.\nEnsure obligations survive termination of the engagement.\nTrack signature status centrally so completeness can be evidenced per person.\nRefresh agreements when scope of access or applicable law changes materially.",
    ),
    (
        "LM-03",
        "Config changes can silently introduce vulnerabilities.",
        "Continuously monitor cloud configuration for drift from a secure baseline and alert on regressions.",
        "Cloud configuration changes take effect immediately and can remove a control silently. Detecting drift from the approved baseline is what turns a one-time hardening exercise into a sustained control.",
        "Monitor cloud configuration continuously against a secure baseline.\nAlert on high-risk regressions such as public storage exposure, disabled logging or opened management ports.\nDefine the remediation path for each alert type, and automate reversion where it is safe to do so.\nReview recurring drift for a root cause in the provisioning process.",
    ),
    (
        "DM-03",
        "Where consent is required it must be captured, recorded and revocable, including explicit consent for sensitive data.",
        "Capture granular consent where required, store consent records, and honour opt-outs downstream.",
        "Where processing relies on consent, that consent must be freely given, recorded, and as easy to withdraw as it was to give. Consent that cannot be evidenced is equivalent to no consent at all.",
        "Capture consent granularly per purpose rather than as a single blanket agreement.\nStore a consent record with timestamp, version of the notice shown, and the method of capture.\nObtain explicit consent where sensitive categories of data are involved.\nHonour withdrawal promptly and propagate it to downstream systems and processors.",
    ),
    (
        "GOV-06",
        "Ongoing evaluation proves controls operate throughout the period, not just at a point in time.",
        "Run automated checks continuously against connected systems and review failures with owners.",
        "A Type II opinion covers a period, not a date. Controls must therefore be shown to operate throughout that period, which point-in-time checks cannot demonstrate. Ongoing evaluation is what moves a control from designed to operating effectively.",
        "Run automated checks continuously against connected systems and retain each result with its timestamp, so the operating history is preserved.\nRoute failures to the named control owner with a remediation SLA.\nReview recurring failures for design weakness instead of closing each occurrence individually.\nRecord periods where monitoring itself was unavailable, as that is a gap in the operating evidence.",
    ),
    (
        "HR-03",
        "Contractors carry the same access risk as employees and are a common offboarding gap.",
        "Track contractors with end dates, apply the same onboarding/offboarding, and review their access.",
        "Contractors carry the same access risk as employees but sit outside the HR lifecycle that normally triggers onboarding and offboarding. That gap is where forgotten access accumulates.",
        "Track every contractor in a register with sponsor, scope of access and a mandatory end date.\nApply the same onboarding requirements: agreements, policy acknowledgement, training and approved access.\nTrigger deprovisioning automatically from the end date, and require positive action to extend.\nInclude contractors in access reviews rather than reviewing employees alone.",
    ),
    (
        "GOV-07",
        "Controls must demonstrably mitigate identified risks, with no orphan risks.",
        "Maintain an explicit mapping of risks to mitigating controls and flag any risk with no control or documented acceptance.",
        "Controls exist to mitigate identified risks. Without an explicit mapping it cannot be shown that every material risk is addressed, nor can it be known which risks a failing control leaves exposed.",
        "Maintain a mapping from each risk in the register to the controls that mitigate it.\nFlag any risk with no mitigating control, and any control that maps to no risk.\nRequire a documented acceptance decision, signed by the risk owner, for risks deliberately left unmitigated.\nRevisit the mapping whenever a control is disabled or a new risk is added.",
    ),
    (
        "DM-04",
        "You cannot protect confidential data consistently until it is identified and classified.",
        "Adopt a classification scheme (public/internal/confidential/restricted) with handling rules per level.",
        "Confidential data cannot be protected consistently until it has been identified and labelled. Classification is what lets handling rules, access decisions and retention be applied by rule rather than by individual judgement.",
        "Adopt a classification scheme such as public, internal, confidential and restricted.\nDefine handling rules per level covering storage, transmission, sharing and disposal.\nClassify data stores and repositories, not only individual documents.\nTrain staff on the scheme and reference it in the acceptable use policy.",
    ),
    (
        "DM-05",
        "Subjects can require inaccurate data to be corrected and propagated.",
        "Provide a correction path, propagate changes to processors, and reconcile PI across systems for quality.",
        "Data subjects have the right to have inaccurate personal information corrected, and the privacy criteria also require that personal information is maintained accurately for its purpose. A correction that does not propagate leaves the error in place downstream.",
        "Provide a documented path for subjects to request correction of their personal information.\nVerify identity before acting on a correction request.\nPropagate corrections to downstream systems, processors and backups within a defined window.\nReconcile personal information across systems periodically to detect divergence.",
    ),
    (
        "DM-06",
        "Knowing where confidential and personal data lives is prerequisite to protecting it.",
        "Maintain a data map of stores and vendors holding confidential/personal data and the protections applied.",
        "Data protection begins with knowing what data exists and where it lives. An inventory that is incomplete guarantees that some data is protected by nobody, because nobody knows it is there.",
        "Maintain a data map covering databases, object storage, file shares, analytics platforms and vendor systems.\nRecord for each store the data categories held, classification, owner, location and retention period.\nNote the protections applied to each store, such as encryption, access model and backup treatment.\nRefresh the map at least annually and when new systems or vendors are introduced.",
    ),
    (
        "DM-07",
        "Collecting only what is needed reduces privacy risk and exposure.",
        "Map collection points to stated purposes, avoid unneeded fields, and keep PI out of logs and error trackers.",
        "Data that is never collected cannot be breached, misused or subject to a deletion request. Minimization is the cheapest privacy control available and the one most often skipped.",
        "Map each collection point to the stated purpose it serves, and remove fields that serve none.\nChallenge new fields at design review rather than after they are in production.\nKeep personal information out of logs, error trackers and analytics events.\nReview collected fields periodically and retire those no longer used.",
    ),
    (
        "DM-08",
        "Data should not be kept longer than needed for its purpose.",
        "Define retention periods per data type and enforce them technically (lifecycle rules, TTL jobs).",
        "Data kept beyond its purpose is pure liability: it expands breach impact, deletion obligations and storage cost without serving the business. Retention that is defined but not enforced technically is retention in name only.",
        "Define a retention period for each data type, based on purpose and legal requirement.\nEnforce retention technically through lifecycle rules, TTLs or scheduled purge jobs rather than by manual review.\nApply retention to backups, archives and analytics copies, not only primary stores.\nDocument any legal hold that suspends normal retention, and lift it when the hold ends.",
    ),
    (
        "GOV-08",
        "Identified deficiencies must be routed, tracked and closed, or formally accepted.",
        "Track every finding with an owner, severity-based SLA and closure evidence, escalating aging or critical items.",
        "Identifying a deficiency is only half the control; the criteria require that deficiencies are communicated to those responsible and corrected. Untracked findings recur, and a pattern of repeat findings is itself an audit exception.",
        "Record every finding from audits, tests, monitoring and incidents in one tracker with an owner, severity, root cause and due date.\nDrive due dates from a severity-based SLA rather than negotiating each one.\nRequire closure evidence rather than self-attestation before a finding is closed.\nEscalate items that age past their SLA to management review.",
    ),
    (
        "GOV-09",
        "Every control needs an accountable owner or it will not be operated reliably.",
        "Map each control to a named owner and keep the mapping current as people change roles.",
        "Accountability that is not assigned is not accountability. The criteria require authorities and responsibilities to be defined so individuals know what they own, and so a failing control has a name attached to it.",
        "Map every control to a named owner, and record the authority that owner holds to act.\nReview the mapping at least annually and whenever someone changes role or leaves.\nReassign ownership as part of offboarding so no control is left orphaned.\nKeep ownership at the level of a person, not a team inbox, for controls that require judgement.",
    ),
    (
        "SD-03",
        "Vulnerable dependencies are a primary supply-chain risk.",
        "Enable dependency and container image scanning on all repos and triage alerts to SLA.",
        "Most application code is third-party dependency code, and vulnerabilities in it are disclosed continuously. Without automated scanning the first notice of an exposed dependency is usually an external report.",
        "Enable dependency and container image scanning on every repository and registry.\nFail builds on newly introduced critical vulnerabilities rather than only reporting them.\nTriage alerts to a severity-based SLA and track remediation to closure.\nMaintain a software bill of materials so exposure to a new disclosure can be assessed quickly.",
    ),
    (
        "GOV-10",
        "A named owner is accountable for the security program and its outcomes.",
        "Formally designate a CISO or security lead in policy or by board resolution, with defined authority and escalation paths.",
        "A security programme without a single accountable owner fragments across teams and stalls at decisions nobody is empowered to make. A formally designated officer gives the programme an escalation point and gives the auditor a name.",
        "Formally designate a security officer or equivalent lead in policy or by board resolution.\nDocument the role's authority, budget and escalation path, and its reporting line to the oversight body.\nName a deputy so accountability survives absence and turnover.\nReview the designation whenever the role changes hands.",
    ),
    (
        "GOV-11",
        "Consistent consequences for policy violations hold people accountable and deter misconduct.",
        "Define a disciplinary process in policy, apply it when violations occur, and retain sanction records.",
        "The criteria require that individuals are held accountable for their control responsibilities. A documented and consistently applied disciplinary process is what makes policy enforceable rather than advisory.",
        "Define the disciplinary process in policy, including the range of sanctions and who decides them.\nReference it in the code of conduct that staff acknowledge, so the consequence is known in advance.\nApply it consistently when violations occur, as inconsistent enforcement undermines the control.\nRetain records of the decision and its basis, handled confidentially through HR.",
    ),
    (
        "DM-09",
        "Personal data may only be disclosed as disclosed and consented, with a record kept.",
        "Gate third-party data flows through the vendor process and maintain a disclosure register.",
        "Personal information may only be disclosed to third parties consistently with the notice given and the consent obtained. Without a record of disclosures, neither commitment can be demonstrated, and subject requests for an accounting of disclosures cannot be answered.",
        "Route every new third-party data flow through the vendor review and approval process.\nMaintain a disclosure register recording the recipient, data categories, purpose and legal basis.\nVerify that each disclosure is consistent with the privacy notice and any consent obtained.\nReview the register at least annually against systems actually sending data.",
    ),
    (
        "DM-10",
        "Your privacy commitments must flow down to processors of personal data.",
        "Execute DPAs with every PI-touching vendor and track DPA coverage as a completeness metric.",
        "Privacy commitments do not stop at the organizational boundary. Where a vendor processes personal information on your behalf, a data processing agreement is what makes your obligations binding on them.",
        "Execute a data processing agreement with every vendor that processes personal information.\nEnsure the agreement covers permitted purposes, security obligations, subprocessing, breach notification, deletion and audit rights.\nTrack DPA coverage as a completeness metric against the vendor register.\nRe-paper agreements when the vendor relationship or applicable regime changes.",
    ),
    (
        "DM-11",
        "Subjects have a right to access their data and an accounting of disclosures.",
        "Operate a DSAR process with identity verification, cross-system compilation and an SLA, logging every request.",
        "Data subjects have the right to access their personal information and, in many regimes, an accounting of who it was disclosed to. These requests carry statutory deadlines and are answered from systems that were rarely designed to answer them.",
        "Operate a documented process with a single intake point and a defined SLA aligned to the applicable regime.\nVerify the requester's identity proportionately before disclosing anything.\nCompile the response across all systems holding the subject's data, using the data map as the checklist.\nLog every request, the response given and the date, so timeliness can be evidenced.",
    ),
    (
        "SD-04",
        "Hotfixes still need control, applied retroactively where necessary.",
        "Define an emergency-change path that requires retroactive review and approval.",
        "Emergencies will bypass the normal path, and a process that pretends otherwise simply goes unfollowed. A defined emergency route keeps the control intact by making the bypass explicit, bounded and reviewed.",
        "Define who may authorize an emergency change and under what circumstances.\nRequire the reason and the actions taken to be recorded at the time, even if briefly.\nRequire retrospective review and approval within a defined window, normally the next business day.\nReview emergency changes at management review, as a rising rate signals a problem with the normal path.",
    ),
    (
        "NS-01",
        "Encrypting stored data protects it if underlying media is exposed.",
        "Enable encryption at rest on every data store using cloud-native KMS and verify no store is unencrypted.",
        "Encryption at rest protects data when the storage layer is exposed through a lost device, a misconfigured snapshot, a decommissioned disk or direct access to the underlying store. It is a baseline expectation for confidential and personal data.",
        "Enable encryption at rest on every data store, including databases, object storage, snapshots, backups and disks.\nUse platform-managed keys as the minimum, and customer-managed keys where required by commitment or regulation.\nVerify encryption is actually enabled rather than assumed, and monitor for unencrypted resources being created.\nEnsure new resources inherit encryption by default through policy or infrastructure as code.",
    ),
    (
        "NS-02",
        "Data in motion must be protected from interception.",
        "Enforce TLS 1.2+ on all external endpoints, HTTPS-only (HSTS), and deny non-TLS access to storage.",
        "Data crossing a network can be intercepted or modified in transit. Transport encryption makes intercepted traffic unusable and authenticates the endpoint being connected to.",
        "Enforce TLS 1.2 or higher on all external endpoints, and disable legacy protocols and weak cipher suites.\nRedirect HTTP to HTTPS and enable HSTS so downgrade is not possible.\nRequire TLS for internal service-to-service traffic and for database connections, not only at the edge.\nMonitor certificate expiry and automate renewal so an outage does not create pressure to disable TLS.",
    ),
    (
        "EP-01",
        "Endpoints are a primary malware entry point.",
        "Deploy EDR/anti-malware on all endpoints with enforced auto-update and monitor agent health.",
        "Endpoints are the most common entry point for malware and the device where credentials and data are most exposed. Detection needs to run on the endpoint itself, where the behaviour occurs.",
        "Deploy endpoint detection and response or anti-malware to every managed endpoint and server.\nEnable automatic signature and agent updates.\nMonitor agent health and coverage, and treat a device without a healthy agent as an exception to be resolved.\nRoute detections into the incident process rather than leaving them in a product console.",
    ),
    (
        "EP-02",
        "Encrypted laptops make loss or disposal safe.",
        "Enforce full-disk encryption on all endpoints and report compliance from MDM.",
        "Full-disk encryption is what makes a lost or stolen laptop a hardware loss rather than a data breach, and it is what allows devices to be disposed of without forensic erasure.",
        "Enforce full-disk encryption on all endpoints through MDM policy.\nEscrow recovery keys centrally so encrypted devices remain recoverable.\nReport compliance from MDM and remediate devices found unencrypted.\nVerify encryption before issuing a device and again during periodic compliance checks.",
    ),
    (
        "IAM-03",
        "MFA is the single highest-value control against account compromise.",
        "Require MFA for all users, and phishing-resistant MFA for administrators, with no broad exclusions.",
        "Passwords alone fail against phishing, reuse and credential-stuffing, and stolen credentials remain the most common initial access vector. Multi-factor authentication is the single highest-value access control available.",
        "Require MFA for all users on all systems that support it, with no standing exclusions.\nRequire phishing-resistant factors such as WebAuthn or hardware keys for administrators and for access to production.\nPrioritize systems holding sensitive data and systems controlling network, infrastructure or production if a phased rollout is unavoidable.\nMonitor for accounts that bypass or disable MFA, and treat enrolment gaps as findings.",
    ),
    (
        "IAM-04",
        "Centralizing authentication improves control over access and makes revocation reliable.",
        "Enable SSO across all critical systems that support it and route access through the identity provider.",
        "Centralizing authentication through one identity provider makes access consistently governed: policy is enforced in one place, and revocation on departure actually reaches every application rather than the ones somebody remembered.",
        "Route access to every system that supports SAML or OIDC through the identity provider.\nEnforce MFA, session and password policy centrally at the provider so applications inherit them.\nMaintain a documented list of systems that cannot support SSO, with compensating controls for each.\nVerify that deprovisioning at the provider removes application access, and check the exceptions explicitly.",
    ),
    (
        "LM-04",
        "Events must be evaluated to decide whether they are incidents.",
        "Define severity classification and keep a triage record for security events, including benign ones.",
        "Not every alert is an incident, and the decision between the two is itself a control. Recording that evaluation is what shows events were assessed rather than ignored.",
        "Define severity levels and the criteria that place an event in each.\nTriage every security event and record the assessment, including events determined to be benign.\nDefine escalation paths and response expectations per severity.\nReview triage decisions periodically for consistency and for events that were misclassified.",
    ),
    (
        "CS-02",
        "Customers must be told your security, availability and privacy commitments.",
        "Publish terms of service, SLA, a security/trust page and privacy policy, kept current with actual practice.",
        "Customers are entitled to know the security, availability and privacy commitments being made to them. Those published commitments are also what the audit tests the system against, so they must match reality.",
        "Publish terms of service, service level commitments, a security or trust page and a privacy notice.\nEnsure published commitments match what the controls actually deliver, as an overstated commitment creates an exception.\nReview published material at least annually and after material change to the service.\nRecord approval of changes to committed terms.",
    ),
    (
        "NS-03",
        "Only explicitly required inbound traffic should be allowed.",
        "Configure firewalls/security groups to deny by default and review for 0.0.0.0/0 on sensitive ports.",
        "A default-allow network is an inventory problem disguised as a security problem: nobody can enumerate what is reachable. Default-deny inverts that, so exposure is deliberate and documented.",
        "Configure firewalls and security groups to deny inbound traffic by default and allow only what is explicitly required.\nReview rules for 0.0.0.0/0 on sensitive ports, and justify or remove each occurrence.\nAttach an owner and a purpose to every allow rule so stale rules can be identified.\nReview rule sets periodically and remove rules for decommissioned services.",
    ),
    (
        "GOV-12",
        "SOC 2 explicitly requires fraud, including insider misuse, to be considered.",
        "Add a fraud/insider-threat section to the risk assessment and map it to mitigations such as least privilege and logging.",
        "SOC 2 requires fraud risk, including insider misuse and management override, to be considered explicitly in the risk assessment. Teams routinely assess external threats and omit this, which is a recurring exception.",
        "Include a fraud and insider-threat section in the annual risk assessment, covering incentive, opportunity and rationalization.\nConsider management override of controls specifically, as it is the scenario most often left out.\nMap identified fraud risks to mitigations such as least privilege, segregation of duties, logging and independent review.\nRecord the conclusion even where the assessed risk is low.",
    ),
    (
        "NS-04",
        "Systems configured to a hardened baseline resist common attacks.",
        "Apply CIS or equivalent hardening baselines to infrastructure and check for drift on a schedule.",
        "Default configurations are built for compatibility, not security. A hardening baseline replaces those defaults with a known-good standard and gives drift something measurable to be measured against.",
        "Apply CIS Benchmarks or an equivalent hardening standard to operating systems, containers and cloud services.\nBuild baselines into images and infrastructure as code so new systems start hardened.\nDocument and approve any deviation from the baseline, with the reason.\nCheck for drift on a schedule and remediate regressions.",
    ),
    (
        "LM-05",
        "Lessons must translate into changes so incidents do not recur.",
        "Run postmortems for incidents and track corrective action items to closure.",
        "The value of an incident is the learning, and that is only realized if the analysis is written down and the corrective actions are tracked. Postmortem records are also the audit trail for how an incident was handled.",
        "Run a postmortem for every significant incident, focused on contributing causes rather than individual blame.\nRecord the timeline, impact, root cause and detection gap.\nRaise corrective actions with named owners and due dates, and track them to closure.\nRetain the record, and review recurring themes across incidents.",
    ),
    (
        "LM-06",
        "Recovery from incidents must be defined and executed, not improvised.",
        "Include restore/rebuild/credential-rotation procedures in the IR plan and document recovery in incidents.",
        "Recovery is the part of incident response most often left undefined, and it is where improvisation causes the most damage: partial restores, missed credential rotation and reinfection from an unclean backup.",
        "Define recovery procedures covering restoring from backup, rebuilding compromised systems and rotating affected credentials.\nEstablish criteria for declaring recovery complete and returning to normal operation.\nVerify system integrity before restoring service, so a compromise is not reintroduced.\nRecord the recovery steps performed in each incident record.",
    ),
    (
        "CS-03",
        "People need a known, easy way to report suspected security issues.",
        "Operate a dedicated channel (e.g. a security Slack channel or security@ alias) and communicate it to all staff.",
        "Staff and customers often notice incidents before monitoring does. A known, low-friction reporting channel is what converts that observation into an alert instead of a private concern.",
        "Operate a dedicated reporting channel, such as a security alias or a monitored chat channel.\nCommunicate it at onboarding, in training and in the incident-response plan.\nMonitor it during defined hours and route reports into the triage process.\nEncourage reporting of suspicion rather than certainty, and respond without blame so people keep reporting.",
    ),
    (
        "LM-07",
        "A defined program contains and remediates incidents predictably.",
        "Maintain an IR plan with roles, severities, containment/eradication/recovery and communication steps.",
        "Incidents are handled under time pressure with incomplete information. A plan written in advance is what makes the response consistent rather than dependent on who happens to be available.",
        "Maintain an incident response plan defining roles, severity levels and the phases of detection, containment, eradication, recovery and lessons learned.\nInclude internal and external communication steps, with the notification decision as an explicit gate.\nKeep contact details, escalation paths and vendor support routes current.\nReview the plan annually and after every significant incident.",
    ),
    (
        "NS-05",
        "Cloud workloads need detection for malicious activity and misconfiguration.",
        "Enable a threat-detection service (e.g. GuardDuty) and route findings to the on-call process.",
        "Cloud workloads are attacked through the control plane as well as the host: credential misuse, cryptomining, anomalous API calls and public exposure. Detection has to cover that plane, not just the operating system.",
        "Enable a managed threat-detection service such as GuardDuty, Defender for Cloud or Security Command Center across all accounts and regions.\nRoute findings into the on-call and incident process rather than a dashboard nobody watches.\nTune out known-benign findings deliberately, and record the tuning decisions.\nAlert on detection being disabled or on an account being created without it.",
    ),
    (
        "SD-05",
        "Bad input must be caught at the door to keep processing complete and accurate.",
        "Validate inputs at ingestion (schema, type, range, duplicates) and route rejects to a monitored queue.",
        "Processing integrity depends on what is allowed into the system. Validating at ingestion keeps malformed, duplicate and out-of-range data from propagating into stores and reports where it is far more expensive to correct.",
        "Validate inputs at the boundary against schema, type, range and required fields.\nDetect and handle duplicate submissions explicitly rather than relying on downstream deduplication.\nReject invalid records to a monitored queue rather than discarding them silently.\nAlert on rejection rates that exceed expected thresholds, as they indicate an upstream defect.",
    ),
    (
        "GOV-13",
        "A periodic internal review catches gaps before the external auditor does.",
        "Perform an internal control review or readiness assessment ahead of the audit window and document the results.",
        "An internal assessment before the audit window converts surprises into planned work. It provides the independent evaluation the monitoring criteria expect and gives management time to remediate before an exception reaches the opinion.",
        "Perform an internal control review or readiness assessment at least annually and ahead of the audit window.\nUse a reviewer independent of the controls being reviewed wherever the team is large enough to allow it.\nDocument scope, method, evidence examined and findings, not just a conclusion.\nRoute findings into deficiency tracking so remediation is managed like any other finding.",
    ),
    (
        "GOV-14",
        "Technology-general controls (access, change, operations) underpin every other control.",
        "Ensure the full technology footprint is inventoried and covered by access, change-management and operations controls.",
        "Application controls rest on general technology controls. Where access, change management or operations are weak on any system in the footprint, every control depending on that system inherits the weakness.",
        "Inventory the full technology footprint, including systems introduced through acquisition or adopted informally.\nConfirm each system is covered by access control, change management and operations controls.\nDocument any system deliberately out of scope, with the rationale and any compensating controls.\nReconcile the inventory against billing and identity-provider records to find systems nobody registered.",
    ),
    (
        "HR-04",
        "Competence starts with defining the qualifications and duties a role requires.",
        "Maintain role descriptions that state required qualifications and security responsibilities.",
        "Competence is a control-environment criterion, and it starts with defining what a role requires. Where security duties are not written into the role, they are nobody's job in particular.",
        "Maintain role descriptions stating required qualifications, experience and responsibilities.\nState the security responsibilities attached to each role explicitly.\nUse the description as the basis for the access the role receives.\nReview descriptions when roles change materially, and align them with the control ownership map.",
    ),
    (
        "NS-06",
        "Keys must be protected and rotated for encryption to be meaningful.",
        "Manage keys in a KMS with access controls and rotation, separate from the data they protect.",
        "Encryption reduces to key management. If keys are unprotected, over-shared or never rotated, the encryption they support provides far less assurance than it appears to.",
        "Manage keys in a dedicated KMS or HSM, held separately from the data they protect.\nRestrict key use and administration through policy, and separate those two permissions.\nEnable rotation on a defined schedule, and define a rotation procedure for compromise.\nLog and monitor key use, particularly decrypt operations at unusual volume.",
    ),
    (
        "DM-12",
        "Personal data must only be used for the purposes disclosed.",
        "Restrict PI access to purpose-based roles, govern secondary uses, and document the AI/training stance.",
        "Personal information collected for one purpose being used for another is one of the most common privacy failures, and it now arises most often when data is repurposed for analytics or model training.",
        "Restrict access to personal information to roles whose purpose requires it.\nRequire documented approval before any secondary use, and check it against the purposes disclosed in the notice.\nState the position on using customer or personal data for AI and model training explicitly, and enforce it technically.\nReview actual data flows against stated purposes at least annually.",
    ),
    (
        "GOV-15",
        "Regular leadership review ensures deficiencies are seen and acted on by the people who can resource fixes.",
        "Hold a recurring (quarterly recommended) management review of control health, findings and remediation, with minutes.",
        "Monitoring only closes the loop when results reach people who can allocate resources. A recurring management review is where control health, findings and risk are considered together, and where remediation is prioritized against everything else competing for effort.",
        "Hold a management review at least quarterly, covering control health, open findings, incidents, risk register changes and remediation progress.\nRecord attendees, decisions, resource commitments and actions with named owners.\nCarry unresolved actions forward to the next review rather than closing them silently.\nEscalate items that have missed two consecutive reviews to the oversight body.",
    ),
    (
        "EP-03",
        "Managed devices can enforce encryption, patching and wipe.",
        "Enroll all endpoints in MDM and reconcile enrolled devices against the employee roster.",
        "Device management is what makes endpoint controls verifiable rather than advisory. It enforces encryption, patching and screen lock consistently, and provides the remote lock and wipe capability that limits the impact of a lost device.",
        "Enrol all company endpoints in MDM before issuing them to staff.\nEnforce baseline policy centrally: encryption, screen lock, patch level and permitted software.\nReconcile enrolled devices against the employee roster to find unmanaged devices.\nDefine how personally owned devices are handled, either enrolled or denied access to company data.",
    ),
    (
        "NS-07",
        "Segmentation limits blast radius and keeps data stores off the public network.",
        "Place databases in private subnets, default-deny security groups, and separate trust zones.",
        "Flat networks let one compromised host reach everything. Segmentation limits blast radius and keeps data stores off paths that never needed to reach them.",
        "Place databases and internal services in private subnets with no route from the internet.\nDefine trust zones and control traffic between them with default-deny rules.\nSeparate production from development and corporate networks.\nVerify segmentation by testing reachability rather than by reading the intended design.",
    ),
    (
        "DM-13",
        "Copying production data into dev/staging is a frequent confidentiality exception.",
        "Populate lower environments with masked or synthetic data and verify prod data does not leak.",
        "Copying production data into development or staging silently extends the confidentiality boundary to environments with weaker access control, less monitoring and broader developer access. It is a frequent and avoidable exception.",
        "Populate lower environments with masked, synthetic or subset data rather than production copies.\nProhibit production data in lower environments in policy, and make the approved seeding path the easy one.\nScan lower environments periodically for data that looks like production personal information.\nWhere a production restore is genuinely required, require approval, time-box it and record the justification.",
    ),
    (
        "NS-08",
        "Internet-exposed SSH/RDP is a common, high-severity finding.",
        "Block SSH/RDP from the internet and require access via VPN, zero-trust or a bastion/SSM.",
        "Internet-exposed SSH and RDP are scanned continuously and are a recurring high-severity finding. Management interfaces should never be directly reachable from the public internet.",
        "Block SSH, RDP and database ports from the internet at the security group and firewall level.\nProvide access through a VPN, zero-trust proxy, bastion host or a session manager service instead.\nScan the external surface regularly to detect newly exposed management ports.\nAlert on any change that opens a management port to a public range.",
    ),
    (
        "HR-05",
        "A single ex-employee with live access is a severe finding; offboarding must be reliable and timely.",
        "Trigger deprovisioning on termination across all systems within a defined SLA and verify it completed.",
        "Departures are the highest-risk transition in the access lifecycle. Retained access after departure is both a common audit exception and a common breach vector, and ownership of documents and accounts is easily lost with the person.",
        "Use a documented offboarding checklist covering access revocation, device return, credential rotation and transfer of document and account ownership.\nTrigger it from the HR system on termination so it cannot be forgotten.\nRevoke access within a defined SLA, measured in hours for involuntary departures.\nVerify and record completion per item rather than marking the checklist done as a whole.",
    ),
    (
        "PE-02",
        "In-scope offices and server areas need access restriction.",
        "Where offices are in scope, use badge access, visitor logs and revoke badges on offboarding.",
        "Offices still hold laptops, printed material and network access. Where an office is in scope, physical access control is what stops digital controls from being bypassed by simply walking in.",
        "Control office entry with badge or equivalent access, and restrict server or network areas further.\nMaintain a visitor log and require visitors to be escorted in sensitive areas.\nRevoke badges as part of offboarding, and reconcile active badges against active staff periodically.\nRetain access records for a defined period, and secure printed confidential material and disposal.",
    ),
    (
        "LM-08",
        "Alerts need a responder at all hours.",
        "Operate an on-call rotation that receives and acknowledges security and availability alerts.",
        "Alerts only reduce risk if someone receives them. An unstaffed alerting pipeline produces the appearance of monitoring without the substance, particularly outside working hours.",
        "Operate an on-call rotation with defined coverage, including nights and weekends where commitments require it.\nRoute security and availability alerts to the rotation through a system that escalates unacknowledged pages.\nDefine acknowledgement and response time expectations per severity.\nTrack missed and unacknowledged pages, and review them as a reliability signal.",
    ),
    (
        "HR-06",
        "A consistent onboarding process ensures access, training and acknowledgments happen every time.",
        "Use a per-hire checklist covering access request/approval, policy acknowledgment and training assignment.",
        "Onboarding is the one moment when a new joiner will reliably complete required steps. Agreements, policy acknowledgement, training and correctly scoped access are far harder to collect afterwards.",
        "Use a per-hire checklist covering signed agreements, policy acknowledgement, security training assignment and access request and approval.\nProvision access from the role definition rather than by copying another user.\nComplete security training within a defined period from the start date.\nRecord completion per item so onboarding can be evidenced for any individual.",
    ),
    (
        "IAM-05",
        "Shared and stored secrets must be encrypted and shared safely, not over chat.",
        "Provide a company password manager and require its use for shared credentials.",
        "Some credentials cannot be replaced by single sign-on, and those are exactly the ones that end up in spreadsheets, chat messages and browser profiles. A managed password manager gives them a controlled home with auditable sharing.",
        "Provide a company password manager and require its use for all shared and non-SSO credentials.\nOrganize secrets into vaults scoped by team and role rather than one shared vault.\nProhibit credential sharing over chat or email in the acceptable use policy.\nRevoke vault access at offboarding, and rotate any shared credential the departing person could read.",
    ),
    (
        "IAM-06",
        "Strong authentication requirements reduce credential-based attacks.",
        "Enforce a password policy (length, complexity, breach checks) in the identity provider.",
        "Password policy is the baseline that protects accounts where stronger factors are unavailable. Modern guidance favours length and breach-checking over forced rotation and complexity rules, which drive predictable, weaker passwords.",
        "Enforce the policy centrally at the identity provider rather than per application.\nSet a minimum length of at least 12 characters and screen new passwords against known breach corpora.\nAvoid mandatory periodic rotation unless a credential is known or suspected to be compromised.\nEnforce lockout or rate limiting on repeated failed authentication attempts.",
    ),
    (
        "EP-04",
        "Unpatched systems are exploited faster than they are noticed.",
        "Define OS and software patch SLAs and enforce timely updates via MDM/automation.",
        "Most successful attacks exploit vulnerabilities for which a patch already exists. Timely patching is therefore among the highest-value controls, and it is one of the easiest to let slip.",
        "Define patch SLAs by severity for operating systems, browsers and installed software.\nAutomate deployment through MDM or a patch management tool rather than relying on user action.\nReport compliance against the SLA and follow up devices that fall behind.\nHandle critical out-of-band patches through the emergency change path.",
    ),
    (
        "SD-06",
        "Reviewed changes prevent unauthorized or defective code reaching production.",
        "Enforce branch protection: PR required, at least one approval, no self-merge, passing status checks.",
        "Peer review catches defects and security weaknesses before they reach production and spreads knowledge across the team. Enforced through branch protection, it also produces the authorization trail the change criterion expects.",
        "Require a pull request with at least one approving review from someone other than the author.\nEnforce it through branch protection, and disable direct pushes to protected branches.\nRequire status checks to pass before merge, and prohibit self-approval.\nRecord any use of an administrator override and review those occurrences.",
    ),
    (
        "GOV-16",
        "Independent testing surfaces weaknesses internal monitoring misses.",
        "Commission an external penetration test at least annually and track findings to remediation against SLA.",
        "A penetration test is an adversarial evaluation of controls as they actually run rather than as they are documented. It surfaces exploitable weaknesses that scanning and self-assessment consistently miss.",
        "Commission an independent penetration test at least annually, and after major architectural change.\nScope it to cover internet-facing applications and infrastructure, and state any exclusions in the report.\nTrack findings to remediation against a severity-based SLA.\nObtain retest confirmation for high and critical findings, and retain the report and attestation letter.",
    ),
    (
        "HR-07",
        "Ongoing performance management sustains a competent workforce.",
        "Run a documented performance-review process for staff.",
        "Performance management is how competence is maintained rather than assumed. It is where skills gaps, including security-relevant ones, are identified and where accountability for control responsibilities is reinforced.",
        "Run a documented performance evaluation for every employee at least annually.\nAssess against clear expectations for the role, including its security responsibilities.\nIdentify skills gaps and record the resulting training or development actions.\nRetain the record of the review, handled confidentially through HR.",
    ),
    (
        "SD-07",
        "In-process data must be stored durably and completely.",
        "Use durable, versioned storage for pipeline stages with integrity checks and retention aligned to spec.",
        "Where data passes through a multi-stage pipeline, the intermediate stores are part of the processing path. Data lost or silently truncated between stages produces output that is incomplete without any error being raised.",
        "Use durable, versioned storage for intermediate pipeline stages rather than ephemeral local disk.\nApply integrity checks such as checksums or record counts between stages.\nMake stages idempotent so a retry cannot duplicate or lose records.\nAlign retention of intermediate data with the processing specification and the retention schedule.",
    ),
    (
        "GOV-17",
        "Written, approved policies deploy controls consistently across the organization.",
        "Maintain the standard policy set (InfoSec, access, change, IR, BC/DR, vendor, data, acceptable use, secure development), approved and versioned.",
        "Policies are how control expectations are deployed consistently across the organization. A gap in the policy set marks an area where practice is undefined and therefore cannot be shown to operate consistently.",
        "Maintain the core policy set: information security, access control, change management, incident response, business continuity and disaster recovery, vendor management, data handling, acceptable use and secure development.\nEnsure each policy is formally approved, versioned and dated.\nMap each policy to the criteria it supports so coverage gaps are visible.\nMake the current set available to all staff at a known location.",
    ),
    (
        "DM-14",
        "A tracked process for privacy inquiries and complaints is a Privacy-category requirement.",
        "Publish a privacy contact, route it into a tracked queue with SLAs, and review privacy compliance periodically.",
        "The privacy criteria require a defined channel for inquiries, complaints and disputes, and evidence that they are addressed. An unmonitored privacy inbox fails the control even where no complaint is ever missed.",
        "Publish a privacy contact point in the privacy notice and on the website.\nRoute it into a tracked queue with an owner and a response SLA rather than an individual's mailbox.\nRecord each inquiry, the resolution and the date closed.\nReview privacy complaints periodically for systemic causes.",
    ),
    (
        "DM-15",
        "Data subjects must be told what personal information is collected and why.",
        "Publish and version a privacy notice covering collection, use, sharing, retention and rights, kept truthful to actual flows.",
        "The privacy notice is the commitment against which every other privacy control is judged. Where it describes practices that differ from what the systems actually do, the gap is a finding regardless of how strong the controls are.",
        "Publish a privacy notice covering what is collected, why, the legal basis, who it is shared with, how long it is kept and what rights subjects hold.\nWrite it to match actual data flows, verified against the data map rather than drafted from a template.\nVersion and date the notice, and retain prior versions.\nNotify subjects of material changes through the channel the notice commits to.",
    ),
    (
        "IAM-07",
        "Admin and root access carry the highest risk and need tighter control.",
        "Inventory privileged accounts, require approval for admin grants, and review them at higher frequency.",
        "Administrative and root access can disable controls, read all data and erase its own traces. It therefore warrants tighter provisioning, shorter tenure and closer review than standard access.",
        "Maintain an inventory of privileged accounts across every system, including cloud root and break-glass accounts.\nRequire explicit, separately recorded approval for privileged grants.\nPrefer just-in-time elevation over standing administrative rights, and log every elevation.\nReview privileged access quarterly, and secure break-glass credentials with monitored, alerting access.",
    ),
    (
        "SD-08",
        "Reconciling outputs to inputs proves processing completeness and accuracy.",
        "Monitor job execution and reconcile record counts/totals, alerting and investigating breaks.",
        "Reconciling outputs against inputs is what demonstrates that processing was complete and accurate. A job that reports success while dropping records is invisible without it.",
        "Monitor job execution for success, failure and non-execution, including jobs that silently do not start.\nReconcile record counts and control totals between source and destination for each run.\nAlert on breaks and investigate them rather than reprocessing blindly.\nRetain reconciliation results, as they are the primary evidence for the processing integrity criteria.",
    ),
    (
        "SD-09",
        "Correct processing can only be tested against a defined specification.",
        "Document data definitions, calculation logic and processing SLAs, versioned with the system.",
        "Processing can only be tested for correctness against a stated specification. Where behaviour is defined only by the code, there is no independent standard to test against and no basis for an accuracy commitment.",
        "Document data definitions, field-level semantics, calculation logic and processing SLAs.\nVersion the specification alongside the system so the two do not diverge.\nReference the specification in test cases so tests verify the spec rather than current behaviour.\nReview it when processing logic changes, and record the approval of the change.",
    ),
    (
        "CS-04",
        "Staff can only follow policies they can find and have acknowledged.",
        "Publish policies where all staff can access them and track acknowledgments at hire and on change.",
        "Policies only influence behaviour if staff can find them and know they apply. Acknowledgement is the evidence that expectations were communicated, which the communication criteria require.",
        "Publish the current policy set where all staff can access it without needing to ask.\nTrack acknowledgement at hire and on material change, per person and per policy.\nCommunicate changes actively rather than relying on staff to notice a new version.\nFollow up outstanding acknowledgements, escalating persistent non-completion.",
    ),
    (
        "IAM-08",
        "Access should be granted by role and limited to what the job requires.",
        "Define roles/groups rather than ad-hoc grants and provision access based on least privilege.",
        "Granting access per person produces entitlements nobody can reason about. Defining access by role makes least privilege reviewable, repeatable, and correct by default when someone joins or changes job.",
        "Define roles or groups that map to job functions, and grant access to roles rather than to individuals.\nBase each role on the minimum access the function requires, and document what that is.\nProvision new joiners from the role definition instead of copying an existing user's access.\nReview role definitions periodically, as roles accumulate permissions the same way individuals do.",
    ),
    (
        "EP-05",
        "Devices leaving the company must not carry recoverable data.",
        "Issue and confirm a remote wipe for departing employees and lost devices, retaining the confirmation.",
        "A device that leaves the organization with a departing employee, or is lost, still holds company data and cached credentials. Remote wipe is what closes that exposure when the device cannot be recovered.",
        "Maintain remote wipe capability through MDM on all managed devices.\nIssue a wipe for lost or stolen devices and for departing employees who do not return hardware.\nConfirm the wipe executed rather than assuming the command succeeded, and retain the confirmation.\nCover the case of a device that never reconnects, by rotating credentials it held.",
    ),
    (
        "GOV-18",
        "A documented, recurring risk assessment is the backbone of the program.",
        "Perform a formal risk assessment at least annually and on major change, scoring likelihood and impact against defined objectives.",
        "The risk assessment is the foundation the rest of the programme rests on: it determines which controls are needed and where effort is justified. Controls selected without one are difficult to defend as sufficient.",
        "Perform a formal risk assessment at least annually, and on significant change to the business or environment.\nIdentify threats to defined objectives, including fraud and third-party risk.\nScore likelihood and impact against a documented scale, and record both inherent and residual risk.\nRetain the methodology so results are reproducible and comparable year over year.",
    ),
    (
        "GOV-19",
        "Risks must be tracked with owners, ratings and a treatment decision to be managed.",
        "Maintain a register capturing inherent and residual risk, owner, and treatment (accept/mitigate/transfer/avoid), linked to controls.",
        "A risk that is identified but not tracked is not managed. The register is the operational record showing each risk has an owner, a rating and a decision, and it is what an auditor traces from assessment through to control.",
        "Capture risk description, category, owner, inherent rating, mitigating controls, residual rating and treatment decision of accept, mitigate, transfer or avoid.\nReview the register at each management review and record rating changes with dates.\nRequire named sign-off at an appropriate level for any accepted risk.\nLink each risk to the controls that mitigate it so coverage can be verified.",
    ),
    (
        "GOV-20",
        "Selected mitigations must be planned and tracked to reduce risk to acceptable levels.",
        "For each material risk, record the treatment actions, owner and due dates, and track them to closure.",
        "A treatment decision only reduces risk once it is executed. The treatment plan turns intent into scheduled, owned work, and it is the evidence that residual risk ratings reflect reality rather than aspiration.",
        "For each risk being mitigated, record the specific treatment actions, the accountable owner, the target date and the expected residual rating.\nTrack actions to closure with evidence rather than status updates alone.\nRe-rate the risk only once the treatment is demonstrably in place.\nReport overdue treatment actions at management review.",
    ),
    (
        "EP-06",
        "Unattended, unlocked devices expose data and sessions.",
        "Enforce automatic screen lock with a short idle timeout via MDM.",
        "An unlocked, unattended device grants full access to whoever is nearby, bypassing every authentication control behind it. Automatic locking is what makes physical proximity insufficient.",
        "Enforce automatic screen lock through MDM policy rather than user preference.\nSet a short idle timeout, typically no more than 15 minutes, and require authentication to unlock.\nApply the policy to all device types that access company data.\nReport compliance and remediate devices that fall out of policy.",
    ),
    (
        "SD-10",
        "A documented SDLC sets expectations for how software is built and changed.",
        "Maintain a secure development policy covering review, testing, environments and deployment.",
        "A documented development lifecycle is how security requirements become routine engineering practice rather than individual habit. It also gives new engineers a defined standard to work to, which is what keeps quality stable as a team grows.",
        "Maintain a secure development policy covering design review, code review, testing, environment use and deployment.\nInclude security requirements such as secure coding standards, dependency management and secrets handling.\nDefine how changes are approved and released, and how emergency changes are handled.\nReview the policy annually and align it with the tooling actually in use.",
    ),
    (
        "SD-11",
        "Committed secrets are routinely harvested by attackers.",
        "Enable secret scanning and pre-commit hooks, and rotate any exposed secret immediately.",
        "A secret committed to a repository should be treated as public from that moment: history is cloned, forked and mirrored, and reverting the commit does not invalidate the credential.",
        "Enable secret scanning on all repositories, including full commit history.\nAdd pre-commit hooks so secrets are caught before they are pushed.\nRotate any exposed secret immediately, and treat the exposure as an incident.\nInvestigate whether the exposed credential was used before rotation, rather than assuming it was not.",
    ),
    (
        "NS-09",
        "Secrets in code are a leading breach cause.",
        "Store secrets in a vault or secrets manager, never in source, and rotate on exposure.",
        "Credentials committed to source code, images or configuration are harvested at scale, and they remain valid long after the commit is reverted. Secrets need a managed store with access control and an audit trail.",
        "Store secrets in a dedicated secrets manager or vault, and never in source control, images or environment files in a repository.\nInject secrets at runtime rather than baking them into build artifacts.\nRestrict and log access to each secret, and scope access per service.\nRotate any secret on exposure and on a defined schedule, and treat exposure as an incident.",
    ),
    (
        "DM-16",
        "Data must be irrecoverable once its retention ends or on a valid erasure request.",
        "Delete data across primary stores, indexes, caches, analytics and vendors, and age it out of backups.",
        "Deletion is only meaningful if the data is actually unrecoverable. Data routinely survives in search indexes, caches, analytics warehouses, vendor systems and backups long after it was deleted from the primary store.",
        "Define a disposal procedure covering primary stores, replicas, search indexes, caches, analytics copies and vendor systems.\nUse the data map as the checklist so no store is missed.\nAge deleted data out of backups within the documented backup retention window, and state that window in the response to the subject.\nRetain a record of what was disposed of, when, and by which method.",
    ),
    (
        "LM-09",
        "Detection is only useful if anomalies raise alerts someone sees.",
        "Alert on security-relevant signals (root use, IAM changes, threat findings) and route to a monitored channel.",
        "Alerting on everything trains responders to ignore alerts. A small set of high-signal alerts that are consistently acted on detects more than an exhaustive set that is muted.",
        "Alert on a deliberately limited set of high-signal conditions rather than on every anomaly.\nPrioritize unauthorized access attempts, unusual authentication patterns, privilege escalation, service unavailability and resource exhaustion.\nRoute each alert to an owner with a defined response, and remove alerts nobody acts on.\nReview alert volume and false-positive rate periodically, and tune deliberately.",
    ),
    (
        "GOV-21",
        "Clear reporting lines and authorities ensure everyone knows who owns security responsibilities.",
        "Maintain a current org chart and role descriptions that include security duties, reviewed at least annually.",
        "The criteria require that reporting lines and authorities are established. An accurate structure shows that security duties sit with real roles holding the standing to carry them out, rather than being distributed informally.",
        "Maintain a current organizational chart showing reporting lines.\nMaintain role descriptions that state the security responsibilities attached to each role.\nReview both at least annually and after any reorganization.\nConfirm security roles retain a reporting line independent enough to raise issues without conflict of interest.",
    ),
    (
        "HR-08",
        "Trained staff are the first line of defence; training gaps are a frequent exception.",
        "Deliver security-awareness training at onboarding and at least annually, tracking 100% completion.",
        "Staff are the most frequently targeted attack surface, primarily through phishing and social engineering. Training is the control that turns the workforce from the weakest link into a detection layer.",
        "Deliver security awareness training at onboarding and at least annually thereafter.\nCover phishing, social engineering, credential handling, data classification and incident reporting.\nTrack completion to 100 percent and escalate non-completion rather than letting it lapse.\nSupplement with periodic phishing simulation, using results to target training rather than to penalize.",
    ),
    (
        "IAM-09",
        "Separating conflicting duties reduces fraud and error risk.",
        "Separate sensitive duties where feasible (e.g. deployer is not sole approver) or document compensating controls.",
        "Where one person can initiate, approve and execute the same sensitive action, both fraud and simple error go undetected. Separating those duties introduces a second pair of eyes at the point where it matters.",
        "Identify conflicting duty pairs, such as deploying to production and approving that deployment, or creating a vendor and approving its payment.\nSeparate them in system permissions rather than by convention.\nWhere team size makes separation impractical, document a compensating control such as independent after-the-fact review of a logged action.\nRe-examine separation whenever the team grows or restructures.",
    ),
    (
        "SD-12",
        "Environment separation prevents untested change and data mixing.",
        "Maintain distinct dev, staging and production environments with controlled promotion.",
        "Testing in production exposes customer data to unreleased code and makes it impossible to distinguish deliberate change from experiment. Separate environments give changes somewhere to be validated before they carry real consequences.",
        "Maintain distinct development, staging and production environments with separate credentials and accounts.\nPromote changes through environments in a controlled sequence rather than deploying directly to production.\nRestrict production access to those who require it, and grant lower-environment access more freely.\nKeep production data out of lower environments, using masked or synthetic data instead.",
    ),
    (
        "IAM-10",
        "Non-human identities are often over-privileged and unreviewed.",
        "Inventory service accounts and API keys, scope them least-privilege, and rotate/review them.",
        "Service accounts, API keys and tokens authenticate without a human present. They are rarely reviewed, frequently over-permissioned, and often outlive the integration that created them.",
        "Inventory every service account, API key and integration token with its owner, purpose and permissions.\nScope each to least privilege, and never use a provider's default or highly privileged service account.\nRotate credentials on a defined schedule and immediately on suspected exposure.\nReview the inventory at least annually and disable accounts with no recent authentication activity.",
    ),
    (
        "IAM-11",
        "Idle and long-lived sessions widen the window for hijacking.",
        "Configure session timeouts and re-authentication for sensitive systems.",
        "Sessions that never expire turn a single stolen laptop or hijacked token into indefinite access. Session limits bound how long a compromised session remains useful.",
        "Configure idle and absolute session timeouts centrally at the identity provider.\nSet shorter timeouts for administrative interfaces and systems holding sensitive data.\nRequire re-authentication for high-risk actions such as changing MFA settings or granting access.\nEnsure logout and deprovisioning invalidate active sessions and refresh tokens, not only future logins.",
    ),
    (
        "BC-05",
        "New SaaS adopted informally creates unmanaged vendor and data risk.",
        "Detect new SSO apps and OAuth grants and feed them into the vendor onboarding workflow.",
        "Software adopted outside procurement still processes company data, but without a vendor review, a data processing agreement or an offboarding path. Detection is what brings it back under management.",
        "Monitor identity-provider sign-ins and OAuth grants to detect newly adopted applications.\nReview expense and card data for software purchases made outside procurement.\nRoute detected applications into the vendor onboarding process, or remove access.\nMake the approved request path easy enough that informal adoption is not the path of least resistance.",
    ),
    (
        "BC-06",
        "Subprocessors receiving customer/personal data must be tracked and (often) published.",
        "Maintain a subprocessor list and reconcile it against vendors actually receiving data.",
        "Subprocessors receiving customer or personal data extend the trust boundary. Customer contracts and privacy regimes commonly require that they are disclosed and, in many cases, that customers are notified before new ones are added.",
        "Maintain a subprocessor list recording the entity, purpose, data categories and location.\nPublish it where customer commitments require, and keep the published version current.\nReconcile the list against vendors that actually receive data, using the data map.\nFollow the contractual notice process before adding a subprocessor.",
    ),
    (
        "GOV-22",
        "Objectives must be defined clearly enough that risks to them can be identified.",
        "Document the system, the commitments made to customers, and the requirements that follow, and anchor the risk assessment to them.",
        "Risks can only be identified against objectives that have been stated. The system description defines the boundary, the commitments made to customers and the requirements that follow, and it anchors both the risk assessment and the audit scope.",
        "Document the system boundary, covering infrastructure, software, people, procedures and data.\nState the service commitments and system requirements made to customers, as those are what the audit tests against.\nDescribe subservice organizations and state clearly which controls are carved out.\nReview annually and on material change, and reconcile the description against what is actually deployed.",
    ),
    (
        "LM-10",
        "In a no-incident year, a tabletop is the operating evidence the program works.",
        "Run at least an annual tabletop exercise with participants and captured findings.",
        "In a period with no incidents, a tabletop exercise is the only operating evidence that the response plan works. It also surfaces the gaps that are otherwise found during a real incident.",
        "Run at least one tabletop exercise annually against a realistic scenario.\nInclude the people who would actually respond, including engineering, leadership and communications.\nCapture what the exercise revealed, particularly gaps in contacts, access and decision authority.\nTrack resulting actions to closure and retain the record as evidence the plan was exercised.",
    ),
    (
        "IAM-12",
        "Access must be removed promptly when no longer authorized.",
        "Remove access on role change or termination within a defined SLA and reconcile active accounts to active staff.",
        "The window between someone losing authorization and losing access is a window of unmonitored risk. Departures are also when access is most likely to be used inappropriately.",
        "Trigger deprovisioning automatically from the HR or identity system on termination or role change.\nDefine an SLA measured in hours for revoking access on involuntary termination.\nCover systems outside SSO, shared credentials, VPN, code repositories and physical access.\nReconcile active accounts against active staff periodically, and investigate every account without a current owner.",
    ),
    (
        "DM-17",
        "Vendors must commit to notifying you of incidents so you can meet your obligations.",
        "Ensure DPAs contain breach-notification clauses with timeframes and record them per vendor.",
        "Your own breach-notification deadlines start when you become aware of an incident. If a vendor is not contractually obliged to tell you promptly, their delay consumes your statutory window.",
        "Require a breach-notification clause with a specific timeframe, expressed in hours, in every data processing agreement.\nSpecify what the notification must contain, so the first message is actionable rather than a holding statement.\nRecord the notification terms per vendor in the vendor register.\nTest the contact path for critical vendors, and confirm the notification route is current at review.",
    ),
    (
        "BC-07",
        "You must know who your vendors are and what data they touch.",
        "Maintain a vendor register with owner, criticality and data-access classification, kept complete.",
        "Third-party risk cannot be managed against an unknown population. The vendor register is the base list that due diligence, agreements and access reviews all work from.",
        "Maintain a vendor register with owner, service provided, criticality and the data each vendor can access.\nReconcile it against accounts payable and identity-provider records to find unregistered vendors.\nRecord contract dates and renewal points so review happens before commitments auto-renew.\nReview the register at least annually and remove vendors no longer in use, confirming their access is revoked.",
    ),
    (
        "BC-08",
        "Vendor risk must be assessed on onboarding and periodically.",
        "Review vendor security (SOC 2 report, questionnaire) scaled to risk and re-review critical vendors annually.",
        "Vendors inherit the data entrusted to you, and their weaknesses become yours. Diligence scaled to risk is what makes that inheritance a decision rather than an accident.",
        "Assess vendor security before granting access to systems or data, with depth scaled to criticality.\nObtain and review a SOC 2 report or equivalent for critical vendors, reading the exceptions and complementary user entity controls rather than filing the report unread.\nRe-review critical vendors at least annually and on material change.\nRecord the assessment, the decision and any accepted risk.",
    ),
    (
        "LM-11",
        "New vulnerabilities must be found and remediated on a defined cadence.",
        "Scan infrastructure and dependencies regularly and remediate by severity-based SLA, tracking to closure.",
        "New vulnerabilities are disclosed continuously against systems that were secure when deployed. A defined cadence of discovery and remediation is what keeps a hardened estate from drifting into exposure.",
        "Scan infrastructure, containers, dependencies and external surface on a defined schedule.\nDefine remediation SLAs by severity, and measure performance against them.\nTrack findings to closure with evidence, and require a documented risk acceptance for anything not remediated.\nFeed penetration test and bug report findings into the same tracker so all vulnerabilities are managed in one place.",
    ),
    (
        "NS-10",
        "Public endpoints need protection against web attacks and volumetric floods.",
        "Front public services with a WAF and DDoS protection (e.g. Cloudflare, AWS WAF/Shield).",
        "Public services face automated attack traffic continuously. A web application firewall filters common injection and scripting attacks, and upstream DDoS protection absorbs volumetric traffic that would otherwise exhaust capacity.",
        "Front public services with a WAF and DDoS protection such as Cloudflare or AWS WAF and Shield.\nStart rules in detection mode, tune out false positives, then enforce.\nEnsure the origin cannot be reached directly, bypassing the WAF.\nMonitor blocked traffic for genuine attack patterns and feed them into detection.",
    ),
    (
        "CS-05",
        "A confidential reporting path supports the integrity and accountability criteria.",
        "Provide an anonymous reporting mechanism and document how reports are handled.",
        "A confidential reporting path allows misconduct to be raised where the normal management line is part of the concern. Its existence supports the integrity and accountability criteria directly.",
        "Provide a confidential and, where practical, anonymous reporting mechanism.\nDocument how reports are received, investigated and escalated, and who is excluded from handling a report about themselves.\nCommunicate the mechanism to all staff and state the prohibition on retaliation.\nRecord reports and their handling confidentially, and report volume to the oversight body.",
    ),
    (
        "NS-11",
        "Internal admin access should not rely on network location alone.",
        "Require a VPN or zero-trust mesh with MFA for administrative access to infrastructure.",
        "Trusting a device because it sits on the corporate network fails the moment that network includes home offices, contractors and personal devices. Access decisions should rest on verified identity and device posture, not location.",
        "Require a VPN or zero-trust access solution with MFA for administrative access to infrastructure.\nBase access decisions on user identity and device posture rather than source network alone.\nGrant access per application rather than issuing broad network access.\nLog access sessions and review them alongside privileged access.",
    ),
)

_UNEDITED = sa.text(
    "CREATE TEMPORARY TABLE _unedited_controls ON COMMIT DROP AS "
    "SELECT c.id FROM controls c JOIN control_templates t ON c.template_id = t.id "
    "WHERE c.description IS NOT DISTINCT FROM t.description "
    "AND c.implementation_guidance IS NOT DISTINCT FROM t.implementation_guidance"
)

_TEMPLATE = sa.text(
    "UPDATE control_templates SET description = :description, "
    "implementation_guidance = :guidance WHERE code = :code"
)

_PROPAGATE = sa.text(
    "UPDATE controls c SET description = t.description, "
    "implementation_guidance = t.implementation_guidance "
    "FROM control_templates t "
    "WHERE c.template_id = t.id AND c.id IN (SELECT id FROM _unedited_controls)"
)


def _apply(index_description: int, index_guidance: int) -> None:
    bind = op.get_bind()
    # FORCE applies to the owner this migration runs as, and it filters SELECT as
    # well as UPDATE. It has to come off *before* the read that captures which
    # rows are unedited: under FORCE that read silently returns zero rows, and
    # the backfill below would then match nothing at all.
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    try:
        # Capture "unedited" against the text the templates hold right now.
        bind.execute(_UNEDITED)
        for row in CONTENT:
            bind.execute(
                _TEMPLATE,
                {
                    "code": row[0],
                    "description": row[index_description],
                    "guidance": row[index_guidance],
                },
            )
        bind.execute(_PROPAGATE)
    finally:
        op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _apply(3, 4)


def downgrade() -> None:
    _apply(1, 2)
