"""Library text for shared controls: neutral wording and the compliance review's corrections.

A control in the one library serves SOC 2 and ISO 27001 at once (ADR-0014). The 2026-10-16
compliance review pass (ISO 27001, PCI DSS and banking audit perspective) changed 60 shipped
controls:

* Controls that framed themselves by one framework ("The criteria require...", "SOC 2
  expects...", "A Type II opinion covers a period") now give the real reason the control
  matters; framework specific reasons live in each mapping's rationale.
* Guidance an auditor could not test (no owner, frequency, record or trigger) was made
  specific, and on-premises, banking and card data cases were added as conditional sentences
  that leave the cloud case unchanged.

Both planes move together, as in the 2026-08-24 guidance rewrite (``a4c81f37b902``):

* ``control_templates`` is global shipped content and is updated unconditionally, so it matches
  the pack ``seed-content`` loads after this migration (which then reports no change for these
  fields).
* ``controls`` holds each workspace's adopted copy. Only copies still identical to their template
  (name, statement and guidance) are refreshed: a workspace that edited its copy keeps its edit
  (CF-6). ``controls`` has FORCE ROW LEVEL SECURITY, which applies to the owner this runs as and
  filters SELECT too, so FORCE is lifted before the read that captures the unedited rows and
  restored in the same transaction.

The set of unedited rows is captured before the templates move, because "unedited" means equal
to the template's previous text. ``downgrade`` restores the previous text on the same basis.

Revision ID: e3a91c5d7b20
Revises: c5d8a2f7e91b
Create Date: 2026-10-16
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision: str = "e3a91c5d7b20"
down_revision: str | None = "c5d8a2f7e91b"
branch_labels: str | None = None
depends_on: str | None = None

# Each row: the code, then the old name, description and guidance, then the new three.
CONTENT: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    (
        "BC-01",
        "Automated, monitored backups",
        "Backups are the last defence against ransomware, accidental deletion and regional failure. Automation removes reliance on anyone remembering to run them, and monitoring ensures a silent failure is not discovered during an incident.",
        "Enable automated backups on every production data store, with frequency and retention aligned to the documented RPO.\nEncrypt backups at rest and restrict restore permissions to a small, reviewed group.\nAlert on backup failure and on jobs that have not completed within the expected window.\nKeep at least one copy in a separate region or account, so a single compromise cannot destroy both data and backups.",
        "Automated, monitored backups",
        "Backups are the last defence against ransomware, accidental deletion and regional failure. Automation removes reliance on anyone remembering to run them, and monitoring ensures a silent failure is not discovered during an incident.",
        "Enable automated backups on every production data store, and keep the configuration, infrastructure code and system images needed to rebuild each service, with frequency and retention aligned to the documented RPO.\nEncrypt backups at rest and restrict restore permissions to a small, reviewed group.\nAlert on backup failure and on jobs that have not completed within the expected window.\nKeep at least one copy in a separate region, account or site, protected by immutable storage or held offline, so a single compromise cannot destroy both data and backups.",
    ),
    (
        "BC-02",
        "Backup restore testing",
        "A backup that has never been restored is an assumption, not a control. Restore testing is what converts it into a demonstrated recovery capability and surfaces the gaps before they matter.",
        "Perform a full restore test at least annually, and after significant changes to the data platform.\nRestore into an isolated environment and validate data completeness and integrity, not just job success.\nMeasure actual restore time against the documented RTO and RPO.\nRecord the test date, scope, result and any corrective actions.",
        "Backup restore testing",
        "A backup that has never been restored is an assumption, not a control. Restore testing is what converts it into a demonstrated recovery capability and surfaces the gaps before they matter.",
        "Perform a full restore test at least annually and after significant changes to the data platform, and where backups are held on tape or on premises, or a regulator expects it, also restore a sample of systems or files at least quarterly.\nRestore into an isolated environment and validate data completeness and integrity, not just job success.\nMeasure actual restore time against the documented RTO and RPO.\nRecord the test date, scope, result and any corrective actions.",
    ),
    (
        "BC-03",
        "Business continuity / disaster recovery plan",
        "Outages, regional failures and destructive incidents will occur. A plan prepared in advance is what allows recovery within committed timeframes instead of improvising while customers are down.",
        "Maintain a business continuity and disaster recovery plan with defined RTO and RPO per critical service.\nIdentify critical dependencies, including third parties, and document workarounds for each.\nDefine activation criteria, roles and communication procedures for customers and staff.\nReview the plan annually, test it, and update it after significant architectural change.",
        "Business continuity / disaster recovery plan",
        "Outages, regional failures and destructive incidents will occur. A plan prepared in advance is what allows recovery within committed timeframes instead of improvising while customers are down.",
        "Maintain a business continuity and disaster recovery plan with defined RTO and RPO per critical service, and record the redundancy each service relies on to meet them, such as multiple availability zones, a secondary site or standby equipment.\nIdentify critical dependencies, including third parties, and document a workaround for each that keeps the security controls it relies on, such as access control, logging and encryption, in place, or names who may approve a temporary relaxation, what compensates for it and when it must be reversed.\nDefine activation criteria, roles and communication procedures for customers and staff.\nReview and test the plan at least annually, including failover of the redundant components and, where a secondary site or region exists, a switch to it with access control, logging and segmentation confirmed working there, and update it after significant architectural change.",
    ),
    (
        "BC-04",
        "Capacity management",
        "Availability commitments are broken by capacity limits reached without warning. Monitoring demand against capacity is what turns a future outage into a planned expansion.",
        "Monitor utilization of compute, storage, database connections, quotas and rate limits.\nSet alert thresholds below the point of failure, leaving time to act.\nUse autoscaling where the workload supports it, and test that it engages under load.\nReview capacity trends and provider quotas periodically against forecast growth.",
        "Capacity management",
        "Availability commitments are broken by capacity limits reached without warning. Monitoring demand against capacity is what turns a future outage into a planned expansion.",
        "Monitor utilization of compute, storage, network bandwidth, database connections, quotas, rate limits and licenses, and in your own data centers, power, cooling and rack space.\nSet alert thresholds below the point of failure, leaving time to act.\nUse autoscaling where the workload supports it and test that it engages under load, and for fixed hardware order capacity early enough to cover supplier lead times.\nReview capacity trends and provider quotas at least quarterly against forecast growth.",
    ),
    (
        "BC-07",
        "Vendor inventory",
        "Third-party risk cannot be managed against an unknown population. The vendor register is the base list that due diligence, agreements and access reviews all work from.",
        "Maintain a vendor register with owner, service provided, criticality and the data each vendor can access.\nReconcile it against accounts payable and identity-provider records to find unregistered vendors.\nRecord contract dates and renewal points so review happens before commitments auto-renew.\nReview the register at least annually and remove vendors no longer in use, confirming their access is revoked.",
        "Vendor inventory",
        "Third-party risk cannot be managed against an unknown population. The vendor register is the base list that due diligence, agreements and access reviews all work from.",
        "Maintain a vendor register with owner, service provided, criticality, the data each vendor can access and, where a regulator defines it, whether the arrangement is material outsourcing that needs notice to or approval from that regulator.\nReconcile it against accounts payable and identity-provider records to find unregistered vendors.\nRecord contract dates and renewal points so review happens before commitments auto-renew.\nReview the register at least annually and remove vendors no longer in use, confirming their access is revoked.",
    ),
    (
        "BC-08",
        "Vendor security due diligence",
        "Vendors inherit the data entrusted to you, and their weaknesses become yours. Diligence scaled to risk is what makes that inheritance a decision rather than an accident.",
        "Assess vendor security before granting access to systems or data, with depth scaled to criticality.\nObtain and review a SOC 2 report or equivalent for critical vendors, reading the exceptions and complementary user entity controls rather than filing the report unread.\nRe-review critical vendors at least annually and on material change.\nRecord the assessment, the decision and any accepted risk.",
        "Vendor security due diligence",
        "Vendors inherit the data entrusted to you, and their weaknesses become yours. Diligence scaled to risk is what makes that inheritance a decision rather than an accident.",
        "Assess vendor security before granting access to systems or data, with depth set by the vendor's criticality, and agree the terms its contract must carry, such as incident notice, audit rights, the security and service levels expected, limits on subcontracting and return or deletion of data at exit.\nObtain current independent assurance for critical vendors, such as a SOC 2 Type II report, an ISO/IEC 27001 certificate with its Statement of Applicability, or a PCI DSS Attestation of Compliance where card data is involved, and read its scope, any exceptions or exclusions, the controls the vendor expects you to operate and the subservice providers it relies on, rather than filing it unread.\nRe-review critical vendors at least annually and on material change, such as a breach, a change of ownership or a new subservice provider, including whether they met the security and service levels agreed in the contract.\nRecord the assessment, the agreed contract terms, the decision and any accepted risk. For suppliers that build software for you, also set security requirements and code ownership in the contract and test what they deliver before it goes live, and where a critical system depends on a supplier's code, such as core banking software, arrange source code escrow and verify the deposit is complete and current at each review.",
    ),
    (
        "CS-02",
        "External security commitments",
        "Customers are entitled to know the security, availability and privacy commitments being made to them. Those published commitments are also what the audit tests the system against, so they must match reality.",
        "Publish terms of service, service level commitments, a security or trust page and a privacy notice.\nEnsure published commitments match what the controls actually deliver, as an overstated commitment creates an exception.\nReview published material at least annually and after material change to the service.\nRecord approval of changes to committed terms.",
        "External security commitments",
        "Customers are entitled to know the security, availability and privacy commitments being made to them. Those published commitments are also obligations the controls must meet and auditors will test against, so they must match reality.",
        "Publish terms of service, service level commitments, a security or trust page and a privacy notice.\nEnsure published commitments match what the controls actually deliver, as an overstated commitment creates an exception.\nReview published material at least annually and after material change to the service.\nRecord approval of changes to committed terms.",
    ),
    (
        "CS-04",
        "Internal policy portal",
        "Policies only influence behaviour if staff can find them and know they apply. Acknowledgement is the evidence that expectations were communicated, which the communication criteria require.",
        "Publish the current policy set where all staff can access it without needing to ask.\nTrack acknowledgement at hire and on material change, per person and per policy.\nCommunicate changes actively rather than relying on staff to notice a new version.\nFollow up outstanding acknowledgements, escalating persistent non-completion.",
        "Internal policy portal",
        "Policies only influence behavior if staff can find them and know they apply. Acknowledgement is the evidence that expectations were communicated, and without it a policy breach can be met with the claim that nobody was told.",
        "Publish the current policy set where all staff can access it without needing to ask.\nTrack acknowledgement at hire and on material change, per person and per policy.\nCommunicate changes actively rather than relying on staff to notice a new version.\nFollow up outstanding acknowledgements, escalating persistent non-completion.",
    ),
    (
        "CS-05",
        "Whistleblower / ethics reporting mechanism",
        "A confidential reporting path allows misconduct to be raised where the normal management line is part of the concern. Its existence supports the integrity and accountability criteria directly.",
        "Provide a confidential and, where practical, anonymous reporting mechanism.\nDocument how reports are received, investigated and escalated, and who is excluded from handling a report about themselves.\nCommunicate the mechanism to all staff and state the prohibition on retaliation.\nRecord reports and their handling confidentially, and report volume to the oversight body.",
        "Whistleblower / ethics reporting mechanism",
        "A confidential reporting path allows misconduct to be raised where the normal management line is part of the concern. Without it, such concerns go unreported, and the organization's commitment to integrity and accountability cannot be shown to work in practice.",
        "Provide a confidential and, where practical, anonymous reporting mechanism.\nDocument how reports are received, investigated and escalated, and who is excluded from handling a report about themselves.\nCommunicate the mechanism to all staff and state the prohibition on retaliation.\nRecord reports and their handling confidentially, and report volume to the oversight body.",
    ),
    (
        "DM-02",
        "Unauthorized-disclosure recordkeeping",
        "The privacy criteria require a record of unauthorized disclosures, not only of incidents that met a notification threshold. Near misses and contained events carry the analysis that prevents the next one.",
        "Record every privacy incident and near miss in the incident register, including those judged not notifiable.\nCapture the data categories affected, the number of subjects, the root cause and the containment action.\nRecord the notification decision and its rationale, including decisions not to notify.\nReview the register periodically for patterns rather than treating entries as closed items.",
        "Unauthorized-disclosure recordkeeping",
        "Every unauthorized disclosure of personal information must be recorded, not only incidents that met a notification threshold, and data protection laws such as the GDPR require a record of every personal data breach whether or not it was notified. Near misses and contained events carry the analysis that prevents the next one.",
        "Record every privacy incident and near miss in the incident register, including those judged not notifiable.\nCapture the data categories affected, the number of subjects, the root cause and the containment action.\nRecord the notification decision and its rationale, including decisions not to notify.\nReview the register periodically for patterns rather than treating entries as closed items.",
    ),
    (
        "DM-04",
        "Data classification policy",
        "Confidential data cannot be protected consistently until it has been identified and labelled. Classification is what lets handling rules, access decisions and retention be applied by rule rather than by individual judgement.",
        "Adopt a classification scheme such as public, internal, confidential and restricted.\nDefine handling rules per level covering storage, transmission, sharing and disposal.\nClassify data stores and repositories, not only individual documents.\nTrain staff on the scheme and reference it in the acceptable use policy.",
        "Data classification policy",
        "Confidential data cannot be protected consistently until it has been identified and labelled. Classification is what lets handling rules, access decisions and retention be applied by rule rather than by individual judgement.",
        "Adopt a classification scheme such as public, internal, confidential and restricted, and give each set of data its level based on its confidentiality, integrity and availability needs and on legal, contractual and customer requirements.\nDefine handling rules per level covering storage, transmission, sharing and disposal, and for removable media holding restricted data, such as card or core banking data, keep a media log, check it against the media held at least annually, and move media off site only by tracked courier with management approval.\nHave each data owner classify their data stores and repositories, not only individual documents, and mark information with its level by a defined method for documents, email, files, media and system records, such as a header, a metadata tag or a sensitivity label, stating when marking may be left out.\nTrain staff on the scheme and on how to mark information, and reference it in the acceptable use policy.",
    ),
    (
        "DM-05",
        "Personal-information correction",
        "Data subjects have the right to have inaccurate personal information corrected, and the privacy criteria also require that personal information is maintained accurately for its purpose. A correction that does not propagate leaves the error in place downstream.",
        "Provide a documented path for subjects to request correction of their personal information.\nVerify identity before acting on a correction request.\nPropagate corrections to downstream systems, processors and backups within a defined window.\nReconcile personal information across systems periodically to detect divergence.",
        "Personal-information correction",
        "Data subjects have the right to have inaccurate personal information corrected, and personal information must also be kept accurate for the purpose it is used for. A correction that does not propagate leaves the error in place downstream.",
        "Provide a documented path for subjects to request correction of their personal information.\nVerify identity before acting on a correction request.\nPropagate corrections to downstream systems, processors and backups within a defined window.\nReconcile personal information across systems periodically to detect divergence.",
    ),
    (
        "DM-08",
        "Data retention schedule",
        "Data kept beyond its purpose is pure liability: it expands breach impact, deletion obligations and storage cost without serving the business. Retention that is defined but not enforced technically is retention in name only.",
        "Define a retention period for each data type, based on purpose and legal requirement.\nEnforce retention technically through lifecycle rules, TTLs or scheduled purge jobs rather than by manual review.\nApply retention to backups, archives and analytics copies, not only primary stores.\nDocument any legal hold that suspends normal retention, and lift it when the hold ends.",
        "Data retention schedule",
        "Data kept beyond its purpose is pure liability: it expands breach impact, deletion obligations and storage cost without serving the business. Retention that is defined but not enforced technically is retention in name only.",
        "Define a retention period for each data type, based on purpose and legal requirement.\nEnforce retention technically through lifecycle rules, TTLs or scheduled purge jobs rather than by manual review, and keep records that law or regulation requires to stay unaltered, such as transaction and audit records, on write once or locked storage for the whole period.\nApply retention to backups, archives and analytics copies, not only primary stores.\nDocument any legal hold that suspends normal retention, and lift it when the hold ends.",
    ),
    (
        "DM-14",
        "Privacy inquiry and complaint handling",
        "The privacy criteria require a defined channel for inquiries, complaints and disputes, and evidence that they are addressed. An unmonitored privacy inbox fails the control even where no complaint is ever missed.",
        "Publish a privacy contact point in the privacy notice and on the website.\nRoute it into a tracked queue with an owner and a response SLA rather than an individual's mailbox.\nRecord each inquiry, the resolution and the date closed.\nReview privacy complaints periodically for systemic causes.",
        "Privacy inquiry and complaint handling",
        "Individuals must have a defined channel for privacy inquiries, complaints and disputes, and the organization must be able to show that each one was addressed. An unmonitored privacy inbox fails the control even where no complaint is ever missed.",
        "Publish a privacy contact point in the privacy notice and on the website.\nRoute it into a tracked queue with an owner and a response SLA rather than an individual's mailbox.\nRecord each inquiry, the resolution and the date closed.\nReview privacy complaints periodically for systemic causes.",
    ),
    (
        "DM-16",
        "Secure data disposal",
        "Deletion is only meaningful if the data is actually unrecoverable. Data routinely survives in search indexes, caches, analytics warehouses, vendor systems and backups long after it was deleted from the primary store.",
        "Define a disposal procedure covering primary stores, replicas, search indexes, caches, analytics copies and vendor systems.\nUse the data map as the checklist so no store is missed.\nAge deleted data out of backups within the documented backup retention window, and state that window in the response to the subject.\nRetain a record of what was disposed of, when, and by which method.",
        "Secure data disposal",
        "Deletion is only meaningful if the data is actually unrecoverable. Data routinely survives in search indexes, caches, analytics warehouses, vendor systems and backups long after it was deleted from the primary store.",
        "Define a disposal procedure covering primary stores, replicas, search indexes, caches, analytics copies and vendor systems, and also laptops, servers, drives, tapes and removable media that are retired, sold, returned from lease or reissued.\nUse the data map and the asset inventory as checklists so no store or device is missed.\nAge deleted data out of backups within the documented backup retention window, and state that window in the response to the subject.\nWipe or destroy each device and medium by a method that fits the data it held, so neither company data nor licensed software can be recovered, confirm the result before reuse or disposal, and retain a record of what was disposed of, when and by which method, including certificates from any disposal contractor.",
    ),
    (
        "EP-01",
        "Endpoint EDR / anti-malware",
        "Endpoints are the most common entry point for malware and the device where credentials and data are most exposed. Detection needs to run on the endpoint itself, where the behaviour occurs.",
        "Deploy endpoint detection and response or anti-malware to every managed endpoint and server.\nEnable automatic signature and agent updates.\nMonitor agent health and coverage, and treat a device without a healthy agent as an exception to be resolved.\nRoute detections into the incident process rather than leaving them in a product console.",
        "Endpoint EDR / anti-malware",
        "Endpoints are the most common entry point for malware and the device where credentials and data are most exposed. Detection needs to run on the endpoint itself, where the behaviour occurs.",
        "Deploy endpoint detection and response or anti-malware to every managed endpoint and server.\nEnable automatic signature and agent updates, and where removable media is allowed, scan it automatically when it is connected.\nMonitor agent health and coverage, treat a device without a healthy agent as an exception to be resolved, and for any system judged not to need anti-malware, such as a mainframe or appliance, record the reason and re-check it at least annually.\nRoute detections into the incident process rather than leaving them in a product console.",
    ),
    (
        "GOV-02",
        "Board / executive security oversight",
        "SOC 2 expects a governing body independent of management to oversee the security programme. Without a documented record of that oversight there is no evidence that leadership exercised the accountability the criteria require.",
        "Put security posture, material incidents, risk assessment results and remediation progress on the board or oversight-body agenda at least annually, and quarterly where practical.\nProvide a written pack rather than a verbal update, so the information given to the body is itself evidence.\nRetain agendas, packs and minutes recording what was discussed and decided.\nRecord any resourcing or risk-acceptance decisions the body makes.",
        "Board / executive security oversight",
        "A governing body independent of management is what holds the security program to account, rather than leaving management to judge its own work. Without a documented record of that oversight there is no evidence that leadership exercised the accountability it carries.",
        "Put security posture, material incidents, risk assessment results and remediation progress on the board or oversight-body agenda at least annually, and quarterly where practical.\nProvide a written pack rather than a verbal update, so the information given to the body is itself evidence.\nRetain agendas, packs and minutes recording what was discussed and decided.\nRecord any resourcing or risk-acceptance decisions the body makes.",
    ),
    (
        "GOV-03",
        "Change-triggered risk review",
        "Risk assessed once a year goes stale as soon as the environment changes. A new subprocessor, a new data type or a major architectural shift can introduce risk that the annual cycle will not surface for months.",
        "Define the triggers that force an out-of-cycle risk review: onboarding a subprocessor that touches customer data, a major architecture or hosting change, a new data type or jurisdiction, or significant organizational change.\nRequire the triggered review before the change goes live, not after.\nDocument each review, its conclusion and any new risks added to the register.\nReview the trigger list annually so it keeps pace with the business.",
        "Change-triggered risk review",
        "Risk assessed once a year goes stale as soon as the environment changes. A new subprocessor, a new data type or a major architectural shift can introduce risk that the annual cycle will not surface for months.",
        "Define the triggers that force an out-of-cycle risk review: onboarding a subprocessor that touches customer data, a major architecture or hosting change, a new data type or jurisdiction, the start of any project that changes systems, data, sites or suppliers, or significant organizational change.\nHold a project's review at its planning stage, and in every case complete the triggered review before the change goes live, not after.\nDocument each review, its conclusion and any new risks added to the register.\nReview the trigger list annually so it keeps pace with the business.",
    ),
    (
        "GOV-04",
        "Code of conduct and ethics policy",
        "The control environment criteria begin with demonstrated commitment to integrity and ethical values. A documented, acknowledged code of conduct is the artifact auditors look for as evidence that expectations were set and accepted rather than assumed.",
        "Publish a code of conduct covering ethical behaviour, acceptable use, conflicts of interest and confidentiality.\nRequire every employee and contractor to acknowledge it at hire and annually thereafter.\nTrack acknowledgement centrally so completion can be evidenced per person.\nRoute non-completion through the disciplinary process rather than leaving it open.",
        "Code of conduct and ethics policy",
        "Every other control depends on leadership and staff showing a real commitment to honest and ethical conduct. A documented, acknowledged code of conduct is the artifact auditors look for as evidence that expectations were set and accepted rather than assumed.",
        "Publish a code of conduct covering ethical behaviour, acceptable use, conflicts of interest and confidentiality.\nRequire every employee and contractor to acknowledge it at hire and annually thereafter.\nTrack acknowledgement centrally so completion can be evidenced per person.\nRoute non-completion through the disciplinary process rather than leaving it open.",
    ),
    (
        "GOV-06",
        "Continuous control monitoring",
        "A Type II opinion covers a period, not a date. Controls must therefore be shown to operate throughout that period, which point-in-time checks cannot demonstrate. Ongoing evaluation is what moves a control from designed to operating effectively.",
        "Run automated checks continuously against connected systems and retain each result with its timestamp, so the operating history is preserved.\nRoute failures to the named control owner with a remediation SLA.\nReview recurring failures for design weakness instead of closing each occurrence individually.\nRecord periods where monitoring itself was unavailable, as that is a gap in the operating evidence.",
        "Continuous control monitoring",
        "Controls are relied on for a period, not a date. They must therefore be shown to operate throughout that period, which point-in-time checks cannot demonstrate. Ongoing evaluation is what moves a control from designed to operating effectively.",
        "Run automated checks continuously against connected systems, and on a set schedule with the organization's own tools for systems that cannot be connected, and retain each result with its timestamp, so the operating history is preserved.\nRoute failures to the named control owner with a remediation SLA.\nReview recurring failures for design weakness instead of closing each occurrence individually.\nRecord periods where monitoring itself was unavailable, as that is a gap in the operating evidence.",
    ),
    (
        "GOV-08",
        "Deficiency remediation tracking",
        "Identifying a deficiency is only half the control; the criteria require that deficiencies are communicated to those responsible and corrected. Untracked findings recur, and a pattern of repeat findings is itself an audit exception.",
        "Record every finding from audits, tests, monitoring and incidents in one tracker with an owner, severity, root cause and due date.\nDrive due dates from a severity-based SLA rather than negotiating each one.\nRequire closure evidence rather than self-attestation before a finding is closed.\nEscalate items that age past their SLA to management review.",
        "Deficiency remediation tracking",
        "Identifying a deficiency is only half the control; the other half is communicating it to those responsible and getting it corrected. Untracked findings recur, and a pattern of repeat findings is itself an audit exception.",
        "Record every finding from audits, tests, monitoring, incidents and complaints in one tracker with an owner, severity, the immediate fix or containment and how its consequences were handled, root cause and due date.\nDrive due dates from a severity-based SLA rather than negotiating each one, and check whether the same cause could exist in other systems, teams or controls.\nRequire closure evidence rather than self-attestation before a finding is closed, and confirm the action worked, for significant findings by checking after a set period that the problem has not returned.\nEscalate items that age past their SLA to management review, and update policies, procedures or controls when the cause shows the program itself needs to change.",
    ),
    (
        "GOV-09",
        "Assigned control ownership (RACI)",
        "Accountability that is not assigned is not accountability. The criteria require authorities and responsibilities to be defined so individuals know what they own, and so a failing control has a name attached to it.",
        "Map every control to a named owner, and record the authority that owner holds to act.\nReview the mapping at least annually and whenever someone changes role or leaves.\nReassign ownership as part of offboarding so no control is left orphaned.\nKeep ownership at the level of a person, not a team inbox, for controls that require judgement.",
        "Assigned control ownership (RACI)",
        "Accountability that is not assigned is not accountability. Authorities and responsibilities must be defined so individuals know what they own, and so a failing control has a name attached to it.",
        "Map every control to a named owner, and record the authority that owner holds to act.\nReview the mapping at least annually and whenever someone changes role or leaves.\nReassign ownership as part of offboarding so no control is left orphaned.\nKeep ownership at the level of a person, not a team inbox, for controls that require judgement.",
    ),
    (
        "GOV-10",
        "Designated security officer",
        "A security programme without a single accountable owner fragments across teams and stalls at decisions nobody is empowered to make. A formally designated officer gives the programme an escalation point and gives the auditor a name.",
        "Formally designate a security officer or equivalent lead in policy or by board resolution.\nDocument the role's authority, budget and escalation path, and its reporting line to the oversight body.\nName a deputy so accountability survives absence and turnover.\nReview the designation whenever the role changes hands.",
        "Designated security officer",
        "A security programme without a single accountable owner fragments across teams and stalls at decisions nobody is empowered to make. A formally designated officer gives the programme an escalation point and gives the auditor a name.",
        "Formally designate a security officer or equivalent lead in policy or by board resolution.\nDocument the role's authority, budget and escalation path, and its reporting line to the oversight body, and where a regulator requires it, keep the role independent of IT operations, for example reporting to the chief executive or the chief risk officer.\nName a deputy so accountability survives absence and turnover.\nReview the designation whenever the role changes hands.",
    ),
    (
        "GOV-11",
        "Documented disciplinary process",
        "The criteria require that individuals are held accountable for their control responsibilities. A documented and consistently applied disciplinary process is what makes policy enforceable rather than advisory.",
        "Define the disciplinary process in policy, including the range of sanctions and who decides them.\nReference it in the code of conduct that staff acknowledge, so the consequence is known in advance.\nApply it consistently when violations occur, as inconsistent enforcement undermines the control.\nRetain records of the decision and its basis, handled confidentially through HR.",
        "Documented disciplinary process",
        "People must know there are consequences when they disregard their security responsibilities, or those responsibilities carry no weight. A documented and consistently applied disciplinary process is what makes policy enforceable rather than advisory.",
        "Define the disciplinary process in policy, including the range of sanctions and who decides them.\nReference it in the code of conduct that staff acknowledge, so the consequence is known in advance.\nApply it consistently when violations occur, as inconsistent enforcement undermines the control.\nRetain records of the decision and its basis, handled confidentially through HR.",
    ),
    (
        "GOV-12",
        "Fraud and insider-threat consideration",
        "SOC 2 requires fraud risk, including insider misuse and management override, to be considered explicitly in the risk assessment. Teams routinely assess external threats and omit this, which is a recurring exception.",
        "Include a fraud and insider-threat section in the annual risk assessment, covering incentive, opportunity and rationalization.\nConsider management override of controls specifically, as it is the scenario most often left out.\nMap identified fraud risks to mitigations such as least privilege, segregation of duties, logging and independent review.\nRecord the conclusion even where the assessed risk is low.",
        "Fraud and insider-threat consideration",
        "Fraud risk, including insider misuse and management override, must be considered explicitly in the risk assessment, because the people with legitimate access are the ones best placed to abuse it. Teams routinely assess external threats and omit this, which is a recurring exception.",
        "Include a fraud and insider-threat section in the annual risk assessment, covering incentive, opportunity and rationalization.\nConsider management override of controls specifically, as it is the scenario most often left out.\nMap identified fraud risks to mitigations such as least privilege, segregation of duties, logging and independent review.\nRecord the conclusion even where the assessed risk is low.",
    ),
    (
        "GOV-13",
        "Internal audit / readiness assessment",
        "An internal assessment before the audit window converts surprises into planned work. It provides the independent evaluation the monitoring criteria expect and gives management time to remediate before an exception reaches the opinion.",
        "Perform an internal control review or readiness assessment at least annually and ahead of the audit window.\nUse a reviewer independent of the controls being reviewed wherever the team is large enough to allow it.\nDocument scope, method, evidence examined and findings, not just a conclusion.\nRoute findings into deficiency tracking so remediation is managed like any other finding.",
        "Internal audit",
        "An internal audit, run on a set program by people who do not audit their own work, tests whether the security program and its controls operate as documented. It finds gaps while there is time to fix them and feeds its findings into corrective action and management review.",
        "Keep an internal audit program that sets how often each part of the security program is audited, based on its importance and the results of earlier audits, the methods used, and who plans, performs and reports each audit, so the whole program, management processes as well as controls, is audited at least once a year and ahead of each external audit, with a targeted review after significant change to the business, systems or program.\nFor each audit, record the scope, the criteria, such as internal policies, contracts and the standards the organization works to, the method, the evidence examined and the findings, not just a conclusion.\nChoose auditors who do not audit their own work, and use another team or an outside reviewer where the security team is too small to keep that separation, rather than having owners assess their own controls.\nReport results to the managers responsible, to management review and, where one exists, to the audit committee, and route findings into deficiency tracking so remediation is managed like any other finding.",
    ),
    (
        "GOV-15",
        "Periodic management review of security",
        "Monitoring only closes the loop when results reach people who can allocate resources. A recurring management review is where control health, findings and risk are considered together, and where remediation is prioritized against everything else competing for effort.",
        "Hold a management review at least quarterly, covering control health, open findings, incidents, risk register changes and remediation progress.\nRecord attendees, decisions, resource commitments and actions with named owners.\nCarry unresolved actions forward to the next review rather than closing them silently.\nEscalate items that have missed two consecutive reviews to the oversight body.",
        "Periodic management review of security",
        "Monitoring only closes the loop when results reach people who can allocate resources. A recurring management review is where control health, findings and risk are considered together, and where remediation is prioritized against everything else competing for effort.",
        "Hold a management review at least quarterly, attended by the security lead and by senior managers who can commit resources, covering control health, open findings, incidents, risk register changes and remediation progress.\nAt least once a year, have the executive team review whether the security program still fits the business, covers what it needs to and works, using actions from earlier reviews, changes in internal and external factors and in what interested parties require, nonconformities and corrective actions, measurement and audit results, objectives achieved, feedback from customers and others, risk assessment results and treatment status, and ideas for improvement.\nRecord attendees, the inputs considered, decisions on improvements and on any changes the program needs, resource commitments and actions with named owners, and carry unresolved actions forward rather than closing them silently.\nEscalate items that have missed two consecutive reviews to the oversight body.",
    ),
    (
        "GOV-16",
        "Annual penetration test",
        "A penetration test is an adversarial evaluation of controls as they actually run rather than as they are documented. It surfaces exploitable weaknesses that scanning and self-assessment consistently miss.",
        "Commission an independent penetration test at least annually, and after major architectural change.\nScope it to cover internet-facing applications and infrastructure, and state any exclusions in the report.\nTrack findings to remediation against a severity-based SLA.\nObtain retest confirmation for high and critical findings, and retain the report and attestation letter.",
        "Annual penetration test",
        "A penetration test is an adversarial evaluation of controls as they actually run rather than as they are documented. It surfaces exploitable weaknesses that scanning and self-assessment consistently miss.",
        "Commission an independent penetration test at least annually and after major architectural change, and before it starts agree the scope, timing, test accounts and any tests that could disrupt service with the system owner in writing.\nScope it to cover internet-facing applications and infrastructure and, where systems run on premises or handle card data, the internal network and the controls that separate the card data environment, using a tester independent of the team that runs those systems, and state any exclusions in the report.\nTrack findings to remediation against a severity-based SLA.\nObtain retest confirmation for high and critical findings, and retain the report and attestation letter.",
    ),
    (
        "GOV-17",
        "Security policy suite",
        "Policies are how control expectations are deployed consistently across the organization. A gap in the policy set marks an area where practice is undefined and therefore cannot be shown to operate consistently.",
        "Maintain the core policy set: information security, access control, change management, incident response, business continuity and disaster recovery, vendor management, data handling, acceptable use and secure development.\nEnsure each policy is formally approved, versioned and dated.\nMap each policy to the criteria it supports so coverage gaps are visible.\nMake the current set available to all staff at a known location.",
        "Security policy suite",
        "Policies are how control expectations are deployed consistently across the organization. A gap in the policy set marks an area where practice is undefined and therefore cannot be shown to operate consistently.",
        "Maintain the core policy set: information security, access control, change management, incident response, business continuity and disaster recovery, vendor management, cloud service use, data handling, acceptable use with clear desk and clear screen rules, remote working including the care of equipment and media taken off site, and secure development.\nEnsure each policy is formally approved, versioned and dated, with the top level information security policy approved by top management, or by the board where a regulator requires it, and each topic policy by its accountable manager. The top level policy states the security objectives or how they are set, and commits to meeting applicable legal, regulatory and contractual requirements and to improving the program.\nMap each policy to the framework requirements it supports so coverage gaps are visible.\nMake the current set available to all staff at a known location, and share the top level policy with customers, regulators or other parties where they need it.",
    ),
    (
        "GOV-18",
        "Annual risk assessment",
        "The risk assessment is the foundation the rest of the programme rests on: it determines which controls are needed and where effort is justified. Controls selected without one are difficult to defend as sufficient.",
        "Perform a formal risk assessment at least annually, and on significant change to the business or environment.\nIdentify threats to defined objectives, including fraud and third-party risk.\nScore likelihood and impact against a documented scale, and record both inherent and residual risk.\nRetain the methodology so results are reproducible and comparable year over year.",
        "Annual risk assessment",
        "The risk assessment is the foundation the rest of the programme rests on: it determines which controls are needed and where effort is justified. Controls selected without one are difficult to defend as sufficient.",
        "Perform a formal risk assessment at least annually, and on significant change to the business or environment, taking account of internal and external factors and the requirements of customers, regulators and other parties.\nIdentify risks to the confidentiality, integrity and availability of information in scope, to the commitments made to customers and to the security program meeting its objectives, including fraud and third-party risk, and name an owner for each.\nScore likelihood and impact against a documented scale, record inherent and residual risk, compare each result with acceptance criteria approved by leadership that state what level of risk may be accepted and by whom, and rank risks for treatment.\nRetain the methodology and results so assessments are reproducible and comparable year over year, and where a standard or contract leaves the frequency of a control to you, keep a short risk analysis that justifies the frequency chosen and review it yearly.",
    ),
    (
        "GOV-20",
        "Risk treatment plan",
        "A treatment decision only reduces risk once it is executed. The treatment plan turns intent into scheduled, owned work, and it is the evidence that residual risk ratings reflect reality rather than aspiration.",
        "For each risk being mitigated, record the specific treatment actions, the accountable owner, the target date and the expected residual rating.\nTrack actions to closure with evidence rather than status updates alone.\nRe-rate the risk only once the treatment is demonstrably in place.\nReport overdue treatment actions at management review.",
        "Risk treatment plan",
        "A treatment decision only reduces risk once it is executed. The treatment plan turns intent into scheduled, owned work, and it is the evidence that residual risk ratings reflect reality rather than aspiration.",
        "For each risk being mitigated, record the specific treatment actions, the accountable owner, the target date and the expected residual rating, and have the risk owner approve the plan.\nTrack actions to closure with evidence rather than status updates alone.\nRe-rate the risk only once the treatment is demonstrably in place, and have the risk owner accept the remaining risk in writing, or send it back for further treatment where it is above the acceptance criteria. When someone other than the risk owner requests the acceptance, name the risk owner as its approver.\nReport overdue treatment actions at management review.",
    ),
    (
        "GOV-21",
        "Organizational structure and reporting lines",
        "The criteria require that reporting lines and authorities are established. An accurate structure shows that security duties sit with real roles holding the standing to carry them out, rather than being distributed informally.",
        "Maintain a current organizational chart showing reporting lines.\nMaintain role descriptions that state the security responsibilities attached to each role.\nReview both at least annually and after any reorganization.\nConfirm security roles retain a reporting line independent enough to raise issues without conflict of interest.",
        "Organizational structure and reporting lines",
        "Security duties are only as effective as the reporting lines and authorities behind them, so both must be established. An accurate structure shows that security duties sit with real roles holding the standing to carry them out, rather than being distributed informally.",
        "Maintain a current organizational chart showing reporting lines.\nMaintain role descriptions that state the security responsibilities attached to each role.\nReview both at least annually and after any reorganization.\nConfirm security roles retain a reporting line independent enough to raise issues without conflict of interest.",
    ),
    (
        "GOV-22",
        "System description and service commitments",
        "Risks can only be identified against objectives that have been stated. The system description defines the boundary, the commitments made to customers and the requirements that follow, and it anchors both the risk assessment and the audit scope.",
        "Document the system boundary, covering infrastructure, software, people, procedures and data.\nState the service commitments and system requirements made to customers, as those are what the audit tests against.\nDescribe subservice organizations and state clearly which controls are carved out.\nReview annually and on material change, and reconcile the description against what is actually deployed.",
        "System description and service commitments",
        "Risks can only be identified against objectives that have been stated. The system description defines the boundary, the commitments made to customers and the requirements that follow, and it anchors both the risk assessment and the audit scope.",
        "Document the system boundary, covering infrastructure, software, people, procedures and data.\nState the commitments made to customers and the legal, regulatory, contractual and internal requirements the system must meet, as those are what the controls are designed and audited against.\nDescribe the third parties the system depends on, and state clearly which controls they operate and which remain yours.\nReview annually and on material change, and reconcile the description against what is actually deployed.",
    ),
    (
        "HR-01",
        "Pre-hire background checks",
        "Background screening is the control that applies before trust is extended. Once someone holds production access, the opportunity to verify suitability has already passed.",
        "Run background checks, where legally permitted, before granting access to production or customer data.\nDefine the check scope by role, applying deeper screening to privileged and finance-facing positions.\nApply the same standard to contractors who receive equivalent access.\nRetain evidence that the check was completed and cleared, without retaining unnecessary personal detail.",
        "Pre-hire background checks",
        "Background screening is the control that applies before trust is extended. Once someone holds production access, the opportunity to verify suitability has already passed.",
        "Run background checks, where legally permitted, before granting access to production or customer data, and again before someone moves into a more sensitive role.\nDefine the check scope by role, applying deeper screening to privileged and finance-facing positions, and repeat or refresh checks for those roles at an interval you set from risk and law, recorded in the screening policy.\nApply the same standard to contractors who receive equivalent access, through the contract with their employer where you cannot screen them yourself.\nRetain evidence that the check was completed and cleared, without retaining unnecessary personal detail.",
    ),
    (
        "HR-02",
        "Confidentiality / IP agreements",
        "Confidentiality agreements make the obligation to protect customer and company information legally binding and enforceable, rather than a matter of expectation.",
        "Require a signed confidentiality and intellectual property agreement from every employee and contractor before access is granted.\nEnsure obligations survive termination of the engagement.\nTrack signature status centrally so completeness can be evidenced per person.\nRefresh agreements when scope of access or applicable law changes materially.",
        "Confidentiality / IP agreements",
        "Confidentiality agreements make the obligation to protect customer and company information legally binding and enforceable, rather than a matter of expectation.",
        "Require a signed confidentiality and intellectual property agreement from every employee and contractor, and a non-disclosure agreement from any other outside party, such as a partner or prospective supplier, before they receive confidential information or access.\nInclude a security clause in each employment contract and contractor agreement that states the person's security duties and the organization's duties to them, refers to the policies they must follow and states the consequence of a breach.\nEnsure obligations survive termination of the engagement, and track signature status centrally so completeness can be evidenced per person and per party.\nReview the templates at least annually against what needs protecting, and refresh agreements when scope of access or applicable law changes materially.",
    ),
    (
        "HR-03",
        "Contractor lifecycle management",
        "Contractors carry the same access risk as employees but sit outside the HR lifecycle that normally triggers onboarding and offboarding. That gap is where forgotten access accumulates.",
        "Track every contractor in a register with sponsor, scope of access and a mandatory end date.\nApply the same onboarding requirements: agreements, policy acknowledgement, training and approved access.\nTrigger deprovisioning automatically from the end date, and require positive action to extend.\nInclude contractors in access reviews rather than reviewing employees alone.",
        "Contractor lifecycle management",
        "Contractors carry the same access risk as employees but sit outside the HR lifecycle that normally triggers onboarding and offboarding. That gap is where forgotten access accumulates.",
        "Track every contractor in a register with sponsor, scope of access and a mandatory end date.\nApply the same onboarding requirements: agreements, policy acknowledgement, training and approved access.\nTrigger deprovisioning and the return of company devices, badges and data automatically from the end date, record each item returned, and require positive action to extend.\nInclude contractors in access reviews rather than reviewing employees alone.",
    ),
    (
        "HR-04",
        "Job descriptions with security responsibilities",
        "Competence is a control-environment criterion, and it starts with defining what a role requires. Where security duties are not written into the role, they are nobody's job in particular.",
        "Maintain role descriptions stating required qualifications, experience and responsibilities.\nState the security responsibilities attached to each role explicitly.\nUse the description as the basis for the access the role receives.\nReview descriptions when roles change materially, and align them with the control ownership map.",
        "Job descriptions with security responsibilities",
        "Competence can only be judged against what a role requires, so that has to be defined first. Where security duties are not written into the role, they are nobody's job in particular.",
        "Maintain role descriptions stating required qualifications, experience and responsibilities.\nState the security responsibilities attached to each role explicitly.\nUse the description as the basis for the access the role receives.\nReview descriptions when roles change materially, and align them with the control ownership map.",
    ),
    (
        "HR-05",
        "Offboarding and deprovisioning",
        "Departures are the highest-risk transition in the access lifecycle. Retained access after departure is both a common audit exception and a common breach vector, and ownership of documents and accounts is easily lost with the person.",
        "Use a documented offboarding checklist covering access revocation, device return, credential rotation and transfer of document and account ownership.\nTrigger it from the HR system on termination so it cannot be forgotten.\nRevoke access within a defined SLA, measured in hours for involuntary departures.\nVerify and record completion per item rather than marking the checklist done as a whole.",
        "Offboarding and deprovisioning",
        "Departures are the highest-risk transition in the access lifecycle. Retained access after departure is both a common audit exception and a common breach vector, and ownership of documents and accounts is easily lost with the person.",
        "Use a documented offboarding checklist covering access revocation, return of devices, badges, physical keys and hardware tokens, credential rotation, transfer of document and account ownership, reassignment of any custodian duty such as key components or safe combinations with any combination the person knew changed, and a written reminder of the duties that continue after exit, such as confidentiality, acknowledged by the leaver.\nTrigger it from the HR system on termination, and run the relevant access, asset and duty items when someone changes role, so rights, assets and duties from the old role do not carry over.\nRevoke access within a defined SLA, measured in hours for involuntary departures.\nVerify and record completion per item rather than marking the checklist done as a whole.",
    ),
    (
        "HR-08",
        "Security awareness training",
        "Staff are the most frequently targeted attack surface, primarily through phishing and social engineering. Training is the control that turns the workforce from the weakest link into a detection layer.",
        "Deliver security awareness training at onboarding and at least annually thereafter.\nCover phishing, social engineering, credential handling, data classification and incident reporting.\nTrack completion to 100 percent and escalate non-completion rather than letting it lapse.\nSupplement with periodic phishing simulation, using results to target training rather than to penalize.",
        "Security awareness training",
        "Staff are the most frequently targeted attack surface, primarily through phishing and social engineering. Training is the control that turns the workforce from the weakest link into a detection layer.",
        "Deliver security awareness training at onboarding and at least annually thereafter, to employees and to contractors with access to company systems or data.\nCover phishing, social engineering, credential handling, data classification and incident reporting, and add role-based modules where a role needs more, such as secure coding for engineers and privileged access handling for administrators.\nTrack completion to 100 percent and escalate non-completion rather than letting it lapse.\nSupplement with periodic phishing simulation, using results to target training rather than to penalize.",
    ),
    (
        "IAM-01",
        "Access provisioning approval",
        "Access granted without a recorded authorization cannot be shown to be appropriate, and it is the point at which least privilege is either enforced or quietly abandoned. The approval record is what an auditor samples to test the control.",
        "Require a documented request and approval before any account or entitlement is created.\nRoute approval to the system or data owner rather than to the requester's manager alone for privileged access.\nCapture the business justification, so the grant can be re-evaluated at the next access review.\nProvision only after approval is recorded, and reject retrospective approvals as a matter of process.",
        "Access provisioning approval",
        "Access granted without a recorded authorization cannot be shown to be appropriate, and it is the point at which least privilege is either enforced or quietly abandoned. The approval record is what an auditor samples to test the control.",
        "Require a documented request and approval before any account or entitlement is created, give each person an account of their own, and allow shared or generic accounts only by approved exception with a named owner.\nRoute approval to the system or data owner rather than to the requester's manager alone for privileged access.\nCapture the business justification, so the grant can be re-evaluated at the next access review.\nProvision only after approval is recorded, and reject retrospective approvals as a matter of process.",
    ),
    (
        "IAM-06",
        "Password policy",
        "Password policy is the baseline that protects accounts where stronger factors are unavailable. Modern guidance favours length and breach-checking over forced rotation and complexity rules, which drive predictable, weaker passwords.",
        "Enforce the policy centrally at the identity provider rather than per application.\nSet a minimum length of at least 12 characters and screen new passwords against known breach corpora.\nAvoid mandatory periodic rotation unless a credential is known or suspected to be compromised.\nEnforce lockout or rate limiting on repeated failed authentication attempts.",
        "Password policy",
        "Password policy is the baseline that protects accounts where stronger factors are unavailable. Modern guidance favours length and breach-checking over forced rotation and complexity rules, which drive predictable, weaker passwords.",
        "Enforce the policy centrally at the identity provider rather than per application.\nSet a minimum length of at least 12 characters, screen new passwords against known breach corpora, and make initial and reset passwords unique, single use and changed at first login.\nAvoid mandatory periodic rotation unless a credential is known or suspected to be compromised, or a regulation or contract you are bound by requires it, for example a change at least every 90 days where a password is the only factor protecting card data and account risk is not analyzed continuously.\nLock accounts after no more than ten failed attempts, for at least 30 minutes or until the user's identity is confirmed, or apply equivalent rate limiting where lockout is not available, and verify the person's identity through a separate channel before resetting a password or second factor.",
    ),
    (
        "IAM-07",
        "Privileged access management",
        "Administrative and root access can disable controls, read all data and erase its own traces. It therefore warrants tighter provisioning, shorter tenure and closer review than standard access.",
        "Maintain an inventory of privileged accounts across every system, including cloud root and break-glass accounts.\nRequire explicit, separately recorded approval for privileged grants.\nPrefer just-in-time elevation over standing administrative rights, and log every elevation.\nReview privileged access quarterly, and secure break-glass credentials with monitored, alerting access.",
        "Privileged access management",
        "Administrative and root access can disable controls, read all data and erase its own traces. It therefore warrants tighter provisioning, shorter tenure and closer review than standard access.",
        "Maintain an inventory of privileged accounts across every system, including cloud root, break-glass, database, network device and built-in administrator accounts, with a named owner for each, and of the tools that can bypass system or application controls, such as cloud and database admin consoles, container exec access, hypervisor tools and debuggers on production hosts.\nRequire explicit, separately recorded approval for privileged grants.\nPrefer just-in-time elevation over standing administrative rights, do privileged work from a separate account or elevated role rather than the one used for email and browsing, and log every elevation and every use of the listed tools.\nReview privileged access quarterly, keep break-glass and shared administrator credentials in a vault with monitored, alerting check-out, and record privileged sessions on the most sensitive systems, such as payment or core banking systems, where the tooling allows.",
    ),
    (
        "IAM-09",
        "Segregation of duties",
        "Where one person can initiate, approve and execute the same sensitive action, both fraud and simple error go undetected. Separating those duties introduces a second pair of eyes at the point where it matters.",
        "Identify conflicting duty pairs, such as deploying to production and approving that deployment, or creating a vendor and approving its payment.\nSeparate them in system permissions rather than by convention.\nWhere team size makes separation impractical, document a compensating control such as independent after-the-fact review of a logged action.\nRe-examine separation whenever the team grows or restructures.",
        "Segregation of duties",
        "Where one person can initiate, approve and execute the same sensitive action, both fraud and simple error go undetected. Separating those duties introduces a second pair of eyes at the point where it matters.",
        "Identify conflicting duty pairs, such as deploying to production and approving that deployment, creating a vendor and approving its payment, or entering and authorizing a financial transaction.\nSeparate them in system permissions rather than by convention, and where a system supports it enforce maker checker approval so the person who enters a sensitive action cannot also approve it.\nWhere team size makes separation impractical, document a compensating control such as independent after-the-fact review of a logged action.\nRe-examine separation whenever the team grows or restructures, and check user entitlements against the conflict matrix at least annually, or quarterly for payment and other high-risk financial systems.",
    ),
    (
        "LM-01",
        "Asset and system inventory",
        "Controls apply to systems that are known. An incomplete inventory means some portion of the estate is unpatched, unmonitored and unreviewed, and nobody can say which portion.",
        "Maintain an inventory of systems, cloud resources, endpoints and applications with owner and classification.\nCollect it automatically from cloud and identity APIs where possible, as manual inventories decay quickly.\nReconcile it against billing, DNS and identity records to find unregistered systems.\nReview the inventory periodically and remove decommissioned assets.",
        "Asset and system inventory",
        "Controls apply to systems that are known. An incomplete inventory means some portion of the estate is unpatched, unmonitored and unreviewed, and nobody can say which portion.",
        "Maintain an inventory of systems, cloud resources, endpoints and applications with owner and classification, including on-premises servers, network and security appliances, hardware security modules and removable media where you have them, and for installed software, hardware and appliances the license held and the date vendor support ends.\nCollect it automatically from cloud and identity APIs where possible, as manual inventories decay quickly.\nReconcile it against billing, DNS and identity records, and for sites you run against network discovery scans and a physical count, to find unregistered systems.\nReview the inventory at least quarterly and remove decommissioned assets.",
    ),
    (
        "LM-02",
        "Centralized logging and retention",
        "Logs are the raw material for detection, investigation and evidence. If they are scattered, short-lived or absent, an incident cannot be reconstructed and the operating history cannot be shown.",
        "Centralize security-relevant logs, including authentication, authorization, administrative action, and application audit events.\nRetain at least twelve months, with recent data immediately searchable.\nProtect logs against modification and restrict who can delete them.\nMonitor for logging gaps, as a source that stops sending is itself a signal.",
        "Centralized logging and retention",
        "Logs are the raw material for detection, investigation and evidence. If they are scattered, short-lived or absent, an incident cannot be reconstructed and the operating history cannot be shown.",
        "Centralize security-relevant logs, including authentication, authorization, administrative action, and application audit events.\nRetain at least twelve months, with at least the most recent three months immediately searchable.\nProtect logs against modification and restrict who can delete them, so the administrators of a system cannot alter or remove its logs.\nMonitor for logging gaps, as a source that stops sending is itself a signal, and review security events at least daily, by automated alerting or by a person.",
    ),
    (
        "LM-07",
        "Incident response plan",
        "Incidents are handled under time pressure with incomplete information. A plan written in advance is what makes the response consistent rather than dependent on who happens to be available.",
        "Maintain an incident response plan defining roles, severity levels and the phases of detection, containment, eradication, recovery and lessons learned.\nInclude internal and external communication steps, with the notification decision as an explicit gate.\nKeep contact details, escalation paths and vendor support routes current.\nReview the plan annually and after every significant incident.",
        "Incident response plan",
        "Incidents are handled under time pressure with incomplete information. A plan written in advance is what makes the response consistent rather than dependent on who happens to be available.",
        "Maintain an incident response plan defining roles, severity levels and the phases of detection, containment, eradication, recovery and lessons learned, and share it with everyone who holds a role in it.\nInclude internal and external communication steps, naming the parties each kind of incident must reach, such as customers, regulators, law enforcement, card brands or the acquirer, with the notification decision as an explicit gate.\nState who may collect evidence during an incident, how logs, disk images and files are captured without changing them, and how each item is stored with a record of who handled it and when.\nKeep contacts, escalation paths and vendor support routes current, and review the plan annually and after every significant incident.",
    ),
    (
        "LM-09",
        "Security anomaly alerting",
        "Alerting on everything trains responders to ignore alerts. A small set of high-signal alerts that are consistently acted on detects more than an exhaustive set that is muted.",
        "Alert on a deliberately limited set of high-signal conditions rather than on every anomaly.\nPrioritize unauthorized access attempts, unusual authentication patterns, privilege escalation, service unavailability and resource exhaustion.\nRoute each alert to an owner with a defined response, and remove alerts nobody acts on.\nReview alert volume and false-positive rate periodically, and tune deliberately.",
        "Security anomaly alerting",
        "Alerting on everything trains responders to ignore alerts. A small set of high-signal alerts that are consistently acted on detects more than an exhaustive set that is muted.",
        "Alert on a deliberately limited set of high-signal conditions rather than on every anomaly, drawing on identity, cloud, endpoint and application logs and, on networks you run yourself, intrusion detection at the perimeter and at critical internal points.\nPrioritize unauthorized access attempts, unusual authentication patterns, privilege escalation, unusual outbound traffic, changes to critical system files, service unavailability and resource exhaustion.\nRoute each alert to an owner with a defined response, and remove alerts nobody acts on.\nReview alert volume and false-positive rate at least quarterly, and tune deliberately.",
    ),
    (
        "LM-11",
        "Vulnerability management program",
        "New vulnerabilities are disclosed continuously against systems that were secure when deployed. A defined cadence of discovery and remediation is what keeps a hardened estate from drifting into exposure.",
        "Scan infrastructure, containers, dependencies and external surface on a defined schedule.\nDefine remediation SLAs by severity, and measure performance against them.\nTrack findings to closure with evidence, and require a documented risk acceptance for anything not remediated.\nFeed penetration test and bug report findings into the same tracker so all vulnerabilities are managed in one place.",
        "Vulnerability management program",
        "New vulnerabilities are disclosed continuously against systems that were secure when deployed. A defined cadence of discovery and remediation is what keeps a hardened estate from drifting into exposure.",
        "Scan infrastructure, containers, dependencies and the external surface on a defined schedule, at least quarterly and after significant change, using authenticated scans for internal systems and, where card data is in scope, an approved scanning vendor for external scans.\nDefine remediation SLAs by severity, and measure performance against them.\nTrack findings to closure with evidence, and require a documented risk acceptance for anything not remediated.\nFeed penetration test and bug report findings into the same tracker so all vulnerabilities are managed in one place.",
    ),
    (
        "NS-04",
        "Hardening baselines (CIS)",
        "Default configurations are built for compatibility, not security. A hardening baseline replaces those defaults with a known-good standard and gives drift something measurable to be measured against.",
        "Apply CIS Benchmarks or an equivalent hardening standard to operating systems, containers and cloud services.\nBuild baselines into images and infrastructure as code so new systems start hardened.\nDocument and approve any deviation from the baseline, with the reason.\nCheck for drift on a schedule and remediate regressions.",
        "Hardening baselines (CIS)",
        "Default configurations are built for compatibility, not security. A hardening baseline replaces those defaults with a known-good standard and gives drift something measurable to be measured against.",
        "Apply CIS Benchmarks or an equivalent hardening standard to operating systems, containers, databases, cloud services and network devices such as firewalls, routers, switches and wireless controllers, removing or disabling services and tools a system does not need.\nBuild baselines into images, infrastructure as code and device configuration templates so new systems start hardened, and back up network device configurations whenever they change.\nDocument and approve any deviation from the baseline, with the reason.\nCheck for drift at least quarterly, or continuously where tooling allows, remediate regressions, including network device firmware that has fallen out of vendor support, and review the baselines at least annually and when a new benchmark version is released.",
    ),
    (
        "NS-06",
        "Encryption key management",
        "Encryption reduces to key management. If keys are unprotected, over-shared or never rotated, the encryption they support provides far less assurance than it appears to.",
        "Manage keys in a dedicated KMS or HSM, held separately from the data they protect.\nRestrict key use and administration through policy, and separate those two permissions.\nEnable rotation on a defined schedule, and define a rotation procedure for compromise.\nLog and monitor key use, particularly decrypt operations at unusual volume.",
        "Encryption key management",
        "Encryption reduces to key management. If keys are unprotected, over-shared or never rotated, the encryption they support provides far less assurance than it appears to.",
        "Manage keys in a dedicated KMS or HSM, held separately from the data they protect, and for keys that protect card data, payment messages or interbank links, generate and load them inside an HSM under dual control and split knowledge, record each key ceremony with the named custodians, and have each custodian sign an acknowledgment of their duties.\nRestrict key use and administration through policy, and separate those two permissions.\nEnable rotation on a defined schedule, define a rotation procedure for compromise, and disable then destroy retired keys only once no data or backup still depends on them, recording each step.\nLog and monitor key use, particularly decrypt operations at unusual volume.",
    ),
    (
        "NS-07",
        "Network segmentation",
        "Flat networks let one compromised host reach everything. Segmentation limits blast radius and keeps data stores off paths that never needed to reach them.",
        "Place databases and internal services in private subnets with no route from the internet.\nDefine trust zones and control traffic between them with default-deny rules.\nSeparate production from development and corporate networks.\nVerify segmentation by testing reachability rather than by reading the intended design.",
        "Network segmentation",
        "Flat networks let one compromised host reach everything. Segmentation limits blast radius and keeps data stores off paths that never needed to reach them.",
        "Place databases and internal services in private subnets with no route from the internet.\nDefine trust zones and control traffic between them with default-deny rules.\nSeparate production from development and corporate networks, and keep guest and wireless networks apart from internal ones.\nVerify segmentation by testing reachability rather than by reading the intended design, at least yearly and after any change to the rules between zones, and every six months where segmentation reduces the scope of card data you handle on behalf of customers.",
    ),
    (
        "PE-01",
        "Cloud physical security (subservice review)",
        "Where infrastructure runs in a cloud provider, physical security is performed by that provider and carved out of your audit. Reviewing their report is what makes that reliance a verified control rather than an assumption.",
        "Obtain the provider's current SOC 2 or ISO 27001 report at least annually.\nReview the exceptions and the complementary user entity controls, and confirm you operate the controls the provider expects of you.\nDisclose the subservice organization and the carve-out in the system description.\nRecord the review, the reviewer and any issues identified.",
        "Cloud physical security (provider assurance review)",
        "Where infrastructure runs in a cloud provider, physical security is performed by that provider and inherited rather than operated by you. Reviewing their independent assurance is what makes that reliance a verified control rather than an assumption.",
        "Obtain the provider's current independent assurance at least annually, such as a SOC 2 Type II report, an ISO/IEC 27001 certificate with its Statement of Applicability, or a PCI DSS Attestation of Compliance where card data is involved, and confirm it covers the regions and services you use.\nReview any exceptions or exclusions and the controls the provider expects of you, such as complementary user entity controls or a shared responsibility matrix, and confirm you operate them.\nDocument the reliance, and which controls the provider operates, in your scope documents, such as the SOC 2 system description, the ISO/IEC 27001 Statement of Applicability or the PCI DSS service provider responsibility matrix.\nRecord the review, the reviewer and any issues identified.",
    ),
    (
        "PE-02",
        "Office physical access controls",
        "Offices still hold laptops, printed material and network access. Where an office is in scope, physical access control is what stops digital controls from being bypassed by simply walking in.",
        "Control office entry with badge or equivalent access, and restrict server or network areas further.\nMaintain a visitor log and require visitors to be escorted in sensitive areas.\nRevoke badges as part of offboarding, and reconcile active badges against active staff periodically.\nRetain access records for a defined period, and secure printed confidential material and disposal.",
        "Office physical access controls",
        "Offices still hold laptops, printed material and network access. Where an office is in scope, physical access control is what stops digital controls from being bypassed by simply walking in.",
        "Control entry to offices and to any server room, data center or recovery site you run with badge or equivalent access, restrict server and network areas further, receive deliveries at a controlled point away from them, and keep those areas and screens showing sensitive work out of public view.\nKeep a visitor log, escort visitors in secure areas, and set written rules for secure areas, such as no unsupervised visitors or contractors and no photography or recording without approval.\nDetect unauthorized entry with intruder alarms or cameras that alert a named responder or monitoring service, or record the monitoring the building provides, and review alarm events, access exceptions and active badges against active staff at least quarterly.\nRevoke badges at offboarding, retain access records and any footage for a defined period of at least 90 days where the law allows, secure printed confidential material and its disposal, and check desks, printers and secure areas on a quarterly walk-through.",
    ),
    (
        "SD-01",
        "Change authorization and approval",
        "Unauthorized change is the most common cause of both outages and security regressions. Requiring changes to be authorized, tested and approved before they reach production is the core of the change-management criterion.",
        "Require every production change to carry a recorded authorization and approval before deployment.\nApply the same requirement to database migrations, configuration and infrastructure changes, not only application code.\nLink the deployment to the approved change record so the two can be reconciled at audit.\nDetect and investigate deployments that reach production without a corresponding approval.",
        "Change authorization and approval",
        "Unauthorized change is the most common cause of both outages and security regressions. Requiring changes to be authorized, tested and approved before they reach production is the core of change management.",
        "Require every production change to carry a recorded authorization and approval before deployment, with its expected impact and how it would be rolled back stated on the change record, and where a change advisory board exists, record its review and decision for high-risk changes and keep a change calendar with agreed freeze periods.\nApply the same requirement to database migrations, configuration and infrastructure changes, and to software installed or updated directly on servers, not only application code; routine low risk changes such as scheduled patching may run under a standard change approved in advance and reviewed yearly.\nLink the deployment to the approved change record so the two can be reconciled at audit.\nDetect and investigate deployments that reach production without a corresponding approval.",
    ),
    (
        "SD-03",
        "Dependency and image scanning",
        "Most application code is third-party dependency code, and vulnerabilities in it are disclosed continuously. Without automated scanning the first notice of an exposed dependency is usually an external report.",
        "Enable dependency and container image scanning on every repository and registry.\nFail builds on newly introduced critical vulnerabilities rather than only reporting them.\nTriage alerts to a severity-based SLA and track remediation to closure.\nMaintain a software bill of materials so exposure to a new disclosure can be assessed quickly.",
        "Dependency and image scanning",
        "Most application code is third-party dependency code, and vulnerabilities in it are disclosed continuously. Without automated scanning the first notice of an exposed dependency is usually an external report.",
        "Enable dependency and container image scanning on every repository and registry.\nFail builds on newly introduced critical vulnerabilities rather than only reporting them.\nTriage alerts to a severity-based SLA and track remediation to closure.\nMaintain a software bill of materials that records each component's license, so exposure to a new disclosure can be assessed quickly and licenses that conflict with how the product is used or sold are flagged for review before release.",
    ),
    (
        "SD-06",
        "Peer code review (branch protection)",
        "Peer review catches defects and security weaknesses before they reach production and spreads knowledge across the team. Enforced through branch protection, it also produces the authorization trail the change criterion expects.",
        "Require a pull request with at least one approving review from someone other than the author.\nEnforce it through branch protection, and disable direct pushes to protected branches.\nRequire status checks to pass before merge, and prohibit self-approval.\nRecord any use of an administrator override and review those occurrences.",
        "Peer code review (branch protection)",
        "Peer review catches defects and security weaknesses before they reach production and spreads knowledge across the team. Enforced through branch protection, it also produces the authorization trail that change management depends on.",
        "Require a pull request with at least one approving review from someone other than the author.\nEnforce it through branch protection, and disable direct pushes to protected branches.\nRequire status checks to pass before merge, and prohibit self-approval.\nRecord any use of an administrator override and review those occurrences.",
    ),
    (
        "SD-08",
        "Processing reconciliation and monitoring",
        "Reconciling outputs against inputs is what demonstrates that processing was complete and accurate. A job that reports success while dropping records is invisible without it.",
        "Monitor job execution for success, failure and non-execution, including jobs that silently do not start.\nReconcile record counts and control totals between source and destination for each run.\nAlert on breaks and investigate them rather than reprocessing blindly.\nRetain reconciliation results, as they are the primary evidence for the processing integrity criteria.",
        "Processing reconciliation and monitoring",
        "Reconciling outputs against inputs is what demonstrates that processing was complete and accurate. A job that reports success while dropping records is invisible without it.",
        "Monitor job execution for success, failure and non-execution, including jobs that silently do not start.\nReconcile record counts and control totals between source and destination for each run.\nAlert on breaks and investigate them rather than reprocessing blindly.\nRetain reconciliation results, as they are the primary evidence that processing was complete and accurate.",
    ),
    (
        "SD-10",
        "Secure SDLC policy",
        "A documented development lifecycle is how security requirements become routine engineering practice rather than individual habit. It also gives new engineers a defined standard to work to, which is what keeps quality stable as a team grows.",
        "Maintain a secure development policy covering design review, code review, testing, environment use and deployment.\nInclude security requirements such as secure coding standards, dependency management and secrets handling.\nDefine how changes are approved and released, and how emergency changes are handled.\nReview the policy annually and align it with the tooling actually in use.",
        "Secure SDLC policy",
        "A documented development lifecycle is how security requirements become routine engineering practice rather than individual habit. It also gives new engineers a defined standard to work to, which is what keeps quality stable as a team grows.",
        "Maintain a secure development policy covering design review, code review, testing, environment use and deployment, and list the design principles, such as least privilege, defense in depth, secure defaults and failing safely, that every new system and major change is built to, whether built in house or by a supplier.\nInclude security requirements such as secure coding standards, static code analysis in the pipeline, dependency management and secrets handling, and train everyone who writes or reviews code in them when they join and at least yearly.\nFor each new application, major feature or acquired system, record its security requirements, such as authentication, access, data classification, logging, privacy and legal needs, have them approved at design review before building or buying, and check they are met before release.\nDefine how changes are approved and released and how emergency changes are handled, and have the engineering lead review the policy annually against the tooling actually in use.",
    ),
    (
        "SD-12",
        "Separate dev/staging/production",
        "Testing in production exposes customer data to unreleased code and makes it impossible to distinguish deliberate change from experiment. Separate environments give changes somewhere to be validated before they carry real consequences.",
        "Maintain distinct development, staging and production environments with separate credentials and accounts.\nPromote changes through environments in a controlled sequence rather than deploying directly to production.\nRestrict production access to those who require it, and grant lower-environment access more freely.\nKeep production data out of lower environments, using masked or synthetic data instead.",
        "Separate dev/staging/production",
        "Testing in production exposes customer data to unreleased code and makes it impossible to distinguish deliberate change from experiment. Separate environments give changes somewhere to be validated before they carry real consequences.",
        "Maintain distinct development, staging and production environments with separate credentials and accounts.\nPromote changes through environments in a controlled sequence rather than deploying directly to production.\nRestrict production access to those who require it, and protect development and staging with their own access control, patching and monitoring even where access to them is wider.\nKeep production data out of lower environments, using masked or synthetic data instead.",
    ),
    (
        "SD-14",
        "Change traceability",
        "An auditor samples changes and asks to see the request, the approval, the review, the test result and the release for each. Where those live in different tools with no link between them, every sample becomes a manual hunt, and a gap in the trail looks like an unauthorized change.",
        "Require every production change to reference a ticket, issue or change request.\nLink pull requests to that ticket, and the deployment to the pull request or commit.\nRecord the approver on the ticket or the pull request, and keep both for the audit window.\nSample changes each quarter and confirm each can be followed from request to release.",
        "Change traceability",
        "An auditor samples changes and asks to see the request, the approval, the review, the test result and the release for each. Where those live in different tools with no link between them, every sample becomes a manual hunt, and a gap in the trail looks like an unauthorized change.",
        "Require every production change to reference a ticket, issue or change request.\nLink pull requests to that ticket, and the deployment to the pull request or commit.\nRecord the approver on the ticket or the pull request, and retain both for at least twelve months, or longer where the next external audit covers a longer period or the retention schedule requires it.\nSample changes each quarter and confirm each can be followed from request to release.",
    ),
)

_UNEDITED = sa.text(
    "CREATE TEMPORARY TABLE _unedited_controls ON COMMIT DROP AS "
    "SELECT c.id FROM controls c JOIN control_templates t ON c.template_id = t.id "
    "WHERE c.name IS NOT DISTINCT FROM t.name "
    "AND c.description IS NOT DISTINCT FROM t.description "
    "AND c.implementation_guidance IS NOT DISTINCT FROM t.implementation_guidance"
)

_TEMPLATE = sa.text(
    "UPDATE control_templates SET name = :name, description = :description, "
    "implementation_guidance = :guidance WHERE code = :code"
)

_PROPAGATE = sa.text(
    "UPDATE controls c SET name = t.name, description = t.description, "
    "implementation_guidance = t.implementation_guidance "
    "FROM control_templates t "
    "WHERE c.template_id = t.id AND c.id IN (SELECT id FROM _unedited_controls)"
)


def _apply(offset: int) -> None:
    bind = op.get_bind()
    op.execute("ALTER TABLE controls NO FORCE ROW LEVEL SECURITY")
    try:
        bind.execute(_UNEDITED)
        for row in CONTENT:
            bind.execute(
                _TEMPLATE,
                {
                    "code": row[0],
                    "name": row[offset],
                    "description": row[offset + 1],
                    "guidance": row[offset + 2],
                },
            )
        bind.execute(_PROPAGATE)
        op.execute("DROP TABLE IF EXISTS _unedited_controls")
    finally:
        op.execute("ALTER TABLE controls FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    _apply(4)


def downgrade() -> None:
    _apply(1)
