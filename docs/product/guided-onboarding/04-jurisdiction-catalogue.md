# Country reference: the rules a company should know, by where it operates

Part 4 of the guided onboarding plan. Read [README.md](README.md) first. Requirements are group JC
in [part 2](02-requirements.md). The screen is section 13 of [part 3](03-experience.md).

## 1. What this is, and what it is not

When a company says where it is registered, where its people are and where its customers are, the
product shows the security, privacy and sector rules it should know about, in plain words, with
dates and sources. It is there so a founder in Karachi selling to Riyadh and Frankfurt learns in
one screen that three data protection regimes and two national control sets are in play.

| It is | It is not |
|---|---|
| A reference list, curated and reviewed by people | Legal advice |
| Matched to the profile with a stated reason | A decision that a law applies |
| A pointer to the controls already run that help | A compliance score, gap figure or readiness claim |
| An input to the obligations register (ISO clause 4.2, control GOV-05) | A new framework with requirements and status |
| Dated, sourced and versioned content | Text generated for each workspace at run time |

A framework that Verity supports with requirements and status (SOC 2, ISO 27001, later HIPAA and
GDPR) is a different thing. An entry here can say "available as a framework" and link to it.

## 2. The decision: written once, reviewed, shipped

The request was: when the user picks a country, generate the applicable requirements with AI, once
for all. The plan reads that as: **use AI to draft the catalogue once, offline, have a person
review it, and ship it as content.** Every workspace then reads the same reviewed entries.

| Option | For | Against | Verdict |
|---|---|---|---|
| Generate per workspace at run time | No content work up front | A model states law with confidence and is sometimes wrong. Two customers get different answers. Nothing can be reviewed before a user reads it. It sends profile data to a model for a legal question. It breaks the rule that AI output is a draft a person approves | Rejected |
| Curated pack, AI drafted, person reviewed, sealed | Same answer for everyone, reviewable, dated, works with AI off, no tenant data leaves | Content work, and a review cost each quarter | Chosen (decision D-7) |
| No catalogue | No risk | The user's request, and the one thing competitors do not offer | Rejected |

How "AI helps once" works in practice:

1. A research pass (done on 2026-11-21, 89 entries in `jurisdiction_catalogue.md`) drafts each
   entry from public sources and tags every source as read, summary only, or not opened.
2. A named person reviews each entry against the primary source and corrects it. Entries that
   could not be checked stay out of the pack or ship with state "unverified" hidden from users.
3. The pack is sealed and shipped like control content. The reviewer and date ride on each entry.
4. Each quarter the same loop runs on what changed. AI drafts the update, a person approves it.

A country outside the pack shows nothing invented. It shows the global entries and a line saying
no reference exists yet, and the request is counted for the provider (JC-7). The provider can then
commission that country through the same four steps.

## 3. Coverage of the first pack

| Jurisdiction | Code | Entries drafted | Sub choices |
|---|---|---|---|
| Australia | AU | 11 | none |
| European Union | EU | 10 | Member state differences are noted in text, not modelled |
| United Kingdom | GB | 5 | none |
| Pakistan | PK | 9 | none |
| United Arab Emirates | AE | 11 | Onshore, DIFC, ADGM. Dubai and Abu Dhabi sector rules as entries |
| Oman | OM | 6 | none |
| Saudi Arabia | SA | 10 | none |
| United States | US | 15 | States matter for privacy and breach laws. Modelled as one entry each with a state table in the detail |
| Global, by activity | GLOBAL | 12 | Card data, SWIFT, enterprise sales, health buyers, car makers, AI governance |

The United Kingdom was not in the original request. It is included because "European" customers
usually include it and its law diverged from the EU's in 2025.

### 3.1 What a company sees first, by jurisdiction

"Most companies here should know" is open by default. "Depends on your sector" appears only when
the profile matches.

| Jurisdiction | Most companies here should know | Depends on your sector |
|---|---|---|
| Australia | Privacy Act with the privacy principles and breach notification. Cyber Security Act ransomware payment reporting. Essential Eight as the expected baseline | Critical infrastructure law (and data storage providers). Prudential standards for regulated financial firms and their vendors. Government security manual and assessor programme. Consumer Data Right. Financial services licence duties. Health records laws |
| European Union | GDPR. Cookie and marketing rules. NIS2, since medium sized software, cloud and managed service providers are in scope. AI Act when any AI is used or sold | DORA for financial entities and their technology vendors. Cyber Resilience Act for product makers. Data Act. Digital identity rules. Certification schemes |
| United Kingdom | UK GDPR and the 2018 and 2025 Acts, with the complaints duty and regulator fee. Marketing and cookie rules. Cyber Essentials as the baseline and public sector entry ticket | Network and information systems rules and the pending bill. Financial regulators' resilience rules. Product security law for device makers |
| Pakistan | The electronic crimes law and its duties on service providers. The fact that the data protection bill is **not yet law**, shown as a watch item. National CERT rules and the 2026 information security framework when dealing with government | Central bank technology governance and cloud outsourcing frameworks. Securities regulator guidelines for insurers. Telecom regulator security regulations. Cloud first policy for public sector suppliers |
| United Arab Emirates | Which privacy law applies: the federal law onshore, the DIFC law, or the ADGM regulations. The cybercrime law. The child digital safety law for consumer platforms | National information assurance standard. Dubai information security regulation and cloud provider certification. Abu Dhabi health information standard and the health data law. Central bank rules |
| Oman | Personal data protection law and its executive regulations, now enforced: officer, 72 hour breach notice, permits for sensitive data. The 2026 cybercrime law | Central bank framework. Cloud and data centre regulation with location rules for classified data. Government security controls. Electronic transactions law for trust services |
| Saudi Arabia | Personal data protection law: registration, officer, 72 hour breach notice, transfer rules. The national controls for private companies that are not critical infrastructure. The cybercrime law | Essential controls and their extensions for government and critical sectors. Cloud controls and cloud regulations. Central bank frameworks. National data office standards |
| United States | State privacy laws with their threshold tests. State breach notification laws. The federal unfair practices baseline. NIST CSF as the common voluntary reference | HIPAA. Financial safeguards rule. New York financial cyber regulation. Listed company disclosure rules and internal control law. Federal cloud authorisation and agency security law. Defence supply chain rules. Children's privacy. Critical infrastructure reporting. State AI laws |
| Global | none | Card data: PCI DSS. SWIFT connection: its customer security framework. Enterprise sales: ISO 27001 or SOC 2. United States health buyers: HITRUST. Car makers: TISAX. AI governance: ISO 42001 |

## 4. What an entry holds

One shape for every entry, so the screen never has to special case a country.

| Field | Meaning | Example |
|---|---|---|
| `key` | Stable id | `SA-01` |
| `jurisdiction` | Code, with an optional zone | `SA` |
| `short_name`, `official_name` | What people call it, and its formal title | PDPL |
| `issuer`, `regulator` | Who made it, who enforces it | |
| `kind` | One or more of: privacy, cybersecurity, resilience, AI, financial sector, health sector, telecom sector, government sector, critical infrastructure, payments, product security, identity | privacy |
| `topic_column` | Which column of the matrix it sits in: privacy, security baseline, breach clock, data location, sector, AI | privacy |
| `force` | Law, regulation, regulator rule, contract standard, voluntary framework | law |
| `state` | In force, in force with dates coming, passed and not yet in force, draft, suspended, voluntary, unverified | in force |
| `state_note` | One or two sentences on where it stands | |
| `tier` | Most should know, sector, also worth knowing | most should know |
| `applies_to` | Who it reaches, in plain words | |
| `duties` | Three to six headline duties, each with a topic (breach notice, officer, location, transfers, baseline, registration, assessment, incident reporting, penalties, consent, board duty, third parties) and, where one exists, a clock in hours | Breach notice, 72 hours |
| `assurance` | None, attestation, certification or registration, with a note | |
| `iso27001`, `soc2` | Named or accepted, helps partly, not relevant, not a substitute, with one sentence | helps partly |
| `helps` | Control codes already in the library that help | DM-01, IAM-08 |
| `not_covered` | Topics no Verity control covers | Transfers outside the Kingdom |
| `framework_code` | Set when Verity supports it as a framework | none |
| `milestones` | Dated events: enacted, in force, duty starts, deadline, proposed, suspended, consultation closes. Each with a precision and whether it is confirmed | |
| `sources` | Address, publisher, kind (official, regulator guidance, law firm, tracker), date read, how well verified | |
| `reviewed_by`, `reviewed_on`, `next_review_due`, `content_version` | Review trail | |
| `triggers` | When to show it (section 5) | |

Wording rules for content authors:

- Own words only. No statute, standard or regulator text is copied.
- A duty is one sentence a non lawyer can act on or ask counsel about.
- A draft is never described as a duty. "Would require" for bills.
- No penalty figure appears unless read from the primary text by the reviewer.
- No sentence says "you must" or "you are subject to". Use "applies to organisations that".

## 5. When an entry is shown

An entry is shown when **any** of its trigger groups matches, and a group matches when **all** of
its conditions do. Conditions read profile fields only.

| Profile field | Example condition |
|---|---|
| `hq_country`, `operating_countries` (with zone) | Operates in Saudi Arabia |
| `customer_regions` | Customers or data subjects in the European Union |
| `data_hosting_regions` | Hosts data in Oman |
| `industry`, `regulator_licences` | Holds a payments licence |
| `customer_types` | Sells to government |
| `personal_data_role`, `sensitive_data` | Handles health data |
| `critical_or_provider` | Provides cloud services to others |
| `ai_use`, `connected_products` | Product uses AI that affects people |
| `headcount_band`, `revenue_band` | 50 people or more |
| `listed_or_swift` | Listed in the United States |
| `existing_assurance` | Holds ISO 27001 (changes the "helps" line, never the match) |

Each group carries one of three confidence words, which choose the sentence on the card:

| Confidence | Sentence | Used when |
|---|---|---|
| applies | "Shown because you are registered in Saudi Arabia." | The trigger is establishment in the country and the rule is general |
| likely applies | "Shown because your customers are in the European Union and you hold personal data." | Reach from outside, or thresholds the profile mostly answers |
| check | "Shown because you sell to banks in Australia. Whether it reaches you depends on your contracts." | Rules that reach vendors through contracts, or thresholds the profile cannot answer |

A missing answer ("not sure yet", or a threshold band not given) never hides an entry of the first
tier. It downgrades the wording to "check" and names the missing answer.

## 6. Linking to the control library

Two links, both honest about their limits.

**Into the obligations register.** Marking an entry relevant offers to add a row to the workspace's
context and obligations register (template `context-and-interested-parties`, control GOV-05), with
the entry's name, regulator and the user's note. That register is what an ISO auditor reads.

**"Controls you already run that help".** A list of library controls per entry. It is shown as a
count and opens a filtered controls register. The words under it are fixed:

> These controls support this area. This is not an assessment against the law, and running them
> does not make you compliant with it.

The compliance review produced the first version of these lists for the entries people ask about
most. Entries not in the table ship with no list.

| Regulation | Controls you already run that help | Not covered by any control |
|---|---|---|
| GDPR and UK GDPR | Principles: DM-07, DM-08, DM-12, DM-05. Consent and notice: DM-03, DM-15. Rights: DM-11, DM-05, DM-14, DM-16. Processors: DM-10, DM-17, BC-06, BC-08. Records: DM-06, DM-12. Security: IAM-03, IAM-08, NS-01, NS-02, NS-06, BC-01, BC-02, LM-11, GOV-16, GOV-18. Breach: DM-01, DM-02, LM-07, CS-01. By design: SD-10, DM-13, DM-18 | Lawful basis other than consent, impact assessments, data protection officer, transfers outside the region, representative, automated decisions |
| Australian Privacy Act | DM-15, DM-07, DM-12, DM-09, DM-05, DM-11, DM-08, DM-16, IAM-08, NS-01, NS-02; breach scheme: DM-01, DM-02, LM-07 | Overseas disclosure accountability, anonymity option, direct marketing rules |
| Saudi PDPL | DM-03, DM-15, DM-07, DM-12, DM-11, DM-05, DM-08, DM-16, DM-10, DM-06, DM-01, NS-01, NS-02, IAM-08 | Transfer outside the Kingdom, officer appointment where required, impact assessment, registration duties |
| UAE PDPL | Same set as Saudi PDPL | Officer, impact assessment, cross border transfer conditions |
| Oman PDPL | Same set, with DM-03 for express consent | Permits for sensitive data, officer, transfer conditions |
| Pakistan PECA | LM-02 (log retention), LM-07, CS-07, DM-09, GOV-05, IAM-08 | It is a cybercrime law, not a data protection regime. Duties on service providers to keep traffic data and assist investigations need legal reading. No general data protection statute should be implied. |
| HIPAA | Administrative: GOV-18, GOV-19, GOV-20, GOV-11, GOV-10, HR-01, HR-05, HR-08, IAM-01, IAM-08, LM-04, LM-07, BC-01, BC-02, BC-03, GOV-13, DM-10, BC-08. Physical: PE-01, PE-02, EP-05, DM-16. Technical: IAM-03, IAM-04, IAM-11, NS-01, NS-02, LM-02. Breach: DM-01, DM-02 | Business associate terms, minimum necessary rule, emergency access, the required or addressable decision for each specification (FW-8) |
| PCI DSS | Network: NS-03, NS-07, NS-08, NS-10. Configuration: NS-04. Stored data and keys: NS-01, NS-06, DM-08, DM-18. Transit: NS-02. Malware: EP-01. Development and change: SD-01, SD-03, SD-05, SD-06, SD-10, SD-12, LM-11, EP-04. Access: IAM-01, IAM-03, IAM-06, IAM-07, IAM-08, IAM-10, IAM-11. Physical: PE-01, PE-02, PE-03, DM-16. Logging: LM-02, LM-09, NS-12. Testing: GOV-16, NS-05, LM-03. Program: GOV-17, GOV-18, GOV-23, HR-01, HR-08, LM-07, BC-07, BC-08 | Cardholder data environment scoping, the standard's fixed parameters and frequencies, targeted risk analyses, customised approach, external scans by an approved vendor. No licence is held, so numbers only. |
| NCA ECC | Governance: GOV-10, GOV-13, GOV-15, GOV-17, GOV-18, GOV-21, GOV-05, HR-01, HR-08. Defence: LM-01, IAM family, EP family, NS family, LM-02, LM-09, LM-11, GOV-16, LM-07, PE-02, DM-04, BC-01. Resilience: BC-03. Third party and cloud: BC-07, BC-08, PE-01 | National requirements such as roles held by nationals, hosting inside the Kingdom, reporting to the authority |
| SAMA CSF | Leadership and governance: GOV-02, GOV-10, GOV-17, GOV-21, HR-08, HR-09. Risk and compliance: GOV-05, GOV-06, GOV-13, GOV-18, GOV-19, GOV-20. Operations and technology: IAM, SD, NS, EP, LM families, BC-03, PE-02, PE-03. Third party: BC-05, BC-07, BC-08, PE-01 | Maturity level scoring, payment system and electronic banking requirements, regulator reporting |
| APRA CPS 234 | Roles: GOV-02, GOV-10, GOV-21. Capability: HR-09, GOV-26. Policy: GOV-17. Asset identification and classification: LM-01, DM-04, DM-06. Controls at third parties: BC-08, PE-01. Incidents: LM-07, LM-10. Testing: GOV-06, GOV-16. Internal audit: GOV-13 | Notification to the regulator within the set periods as a tracked control |
| NIS2 | GOV-17, GOV-18, LM-04, LM-07, BC-01, BC-02, BC-03, BC-06, BC-07, BC-08, SD-10, LM-11, SD-03, GOV-06, GOV-13, GOV-16, HR-08, NS-01, NS-02, NS-06, HR-01, HR-05, IAM family, LM-01, IAM-03, NS-11, GOV-02 | Staged incident reporting deadlines, registration, national differences |
| DORA | Risk framework: GOV-02, GOV-17, GOV-18, GOV-19. Incidents: LM-04, LM-05, LM-07, DM-01. Testing: GOV-16, BC-02, LM-10. Third parties: BC-06, BC-07, BC-08. Sharing: CS-07, LM-12 | Register of contractual arrangements in the prescribed form, mandatory contract clauses, threat led testing, major incident classification, concentration risk |

The "not covered" column is shown on the card as plain topics. It is the most useful line for a
reader: it says where the platform stops and counsel starts.

## 7. What the workspace stores

Only the person's own decisions. The catalogue itself is global content.

| Stored per workspace | Purpose |
|---|---|
| Relevance of an entry: suggested, marked relevant, marked not relevant | The user's own decision, with note, member and time |
| Whether a row was added to the obligations register | Avoids duplicates |
| The profile version the suggestions came from | So a profile change can show "2 new, 1 no longer shown" |

Nothing else. No status, no evidence, no owner. If a customer needs to manage a law as work, that
is a framework, and it goes through the framework process of the common control framework spec.

## 8. Review and upkeep

| Rule | Detail |
|---|---|
| Before first release | Every entry checked against a primary source by a named reviewer. For Pakistan, the United Arab Emirates, Oman and Saudi Arabia, where official English sources are thin, by counsel or a practitioner in that country (decision D-8) |
| Quarterly | Full review of every entry. `reviewed_on` and `next_review_due` updated |
| Monthly | Entries whose state is draft, suspended, phasing or unverified, and the dates coming up |
| On a date | When a milestone date passes, the entry is checked and its state updated |
| Overdue | An entry past `next_review_due` shows "Review overdue" to users (JC-9). It is not hidden |
| Errors | "Report an error" on every entry opens a short form that reaches the provider |
| Changes | A content change is a new pack version with a change note. Workspaces see "Updated on [date]" on the entry |
| AI | May draft an update. A person approves it. The approval is recorded on the entry |

## 9. The disclaimer

Shown as a banner on the panel in short form and in full behind "About this page".

> This page is general reference information to help you find laws and standards that may be
> relevant to your organisation. It is not legal advice. It may not be complete or current, and
> whether a rule applies to you depends on your facts. Status and dates were last reviewed on
> [date]. Confirm what applies with qualified counsel in each country before relying on it.
> Marking an item relevant or not relevant is your own decision and is recorded as such.

## 10. State of the draft content

The 89 drafted entries are research notes, not shippable content.

| Fact | Consequence |
|---|---|
| Most sources are search summaries. Several official sites refused automated reading | Every entry needs a human read of the primary source |
| 18 groups of items could not be verified, listed at the end of the research notes | They ship as state "unverified" and stay hidden, or are fixed in review |
| Several regimes moved in 2026: Oman's new cybercrime law and enforced data protection law, Saudi controls for ordinary private companies, an amended EU AI Act, a suspended phase of the United States defence programme, Pakistan's data protection still a bill, UAE executive regulations still not issued | The pack must carry dates and a state note, and the monthly check matters |
| About thirty dated changes fall in the next twelve months | The "Dates coming up" strip has real content from day one |

**Source check of the first tier, 2026-11-21.** An AI pass opened official or regulator pages for the
26 "most companies should know" entries (`research_notes/Guided onboarding plan/jurisdiction_first_tier_check.md`
in the owner's notes folder). It is a source check to help the reviewer, not a legal review.
17 confirmed, 8 corrected, 1 not confirmed. Corrections that change a date, status or clock:
Oman's data protection law was amended by Royal Decree 68/2026 (in force 7 September 2026);
Oman's new cybercrime law took effect 8 June 2026; ADGM's regulations applied from 14 August 2021
(new entities) and 14 February 2022 (existing); the UAE child digital safety law has an
implementing resolution (106/2026) with a platform deadline of 30 June 2027; Pakistan's 2026
information security framework sets 12, 15 or 18 month timelines by tier from an unknown start;
Australia's ransomware reporting applies above AUD 3 million turnover; Saudi draft amendments
would apply the 72 hour clock to every breach.

**Follow up the same day.** The eight corrections are applied to the draft, and the four blocked
entries were rechecked against official texts (gazette and regulator pages, read in a browser where
automated reads were refused): OM-01 rewritten for Royal Decree 68/2026 (the decree left the breach
and officer articles alone; the 72 hour clocks come from the regulations); PK-07 binds government
bodies, state corporations and designated critical infrastructure, with 12, 15 or 18 month
timelines; SA-05 binds a company once the national authority notifies it, with no deadline in the
text; AE-02 has no hour count for breach notice ("as soon as practicable"). US-15 checked against the
regulator's site. Still for the human reviewer: when the Pakistan clock starts and whether the notice
is in the gazette, the Saudi adoption date (law firm sources only), and official dates for the UAE
child safety resolution. Nothing ships before that review (decision D-8).

## 11. Acceptance for the first release

1. A workspace registered in Pakistan with customers in Saudi Arabia and the European Union sees,
   in the first tier: the Pakistan electronic crimes law, the Pakistan bill as a watch item, the
   Saudi data protection law, the Saudi private sector controls, GDPR and NIS2, each with a reason
   sentence that quotes the answer behind it.
2. No number on the page suggests a degree of compliance.
3. Every entry shows state, last reviewed date and at least one source.
4. A bill is drawn in the neutral style and reads "Not law yet".
5. Selecting a country outside the pack shows the global tier and the "no reference yet" line.
6. Marking an entry relevant writes one audit row and offers the obligations register row.
7. The page renders with AI switched off and with no network access to anything but the API.
8. Changing the profile's countries updates the panel without a reload of the workspace.

## 12. Work packages

| Package | Contents | Effort | Depends on |
|---|---|---|---|
| J1 Content model and pack | Tables or files for entries, duties, milestones, triggers, sources. Loader branch, seal, content tests. Contract documents updated for the new global content | medium | Decision D-7. Spec approved |
| J2 Review of the first pack | 89 entries read against primary sources, corrected, signed | large, mostly reviewer time | Decision D-8 |
| J3 Matching | Trigger evaluation over the profile, the three wordings, the "not sure" downgrade | small | Profile fields (part 2) |
| J4 Panel | Chips, matrix, cards, dates strip, drawer, disclaimer | medium | J1, J3, `CountrySelect` |
| J5 Decisions and register link | Relevance per entry, obligations register row | small | J4, the context register template |
| J6 Provider side | Requests for uncovered countries as a log event with the country code only, and where "Report an error" lands. A provider view comes later | small | J4 |

J1, J3 and J4 can be built against five reviewed entries. J2 runs alongside and decides the
release date.
