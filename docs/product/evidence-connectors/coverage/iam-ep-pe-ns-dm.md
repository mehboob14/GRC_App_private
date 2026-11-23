# Evidence coverage: IAM, EP, PE, NS and DM

Families: identity and access (IAM), endpoints (EP), physical (PE), network and cloud security (NS)
and data management and privacy (DM). 53 controls today, 5 more proposed below. Written to
`AUTHORING.md` sections 5 and 6. Machine readable files beside this one:

- `iam-ep-pe-ns-dm.json`: one entry per artifact per control, in the proposed structure
  (321 entries, 162 distinct artifacts, two of them proposed).
- `iam-ep-pe-ns-dm.controls.json`: one decision per control (keep, revise objectives, split, add).

This is a plan. Nothing here changes content JSON, and every mapping or objective change below is a
proposal for the qualified review of FW-5. The mappings are Verity's reading, reviewed internally only.

## Proposed control changes

| Decision | Count | Controls |
|---|---|---|
| keep | 33 | IAM-05, IAM-08 (mapping change only), IAM-10, IAM-11, EP-01, EP-02, EP-05, EP-06, NS-01, NS-05 to NS-10, NS-12, PE-01 to PE-03, DM-02, DM-04 to DM-07, DM-09, DM-10, DM-12 to DM-15, DM-17 to DM-19 |
| revise objectives | 16 | IAM-01, IAM-02, IAM-03, IAM-04, IAM-06, IAM-07, IAM-12, EP-03, EP-07, NS-02, NS-03, NS-11, DM-01, DM-03, DM-08, DM-11 |
| split | 4 | IAM-09 to IAM-13, EP-04 to NS-13, NS-04 to NS-14, DM-16 to EP-08 |
| add | 1 | IAM-14 |
| merge or deprecate | 0 | none found that duplicates a whole activity; two duplicated objectives are fixed by rewording (IAM-04.D against IAM-12.D, DM-08.C against DM-16.D) |

The test used: split only when the parts have different owners in the owner function table, can be
applicable independently, or reach requirements of a different nature, and when a connector check would
otherwise have to land on a control it only half fits. Configuration and monitoring parts that share an
owner and always apply together stay together (EP-01, NS-05, NS-10, DM-19).

### Splits

| Control | Stays on the original code | Successor (proposed) | Owner of successor | Successor applies when | Objectives | Mapping | Which checks move |
|---|---|---|---|---|---|---|---|
| IAM-09 Segregation of duties | Technology duties: change author and approver, deployer, administrator and log reviewer, granter and reviewer of access | IAM-13 Segregation of duties in finance and payment processes | finance lead | in scope finance or payment processes, or services that affect customers' financial reporting | IAM-09.A, C, D reworded; IAM-13.A to D new | A.5.3 full becomes partial on both; CC5.1 partial added to IAM-13 | `idp.access_list_exported` and `vcs.merged_changes_reviewed` stay on IAM-09 |
| EP-04 Patch management | Company devices: laptops, desktops, mobile | NS-13 Server and container image patching | engineering lead | the company runs servers, VMs or images it maintains | EP-04.A, C, D reworded; EP-04.E moves to NS-13.E; NS-13.A to D new | A.8.8, CC7.1, CC6.8 partial on both | `devices.os_current` stays; `scanner.scans_current`, `verity.vulns.within_sla` and cloud patch needs go to NS-13 |
| NS-04 Hardening baselines | Cloud services, servers, containers, databases | NS-14 Network equipment hardening and firmware | IT lead | own network equipment in offices or sites | NS-04.A, D reworded; NS-14.A to D new | A.8.20 moves from NS-04 to NS-14; A.8.9 full becomes partial on both | `cloud.hardening_baseline` stays; NS-14 has no connector |
| DM-16 Secure data disposal | Deleting data from every store and copy | EP-08 Equipment and media wiping and disposal | IT lead | always | DM-16.A reworded; DM-16.B, C move to EP-08.B, C; DM-16.E new (deletion at customer exit and on erasure request); EP-08.A new | A.7.14, A.7.10, CC6.5 move to EP-08; C1.2 full becomes partial on DM-16 and partial on EP-08; A.8.10 and P4.3 stay full on DM-16 | `verity.assets.disposal_recorded` moves to EP-08; `cloud.storage_lifecycle` stays |

### Addition

**IAM-14 Product sign in protections for customer users** (proposed, engineering lead, applies when
customers' users sign in to the product). No control tested how the product itself authenticates its
users: password rules, storage as a slow salted hash, lockout, reset links and second factor options.
IAM-03, IAM-04 and IAM-06 cover staff only; IAM-11 covers product sessions only. Maps SOC2:CC6.1,
ISO27001:A.8.5 and A.5.17, all partial. Objectives A to D; one proposed artifact
`product-sign-in-settings`. The `engineering-security-standard` template needs a product sign in section first.

### Objective revisions

| Control | Change | Requirement that drives it |
|---|---|---|
| IAM-01 | B adds movers; new F: access for auditors, testers and outside support approved by the system owner, time limited, removed | SOC2:CC6.3 (changes to access), ISO27001:A.8.34 (untested) |
| IAM-02 | C names the code host, build pipelines and registries as review scope | ISO27001:A.8.4 rationale |
| IAM-03 | New F: second factor on systems people sign in to directly (cloud console, code host, password manager, apps outside SSO) | ISO27001:A.8.5 and IAM-03.A; gives `vcs.org_two_factor_required` and `cloud.root_account_mfa` an objective |
| IAM-04 | D reworded from leaver removal to "apps behind SSO refuse local passwords"; the leaver side moves to IAM-12.D | duplicate of IAM-12.C and D |
| IAM-06 | New E: single use initial and reset passwords, identity check before a reset | ISO27001:A.5.17 rationale |
| IAM-07 | A covers the granting rules, break glass and logging; new F: each elevation and break glass use logged, alerted and reviewed | ISO27001:A.8.2 (full), A.8.18 |
| IAM-12 | B adds role changes; D gains the list of apps outside SSO | SOC2:CC6.3, ISO27001:A.5.18 |
| EP-03 | New E: software installs limited to the permitted list | ISO27001:A.8.19 rationale |
| EP-07 | C (server outbound web limits) moves to NS-03.E | owner and evidence are network rules, not the web filter |
| NS-02 | D gets a settings artifact a test can read (`internal-tls-enforcement-settings`, proposed) | operating objective tested only by reading the standard |
| NS-03 | New E (from EP-07.C) | ISO27001:A.8.23 partial added |
| NS-11 | D split into D (per application access) and E (sessions logged and reviewed) | bundled configuration and monitoring |
| DM-01 | C limited to customer notices under contract; new E for regulator and individual notices where the company is controller | the personal data role switches which applies |
| DM-03 | New E: people told what follows if they refuse or withdraw consent | SOC2:P3.2 (then full) |
| DM-08 | C reworded to "the schedule covers every copy"; the deletion test stays in DM-16.D | duplicate of DM-16.D |
| DM-11 | New E: requests about customer data passed to the customer within the contract time | processor path |

### Mapping changes

| Requirement | Control | From | To | Why |
|---|---|---|---|---|
| SOC2:CC6.3 | IAM-02 | full | partial | Two full links (IAM-02, IAM-08) cannot both be true; neither alone authorizes, changes and removes access |
| SOC2:CC6.3 | IAM-08 | full | partial | as above |
| ISO27001:A.5.3 | IAM-09 | full | partial | finance duties move to IAM-13 |
| ISO27001:A.5.3 | IAM-13 | none | partial | new |
| SOC2:CC5.1 | IAM-13 | none | partial | new |
| ISO27001:A.8.23 | EP-07 | full | partial | server outbound limits move to NS-03 |
| ISO27001:A.8.23 | NS-03 | none | partial | receives EP-07.C |
| ISO27001:A.8.20 | NS-04 | partial | removed | its rationale described network equipment only |
| ISO27001:A.8.20, A.8.9 | NS-14 | none | partial | new |
| ISO27001:A.8.9 | NS-04 | full | partial | network equipment moves to NS-14 |
| ISO27001:A.8.8, SOC2:CC7.1, CC6.8 | NS-13 | none | partial | new |
| ISO27001:A.7.14, A.7.10, SOC2:CC6.5 | DM-16 | partial | removed | move to EP-08 |
| ISO27001:A.7.14, A.7.10, SOC2:CC6.5, C1.2 | EP-08 | none | partial | new |
| SOC2:C1.2 | DM-16 | full | partial | equipment wiping is EP-08 |
| SOC2:P3.2 | DM-03 | partial | full | only once DM-03.E ships |
| SOC2:CC6.1, ISO27001:A.8.5, A.5.17 | IAM-14 | none | partial | new control |

### What existing workspaces need

- No codes change meaning or get reused. Retired objective letters (EP-04.E, EP-07.C, DM-16.B, DM-16.C)
  are never reused; their objectives keep their letters in the successor where possible (NS-13.E,
  EP-08.B, EP-08.C). EP-07.C becomes NS-03.E because NS-03 already has a C.
- Each successor is an adoption proposal that a person confirms, with an audit row. The original keeps
  its evidence, history, owner and exceptions. No green result and no risk acceptance is copied to a
  successor, and old engagement conclusions stay as they were.
- `checks.json` mappings follow the split (`verity.assets.disposal_recorded` to EP-08, `scanner.scans_current`
  and `verity.vulns.within_sla` gain NS-13). That is a content change for the owner to approve.
- **Engine gap found while splitting.** Coverage is static, but applicability is not. When NS-14 or IAM-13
  is not applicable, A.8.9 or A.5.3 rests on one partial link and CL-3 reads it as partly covered, although
  the remaining control then covers everything that exists. The engine needs a way to say "full when the
  sibling is not applicable", or the split cannot ship without wrongly lowering ISO status.

## How to read this file

**Phase** is given per artifact per control, and names the source that carries most of the artifact's
weight for the objectives it serves:

| Phase | Meaning |
|---|---|
| P1 | A Verity module or a document template fills it with what Verity holds now. Some of these use new `verity.*` checks; the runner for Verity checks is not built yet (ME-2). |
| P2 | A signed Phase 2 connector: identity provider (Okta, Google Workspace, Entra ID), 1Password, AWS, Cloudflare or Tailscale, Jira, GitHub, GitLab or Bitbucket, Datadog or Sentry, PagerDuty or Slack. |
| P3 | A later or unsigned connector: device management, endpoint protection, HR systems, vulnerability scanners, Azure and Google Cloud, business applications. |
| people-only | Nothing a system holds can test the substance. A Verity module may still store the file. |

**fills** is about the artifact, not the control: `full` means that one source alone produces the whole
artifact for its objectives (11 places), `partial` everywhere else. No check here fully
proves a control. A P1 artifact backed by `verity.tasks.reviews_on_cadence` means Verity proves the review
happened on time and who signed it, never what the reviewer concluded.

**today** repeats the sources in `artifacts.json`. None of the checks it names for these artifacts runs
yet. Three GitHub checks used here already run: `vcs.org_two_factor_required` (IAM-03),
`vcs.merged_changes_reviewed` (IAM-09, DM-18) and `vcs.secret_scanning_enabled` (NS-09).

## Counts

| | Entries |
|---|---|
| P1 | 229 (144 led by a document template, the rest by a module; 19 rest on the review cadence check) |
| P2 | 55 |
| P3 | 29 |
| people-only | 8 |
| Entries under proposed controls | 23 |

Objectives in the proposed structure: 256 across 58 controls (229 today).
New `verity.*` checks: 14. NEED entries: 99 distinct predicates.

## Verity's own sign in and directory sync as evidence

Verity signs people in through Keycloak, which brokers to the customer's Entra ID, Google or Okta
(`docs/runbooks/keycloak-production.md`, `sso-providers.md`). What Verity holds about that is evidence
for **one application, Verity itself**, and it is honest only at that size:

| What Verity records | Fills | Limit |
|---|---|---|
| Workspace SSO on and required, proven domains, break glass Admins with TOTP | IAM-04 for Verity (`verity.identity.sso_required`) | One app of many behind the identity provider |
| Each sign in's provider, `acr` and `amr` in the session audit row | IAM-03: a sample of real sign ins where the provider's MFA applied (`verity.identity.second_factor_on_sign_in`) | Unverified whether Keycloak passes the upstream provider's method claims through brokering; if not, the check reports insufficient information |
| Hourly directory sync that disables leavers and moves roles, back-channel logout | IAM-12 and IAM-11 for Verity (`verity.identity.leavers_removed_by_sync`) | Needs a lifecycle feed (SCIM or LDAP) into Keycloak; the runbook records that this Keycloak build's SCIM server does not place users in organizations |
| Roles from mapped IdP groups, Admin holders | IAM-08 and IAM-07 for Verity (`verity.identity.roles_from_groups`) | Verity's roles govern Verity only |
| Password, lockout and idle timeout settings | IAM-06 and IAM-11 for Verity (`verity.identity.sign_in_settings`) | Only where password sign in is still allowed |

What it is not: Verity's member list is not a staff roster and never fills `roster-of-joiners-and-leavers-with`
(continuous-compliance-plan section 6 C says the same). The evidence connectors for Entra, Google and Okta
are a separate read only credential from the sign in app (`sso-providers.md` section 7); the sign in app
must not gain directory read rights to serve evidence. These checks need a new capability,
`verity_identity` (Verity members, roles and sign in), which `capabilities.json` does not have yet.

## New verity.* checks

All read Verity's own modules through their services, inside RLS, and keep no secrets (ME-6). None is
built. Each states population, predicate, period and the empty population rule (AUTHORING rule 4).

#### `verity.tasks.reviews_on_cadence` Periodic reviews happen on time and are signed off

| | |
|---|---|
| Capability | verity_tasks |
| Resource | task |
| Population | Every occurrence, due in the last 12 months, of a recurring task linked to the control (tasks with a recurrence rule and a link to the control). |
| Predicate | Each occurrence was closed, not cancelled, by its due date or within its SLA; has at least one attachment; and, where the template requires approval, was approved by an active member who is not its owner or assignee. |
| Empty population | Fail: no recurring review is set up for a control in scope. Verity owns this population, so an empty list is a real gap. |
| Results | Pass: all occurrences meet the predicate. Fail: one is late, cancelled, missing its record or self approved. Insufficient: an occurrence is still open inside its window (shown as pending). |
| Frequency | daily |
| Evidence kept | Occurrence list with due date, closed at, closer, approver, attachment names and hashes. |
| Controls | IAM-02, IAM-07, IAM-09, IAM-10, IAM-13, NS-03, NS-04, NS-05, NS-06, NS-07, NS-10, NS-12, NS-14, EP-07, DM-02, DM-06, DM-07, DM-19, PE-02, PE-03 (all partial: proves the review happened and who signed it, never what it concluded). |

#### `verity.tasks.approved_before_done` Requests are approved before they are done

| | |
|---|---|
| Capability | verity_tasks |
| Resource | task |
| Population | Tasks created in the period from a template marked as requiring approval (access request, privileged access request, new use of personal data). |
| Predicate | Each was approved before it was resolved or closed, by an active member who is neither its reporter nor its owner; a privileged access request was approved by the primary owner of the linked asset. |
| Empty population | Not applicable when no such template is in use (the company uses another request tool). Otherwise an empty period passes and is listed as none raised. |
| Results | Pass, fail per task as above. Insufficient: a privileged request with no linked asset, so the system owner is unknown. |
| Frequency | daily |
| Evidence kept | Task list with reporter, approver, approved at, closed at, linked asset and its owner. |
| Controls | IAM-01 (partial: approval before closure; the grant time in the target system comes from the identity provider or ticketing), DM-12 (partial: new uses approved before start). |

#### `verity.tasks.privacy_requests_on_time` Privacy requests are answered on time

| | |
|---|---|
| Capability | verity_tasks |
| Resource | task |
| Population | Tasks created from the privacy request templates (access, correction, erasure, consent withdrawal, inquiry or complaint) received (detected at) in the period. |
| Predicate | Each was closed by its SLA due date, set from the legal or contract deadline; its identity check subtask closed before its response subtask; it has a closure note; a request about customer data has its passed to the customer subtask closed within the contract time. |
| Empty population | Insufficient information: Verity cannot see the privacy mailbox or support tool, so an empty log needs a dated nil return filed by a person. |
| Results | Pass, fail as above. Error: none (internal data). |
| Frequency | daily |
| Evidence kept | Request list with type, received, due, identity check time, answered, outcome. |
| Controls | DM-03, DM-05, DM-11, DM-14, DM-16 (all partial: timeliness and order of steps, not the completeness of an answer). |

#### `verity.tasks.incident_notice_decided` Every incident has a recorded notice decision

| | |
|---|---|
| Capability | verity_tasks |
| Resource | task |
| Population | Issues created in the period from the incident template, and vendor breach notice tasks. |
| Predicate | Each has its notice decision subtask closed with a note naming the decision and who decided, including decisions not to notify; where notice was given, the notice subtask closed before the deadline recorded on it. |
| Empty population | Insufficient information: needs a dated nil return, because incidents may never have been raised in Verity. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Incident list with notice decision, decider, deadline, notice sent at. |
| Controls | DM-01, DM-02, DM-17 (partial: the decision is recorded and timely; whether it was right is legal judgement). |

#### `verity.exceptions.in_force` Control exceptions are approved and in force

| | |
|---|---|
| Capability | verity_risks |
| Resource | risk |
| Population | Open risks linked to the control whose treatment is accept (the control's recorded exceptions). |
| Predicate | Each has an approved acceptance in force: approver is not the requester (already a database rule), rationale filled with the reason and the safeguard, expiry not passed and no more than 12 months after the decision. An expired acceptance is listed with the date the gap reopened. |
| Empty population | Not applicable: no exceptions recorded. This is never reported as proof that no gap exists; the connector check for the control shows that. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Exception list with requester, approver, decided at, expiry, rationale. |
| Controls | IAM-01, IAM-03, IAM-04, EP-02, EP-07, NS-04, NS-08, NS-13, NS-14 (partial). Connector checks for the same control should treat an item named in an exception in force as excepted and list it, not fail it. |

#### `verity.identity.sso_required` Verity sign in goes through the identity provider

| | |
|---|---|
| Capability | verity_identity (new) |
| Resource | workspace |
| Population | The workspace's SSO configuration and every sign in to Verity by an active member in the last 90 days (session audit rows). |
| Predicate | SSO is on and required, at least one domain is proven, and every sign in by a member in a proven domain came through the identity provider. Password sign ins are only by break glass Admins with TOTP, each listed. |
| Empty population | Insufficient information when nobody signed in during the window. |
| Results | Pass, fail as above. Error: SSO status cannot be read from Keycloak. |
| Frequency | daily |
| Evidence kept | SSO settings, proven domains, sign in counts by method, list of password sign ins. |
| Controls | IAM-04 (partial: Verity is one application behind single sign on; the others need idp.sso_enforced). |

#### `verity.identity.second_factor_on_sign_in` Sign ins to Verity used a second factor

| | |
|---|---|
| Capability | verity_identity (new) |
| Resource | session |
| Population | Sign ins to Verity by active members in the last 90 days. |
| Predicate | Each SSO sign in carries an authentication method or level claim that shows a second factor at the provider, and each password sign in used TOTP; Admin MFA is required in workspace settings. |
| Empty population | Insufficient information when nobody signed in. |
| Results | Pass, fail as above. Insufficient: unverified whether Keycloak passes the upstream provider's method claims through brokering; if the claim is absent the result is insufficient, never pass. |
| Frequency | daily |
| Evidence kept | Sign in list with method, amr and acr values. |
| Controls | IAM-03 (partial: an independent sample of the provider's MFA on real sign ins for one application). |

#### `verity.identity.leavers_removed_by_sync` Leavers at the identity provider lose Verity access

| | |
|---|---|
| Capability | verity_identity (new) |
| Resource | member |
| Population | Members linked to a Keycloak user, in a workspace with directory sync on, and the sync runs in the period. |
| Predicate | The sync ran at least every two hours, with no failed run left unresolved for more than 24 hours; every member removed or disabled in the organization was disabled in Verity at the next run and their sessions were revoked. |
| Empty population | Not applicable when sync is off; manual disablements are listed from the audit log instead. |
| Results | Pass, fail as above. Error: Keycloak unreachable for a run. |
| Frequency | hourly with the sync |
| Evidence kept | Sync runs with time and outcome, members disabled with source time and Verity time, sessions revoked. |
| Controls | IAM-12 (partial: removal reached one application a leaver held), IAM-11 (partial: disabling ends sessions in Verity). |

#### `verity.identity.roles_from_groups` Verity roles come from identity provider groups

| | |
|---|---|
| Capability | verity_identity (new) |
| Resource | role_assignment |
| Population | Role assignments of active members. |
| Predicate | Where group mapping is on, every role of an SSO member comes from a mapped group; direct assignments are listed with who made them; every Admin is named, active and signs in with a second factor. |
| Empty population | Fail: a workspace always has at least one Admin, so an empty list is an error in collection. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Assignments with role, source (group or direct), assigned by, Admin list. |
| Controls | IAM-08 (partial: Verity as one system), IAM-07 (partial: Verity admins are privileged accounts of one system). |

#### `verity.identity.sign_in_settings` Verity's own sign in settings meet the standard

| | |
|---|---|
| Capability | verity_identity (new) |
| Resource | workspace |
| Population | The workspace's password, lockout and session settings. |
| Predicate | Where password sign in is allowed: minimum length at least 12, lockout after 1 to 10 failures for at least 30 minutes; idle timeout set and no longer than the session standard's limit (a parameter). |
| Empty population | Not applicable. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Settings snapshot. |
| Controls | IAM-06 (partial), IAM-11 (partial): Verity only. |

#### `verity.vendors.assurance_reviewed` Hosting providers' assurance reports were reviewed

| | |
|---|---|
| Capability | verity_vendors |
| Resource | vendor |
| Population | Active vendors linked to PE-01 (the hosting providers relied on for physical security). |
| Predicate | Each has a SOC report review or certificate whose period ended within the last 12 months, or a bridge letter covering the gap; a named reviewer and review date within 12 months; complementary user entity controls marked reviewed; and material findings linked to a risk or task. |
| Empty population | Fail when PE-01 is in scope: a hosting provider must be linked. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Report kind, type, period, opinion, reviewer, reviewed at, CUEC notes. |
| Controls | PE-01 (partial: the review is recorded and current; mapping each customer control to a company control is a person's work). |

#### `verity.vendors.breach_terms_recorded` Vendor contracts state breach notice hours

| | |
|---|---|
| Capability | verity_vendors |
| Resource | vendor |
| Population | Active vendors marked as holding personal data, with an active contract of type dpa or master. |
| Predicate | Each active such contract records breach notification hours no greater than the policy's maximum (a parameter) and has the contract file attached. |
| Empty population | Not applicable when no vendor holds personal data; listed as such. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Vendor, contract, breach hours, file reference. |
| Controls | DM-17 (partial), DM-10 (partial, the breach term of DM-10.C). |

#### `verity.vendors.personal_data_recorded` Vendors that receive personal data are fully recorded

| | |
|---|---|
| Capability | verity_vendors |
| Resource | vendor |
| Population | Active vendors marked as holding personal data. |
| Predicate | Each has the data types in scope, the data location, the systems in scope and the services provided filled, and an approval recorded before its first engagement started. |
| Empty population | Not applicable when none is marked; a person confirms against the data map. |
| Results | Pass, fail as above. Lawful basis is not a field, so the check never claims it. |
| Frequency | daily |
| Evidence kept | Vendor register rows with the fields above and the approval date. |
| Controls | DM-09 (partial), DM-06 (partial, vendor flows). |

#### `verity.assets.data_stores_mapped` Data stores carry what the data map needs

| | |
|---|---|
| Capability | verity_assets |
| Resource | asset |
| Population | Assets in service of type data, and cloud assets marked as holding data. |
| Predicate | Each has a classification, a primary owner who is an active member, a location, an environment, a regulated data type where it holds personal data, at least one relationship showing where its data comes from or goes, and the retention and encryption custom fields filled. |
| Empty population | Fail: a company in scope always has at least one data store. |
| Results | Pass, fail as above. |
| Frequency | daily |
| Evidence kept | Data asset rows with the fields above and their relationships. |
| Controls | DM-06 (partial: the map is complete in its own terms; completeness against reality needs assets.resources_registered). |


## NEED entries by capability

Plain predicates for the reconciliation step to match to connector keys. Where an existing key fits, the
JSON uses the key instead. Feasibility per provider is for the connector documents; predicates marked
unverified in the JSON may not be readable from every provider.

**business_applications** (7)

- NEED business_applications: Business applications that hold personal data are listed (DM-05, DM-06, DM-09, DM-11, DM-12, DM-15, DM-16)
- NEED business_applications: Chat and file sharing tools restrict external sharing as the rules set (DM-19)
- NEED business_applications: Consent records from the consent tool carry person or ID, time, purpose, notice version and capture method (DM-03)
- NEED business_applications: Finance and payment system roles are listed per user (IAM-13)
- NEED business_applications: Support tickets tagged as privacy inquiries carry received and resolved times (DM-14)
- NEED business_applications: Support tickets tagged as privacy requests carry received and answered times (DM-05, DM-11, DM-16)
- NEED business_applications: Withdrawals in the consent tool are listed with the time processing stopped (DM-03)

**ci_cd** (2)

- NEED ci_cd: Pipeline secrets, deploy keys and tokens are listed with created date and last rotation (IAM-10)
- NEED ci_cd: Running container images were rebuilt from a current base image within the set interval (NS-13)

**cloud_infrastructure** (28)

- NEED cloud_infrastructure: A change that opens a management port to a public range raises an alert (NS-08)
- NEED cloud_infrastructure: A reachability analysis between zones finds no path that the diagram forbids (NS-07)
- NEED cloud_infrastructure: Backups age out within the backup retention window, and no backup older than it exists (DM-16)
- NEED cloud_infrastructure: Cloud users, roles and access keys are listed with the extraction time, including those of outside parties (IAM-02, IAM-10, IAM-12)
- NEED cloud_infrastructure: Configuration rule findings are listed with first seen and resolved times, and each open past the response time is flagged (NS-04, NS-05, NS-08)
- NEED cloud_infrastructure: Console role maximum session lengths are within the standard (IAM-11)
- NEED cloud_infrastructure: Data stores in non production accounts carry a masking or synthetic tag (DM-13)
- NEED cloud_infrastructure: Database parameters refuse unencrypted connections, and load balancers reach targets over TLS (NS-02)
- NEED cloud_infrastructure: Disabled keys and keys pending deletion are listed with the stores and backups still using them (NS-06)
- NEED cloud_infrastructure: Disabling the detection service, or an account without it, raises an alert (NS-05)
- NEED cloud_infrastructure: Each data store records the key type used, customer managed or provider managed (NS-01)
- NEED cloud_infrastructure: Each finding of the severity the procedure names is linked to an incident record (NS-05)
- NEED cloud_infrastructure: Each instance and managed service uses the provider's or a named time source (NS-12)
- NEED cloud_infrastructure: Each managed instance reports patch compliance from the cloud's patch manager, within the timeframe for its severity (NS-13)
- NEED cloud_infrastructure: Each public origin accepts traffic only from the edge provider's ranges (NS-10)
- NEED cloud_infrastructure: Each secret in the store has a last rotated date within the interval and an owner tag; values are never read (NS-09)
- NEED cloud_infrastructure: Every allow rule carries an owner and purpose in a tag or description (NS-03)
- NEED cloud_infrastructure: Every cloud permission marked for removal in a review is gone at the next listing (IAM-02, IAM-07)
- NEED cloud_infrastructure: Key policies give administration and use to different roles, and no principal holds both (NS-06)
- NEED cloud_infrastructure: Lifecycle and expiry rules ran in the period, with deletion counts per store (DM-08, DM-16)
- NEED cloud_infrastructure: No allow rule points at a retired service (NS-03)
- NEED cloud_infrastructure: No production snapshot or database copy was restored into, or shared with, a non production account in the period (DM-13)
- NEED cloud_infrastructure: Outbound rules for workloads tagged high value allow only named destinations (NS-03)
- NEED cloud_infrastructure: Root and break glass sign ins and privileged role assumptions are listed from the audit log, each with the alert it raised (IAM-07)
- NEED cloud_infrastructure: Storage buckets block public access at account level (DM-19)
- NEED cloud_infrastructure: Suppression rules in the threat detection service are listed with a reason and author (NS-05)
- NEED cloud_infrastructure: Temporary roles for auditors and testers expired at the agreed time (IAM-01)
- NEED cloud_infrastructure: Threat detection findings are listed with severity, status, first seen and closed time, and who closed them (NS-05)

**device_management** (14)

- NEED device_management: Browser and installed application versions are within the patch timeframe (EP-03, EP-04)
- NEED device_management: Devices out of the baseline are listed with the date found and fixed (EP-03)
- NEED device_management: Devices out of the screen lock setting are listed with the date found and fixed (EP-06)
- NEED device_management: Devices removed from device management in the period are listed (EP-08)
- NEED device_management: Each device is assigned to a person, for comparison with the staff roster (EP-03)
- NEED device_management: Each device was enrolled before its first assignment to a person (EP-03)
- NEED device_management: Each wipe command shows a confirmed completion time per device (EP-05)
- NEED device_management: Encryption was on before a device's first assignment, and the compliance history shows unencrypted devices were fixed (EP-02)
- NEED device_management: Enrolment date precedes the joiner's start date (EP-03)
- NEED device_management: Every company device without full disk encryption is named in an exception in force (EP-02)
- NEED device_management: Every device removed from device management in the period has a disposal or reissue record (EP-08)
- NEED device_management: Every encrypted device has its recovery key held in device management (EP-02)
- NEED device_management: Installed software outside the permitted list is reported per device (EP-03)
- NEED device_management: Removable storage is blocked or limited to encrypted media by a device profile (DM-19)

**endpoint_protection** (4)

- NEED endpoint_protection: Detections are listed with device, severity, assignee, status and closed time, and none of high severity stays open past the response time (EP-01)
- NEED endpoint_protection: Each high severity detection is linked to an incident record (EP-01)
- NEED endpoint_protection: Every server asset in the inventory runs a healthy agent (EP-01)
- NEED endpoint_protection: Web protection is on in the endpoint agent (EP-07)

**hr_system** (1)

- NEED hr_system: Joiners, movers and leavers are listed with effective dates (IAM-01, IAM-05, IAM-12, EP-03, EP-05, PE-02, NS-11)

**identity_provider** (18)

- NEED identity_provider: A new or moved user's groups equal the groups their role defines (IAM-08)
- NEED identity_provider: Accounts and groups created for auditors and testers carry an end date and were disabled by it (IAM-01)
- NEED identity_provider: Accounts not linked to one named person (shared or generic) are listed (IAM-01)
- NEED identity_provider: Accounts with no sign in for the set number of days are listed (IAM-12)
- NEED identity_provider: After an account is disabled, its sign in log shows no session or token use (IAM-11)
- NEED identity_provider: Disabling a user revokes their sessions and refresh tokens (IAM-11)
- NEED identity_provider: Each disabled account has a disable time from the audit log (IAM-12)
- NEED identity_provider: Every account or group membership marked for removal in a review is absent from the next account export, with the date it went (IAM-02, IAM-07)
- NEED identity_provider: Every administrator has a phishing resistant factor enrolled and required (IAM-03)
- NEED identity_provider: Every group or application assignment in the period has an assignment time and actor from the audit log, so it can be matched to its request (IAM-01, IAM-08)
- NEED identity_provider: External sharing in the mail and file suite is limited as the rules set, public links are off or expire, and leak prevention rules are on (DM-19)
- NEED identity_provider: Files and mail in the productivity suite carry a sensitivity label where the policy requires marking (DM-04)
- NEED identity_provider: Groups that grant access to systems holding personal data contain only the roles the purpose register allows (DM-12)
- NEED identity_provider: Leak prevention and sharing alerts in the mail and file suite are listed with severity, status and triage time (DM-19)
- NEED identity_provider: Privileged role activations and administrator role grants are listed from the audit log with actor and time (IAM-07)
- NEED identity_provider: Sensitive admin actions require a fresh sign in (IAM-11)
- NEED identity_provider: Service principals and tokens with no use in 90 days are disabled (IAM-10)
- NEED identity_provider: Service principals, API tokens and service accounts are listed with owner, created date, last use and credential expiry (IAM-10)

**network_edge** (8)

- NEED network_edge: Access policies grant per application or per system, not to whole networks (NS-08, NS-11)
- NEED network_edge: Administrative SSH and RDP are reachable only through the zero trust or VPN tool (NS-08)
- NEED network_edge: Each public hostname sends HSTS, and its certificate renews automatically and has more than 14 days left (NS-02)
- NEED network_edge: Every managed device runs the secure web gateway client, including newly enrolled ones (EP-07)
- NEED network_edge: Managed rule sets are in block mode, not log only, for each public hostname (NS-10)
- NEED network_edge: Remote access members match current staff and approved contractors, and leavers were removed (NS-08, NS-11)
- NEED network_edge: Remote session logs are retained and exported (NS-08, NS-11)
- NEED network_edge: Secure web gateway policies block the named categories, and every enrolled device runs the gateway client (EP-07)

**observability** (2)

- NEED observability: Each monitored host reports a clock offset within the allowed limit, and offsets beyond it raised an alert (NS-12)
- NEED observability: Log timestamps from every source are stored in UTC or carry an offset (NS-12)

**password_manager** (5)

- NEED password_manager: Access to break glass vault items is listed with who and when (IAM-07)
- NEED password_manager: No member who left still has an active account, and leavers were suspended within the removal time (IAM-05)
- NEED password_manager: Password manager administrators are listed (IAM-01, IAM-03, IAM-07, IAM-10)
- NEED password_manager: Shared vaults are listed with an owner and member groups, and none is shared with everyone (IAM-05)
- NEED password_manager: The password manager requires a second factor for every member (IAM-03)

**ticketing** (1)

- NEED ticketing: Every leaver has an offboarding ticket closed with each system checked (IAM-05, IAM-12, EP-05)

**version_control** (8)

- NEED version_control: Code host members, outside collaborators and team permissions are listed with the extraction time (IAM-02, IAM-10, IAM-12)
- NEED version_control: Code host owners and repository administrators are listed (IAM-01, IAM-03, IAM-07, IAM-10)
- NEED version_control: Code host teams, members and repository roles are listed with the extraction time (IAM-08, IAM-09)
- NEED version_control: Deploy keys and installed apps with their permissions are listed (IAM-10)
- NEED version_control: Each leaver was removed from the code host organisation (IAM-12)
- NEED version_control: Pull requests that add personal data fields carry a privacy review label or link (DM-07)
- NEED version_control: Secret scanning alerts are listed with created and resolved times and the resolution, and none stays open past the response time (NS-09)
- NEED version_control: The repositories holding infrastructure code are identified, and every change to them merged in the period was reviewed by someone other than its author (NS-04)

**vulnerability_scanner** (1)

- NEED vulnerability_scanner: An external scan of the public address ranges finds no management port open (NS-08)


## Control by control

### IAM-01 Access provisioning approval

SOC 2: CC6.2 (full), CC6.3 (partial). ISO 27001:2022: A.5.15 (partial), A.5.16 (partial), A.5.18 (partial), A.8.34 (partial). Decision: revise objectives.

The request and approval record is the heart of this control. Jira plus the identity provider can join each grant to its approval (P2); a small company that uses Verity tasks for requests gets the approval half now. The grant time always comes from the system that granted it.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-request-and-approval-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `approved-requests-for-a-sample-of` | B, C, D, E, F | `tickets.access_requests_approved`; NEED identity_provider: Every group or application assignment in the period has an assignment time and actor from the audit log, so it can be matched to its request | Tasks: Access request tasks with approval + `verity.tasks.approved_before_done` NEW | export from the request tool for the period | P2 |
| `completed-checklists-for-a-sample-of` | B | `people.joiners_onboarded` | Tasks: Joiner checklist tasks from the joiner template | HR export of joiners | P3 |
| `roster-of-joiners-and-leavers-with` | B | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `list-of-privileged-accounts-with-approval` | D | `idp.admins_limited`; `cloud.least_privilege`; NEED version_control: Code host owners and repository administrators are listed; NEED password_manager: Password manager administrators are listed | IAM: Verity Admin role holders + `verity.identity.roles_from_groups` NEW | approval and need for each privileged account | P2 |
| `completed-access-reviews-with-reviewer-sign` | E | `idp.access_list_exported`; NEED identity_provider: Accounts not linked to one named person (shared or generic) are listed | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | reviewer's account by account decisions and sign off | P1 |
| `removal-records-for-a-sample-of` | F | NEED identity_provider: Accounts and groups created for auditors and testers carry an end date and were disabled by it; NEED cloud_infrastructure: Temporary roles for auditors and testers expired at the agreed time | none | record of what access the test needed | P2 |

No system can prove: that the business reason was sound and that the approver had the authority to approve (interview, IAM-01.A and E).

### IAM-02 Periodic user access reviews

SOC 2: CC6.2 (partial), CC6.3 (partial). ISO 27001:2022: A.5.18 (partial), A.8.4 (partial). Decision: revise objectives.

The identity provider freezes the account list (P2). The review itself is a person's decision per account; Verity can prove it happened on time and was signed by someone other than the reviewed, until the access review module (Phase 3.2) holds the decisions.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-review-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `account-list-export` | B | `idp.access_list_exported`; NEED cloud_infrastructure: Cloud users, roles and access keys are listed with the extraction time, including those of outside parties; NEED version_control: Code host members, outside collaborators and team permissions are listed with the extraction time | IAM: Verity members report: member, status, roles and their source, groups, last sign in, sign in method, second factor | exports from systems no connector reads, with the steps used | P2 |
| `completed-access-reviews-with-reviewer-sign` | C, D | `idp.access_list_exported` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | reviewer's account by account decisions and sign off | P1 |
| `asset-inventory` | C | `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned`; Assets: Assets in compliance scope | none | P1 |
| `access-changes-made-as-a-result` | E | `tickets.remediation_tracked`; NEED identity_provider: Every account or group membership marked for removal in a review is absent from the next account export, with the date it went; NEED cloud_infrastructure: Every cloud permission marked for removal in a review is gone at the next listing | Tasks: Removal tasks raised from the review + `verity.tasks.remediation_in_sla` | reviewer confirms removals against the source | P2 |
| `log-of-control-deficiencies-with-owner` | E | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |

No system can prove: that each reviewer actually looked at each account (IAM-02.D, interview).

### IAM-03 Enforce multi-factor authentication

SOC 2: CC6.1 (partial). ISO 27001:2022: A.8.5 (partial). Decision: revise objectives.

The identity provider proves enforcement and enrolment (P2). GitHub's two factor check already runs and lands on the new IAM-03.F. Verity's own sign ins are a small independent sample of the provider's MFA working on real sign ins.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-policy-requiring-multi-factor-authentication` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `second-factor-enforcement-and-enrolled-users` | B, C, D, E, F | `idp.mfa_enforced`; `cloud.root_account_mfa`; `vcs.org_two_factor_required`; NEED identity_provider: Every administrator has a phishing resistant factor enrolled and required; NEED password_manager: The password manager requires a second factor for every member | IAM: Sign ins to Verity + `verity.identity.second_factor_on_sign_in` NEW | none | P2 |
| `list-of-privileged-accounts-with-approval` | C | `idp.admins_limited`; `cloud.least_privilege`; NEED version_control: Code host owners and repository administrators are listed; NEED password_manager: Password manager administrators are listed; `cloud.root_account_mfa` | IAM: Verity Admin role holders + `verity.identity.roles_from_groups` NEW | approval and need for each privileged account | P2 |
| `approved-exceptions-to-multi-factor-authentication` | D | `idp.mfa_enforced` | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |
| `log-of-control-deficiencies-with-owner` | E | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |
| `applications-inside-and-outside-single-sign-on` | F | `vcs.org_two_factor_required`; `cloud.root_account_mfa`; NEED password_manager: The password manager requires a second factor for every member | none | for each application outside single sign on, how it requires a second factor | P2 |

No system can prove: that an exception's safeguard really works (IAM-03.D).

### IAM-04 Enforce single sign-on

SOC 2: CC6.1 (partial). ISO 27001:2022: A.8.5 (partial). Decision: revise objectives.

The identity provider lists apps behind it (P2). Apps outside it are known only from the vendor register and a person's list, so completeness is a comparison, not a check. Verity is itself one app behind SSO and can prove it.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-cloud-services-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cloud-services-security-policy` | P1 |
| `applications-inside-and-outside-single-sign-on` | B, C, D | `idp.sso_enforced`; `idp.connected_apps_known` | Vendors: Vendor register report (systems in scope) and discovered apps; IAM: Verity's own SSO setting + `verity.identity.sso_required` NEW | IT lead's list of applications outside single sign on and how each signs in | P2 |
| `vendor-inventory-with-owner-data-and` | B | `idp.connected_apps_known` | Vendors: Vendor register report + `verity.vendors.owner_and_tier` | none | P1 |
| `approved-exceptions-for-applications-outside-single` | C | `idp.sso_enforced` | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |

No system can prove: that the list of applications outside single sign on is complete (IAM-04.B relies on a person's list and the vendor register).

### IAM-05 Company password manager

SOC 2: CC6.1 (partial). ISO 27001:2022: A.5.17 (partial). Decision: keep.

1Password (P2) proves who has a vault account. Leavers need an HR source to compare with, and vault scoping is a judgement on top of the export.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `policy-requiring-a-password-manager-for` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy`; template `acceptable-use-policy` | P1 |
| `doc-acceptable-use-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `acceptable-use-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `password-manager-members-against-staff-list` | B, C, D | `vault.everyone_enrolled`; NEED password_manager: No member who left still has an active account, and leavers were suspended within the removal time; NEED password_manager: Shared vaults are listed with an owner and member groups, and none is shared with everyone | none | staff list from HR | P2 |
| `roster-of-joiners-and-leavers-with` | B | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates; `vault.everyone_enrolled` | none | HR or payroll export | P3 |
| `completed-offboarding-records-for-leavers-in` | D | `people.leavers_deprovisioned`; NEED ticketing: Every leaver has an offboarding ticket closed with each system checked | Tasks: Leaver checklist tasks from the leaver template | closed checklist for each leaver | P3 |

No system can prove: that vaults are scoped sensibly by team (IAM-05.C, interview).

### IAM-06 Password policy

SOC 2: CC6.1 (partial). ISO 27001:2022: A.5.17 (partial), A.8.5 (partial). Decision: revise objectives.

The identity provider settings prove the policy is configured (P2). Rotation only when justified is a reading of policy against settings.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `password-policy` | A, B, D | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `identity-provider-password-settings` | B, C, D, E | `idp.password_policy` (full) | IAM: Verity's own password settings + `verity.identity.sign_in_settings` NEW | none | P2 |

No system can prove: that a scheduled password change traces to a real contract or rule (IAM-06.D, interview).

### IAM-07 Privileged access management

SOC 2: CC6.3 (partial). ISO 27001:2022: A.8.18 (partial), A.8.2 (full). Decision: revise objectives.

The identity provider and cloud list privileged accounts and their use (P2). Need, approval and the review verdict stay with people; Verity proves the review cadence.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-review-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `list-of-privileged-accounts-with-approval` | B | `idp.admins_limited`; `cloud.least_privilege`; NEED version_control: Code host owners and repository administrators are listed; NEED password_manager: Password manager administrators are listed | IAM: Verity Admin role holders + `verity.identity.roles_from_groups` NEW | approval and need for each privileged account | P2 |
| `privileged-elevation-and-break-glass-log` | B, F | NEED cloud_infrastructure: Root and break glass sign ins and privileged role assumptions are listed from the audit log, each with the alert it raised; NEED identity_provider: Privileged role activations and administrator role grants are listed from the audit log with actor and time; NEED password_manager: Access to break glass vault items is listed with who and when | Audit log: Verity audit log of Admin actions | after the fact review of each use | P2 |
| `review-of-privileged-access` | C, D, E, F | `idp.admins_limited` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |
| `completed-access-reviews-with-reviewer-sign` | C, D | `idp.access_list_exported` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | reviewer's account by account decisions and sign off | P1 |
| `asset-inventory` | D | `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned`; Assets: Assets in compliance scope | none | P1 |
| `access-changes-made-as-a-result` | E | `tickets.remediation_tracked`; NEED identity_provider: Every account or group membership marked for removal in a review is absent from the next account export, with the date it went; NEED cloud_infrastructure: Every cloud permission marked for removal in a review is gone at the next listing | Tasks: Removal tasks raised from the review + `verity.tasks.remediation_in_sla` | reviewer confirms removals against the source | P2 |
| `log-of-control-deficiencies-with-owner` | E | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |

No system can prove: that each privileged account is needed (IAM-07.B judgement) and that a review was meaningful.

### IAM-08 Role-based access and least privilege

SOC 2: CC5.2 (partial), CC6.1 (partial), CC6.3 (partial). ISO 27001:2022: A.5.15 (partial), A.8.3 (partial), A.8.4 (partial). Decision: keep.

Group based access is checkable in the identity provider and code host (P2). Whether the matrix is least privilege is a judgement; owner approvals fit the Documents approval tiers now.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `role-and-access-matrix` | A, B, D | `idp.groups_drive_access` | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `role-definitions-approved-by-their-owners` | A, D | none | Documents: Approval record of the role matrix document + `verity.documents.controlled` | template `access-control-policy` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `group-and-role-membership-export` | B, C | `idp.groups_drive_access`; `idp.access_list_exported`; `cloud.least_privilege`; NEED version_control: Code host teams, members and repository roles are listed with the extraction time | IAM: Verity roles and their source + `verity.identity.roles_from_groups` NEW | none | P2 |
| `approved-requests-for-a-sample-of` | C | `tickets.access_requests_approved`; NEED identity_provider: Every group or application assignment in the period has an assignment time and actor from the audit log, so it can be matched to its request; NEED identity_provider: A new or moved user's groups equal the groups their role defines | Tasks: Access request tasks with approval + `verity.tasks.approved_before_done` NEW | export from the request tool for the period | P2 |

No system can prove: that a role is truly least privilege for the job (IAM-08.A, D).

### IAM-09 Segregation of duties

SOC 2: CC5.1 (partial), CC6.3 (partial). ISO 27001:2022: A.5.3 (partial). Decision: split.

After the split this covers technology duties. GitHub already proves nobody approves their own change. Other pairs need the conflicts review.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `matrix-of-conflicting-duties` | A, D | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy`; the matrix sheet, approved by the security lead | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `review-of-people-who-hold-conflicting` | B, C, D | `vcs.merged_changes_reviewed`; `idp.access_list_exported` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | reviewer's comparison of the matrix with current access | P1 |
| `group-and-role-membership-export` | B | `idp.groups_drive_access`; `idp.access_list_exported`; `cloud.least_privilege`; NEED version_control: Code host teams, members and repository roles are listed with the extraction time | IAM: Verity roles and their source + `verity.identity.roles_from_groups` NEW | none | P2 |

No system can prove: that a compensating review was independent and done with care (IAM-09.C, interview).

### IAM-10 Service and machine account governance

SOC 2: CC6.1 (partial), CC6.3 (partial). ISO 27001:2022: A.5.16 (partial), A.8.3 (partial). Decision: keep.

Cloud, identity provider, CI and code host can each list machine identities with age and last use (P2). Owner and purpose are often missing in the source; a person adds them.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-cloud-services-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cloud-services-security-policy` | P1 |
| `inventory-of-service-accounts-and-keys` | B, C, D | `cloud.machine_credentials_rotated`; `cloud.least_privilege`; NEED identity_provider: Service principals, API tokens and service accounts are listed with owner, created date, last use and credential expiry; NEED ci_cd: Pipeline secrets, deploy keys and tokens are listed with created date and last rotation; NEED version_control: Deploy keys and installed apps with their permissions are listed | none | owner and purpose where no source records them | P2 |
| `account-list-export` | B | `idp.access_list_exported`; NEED cloud_infrastructure: Cloud users, roles and access keys are listed with the extraction time, including those of outside parties; NEED version_control: Code host members, outside collaborators and team permissions are listed with the extraction time | IAM: Verity members report: member, status, roles and their source, groups, last sign in, sign in method, second factor | exports from systems no connector reads, with the steps used | P2 |
| `list-of-privileged-accounts-with-approval` | C | `idp.admins_limited`; `cloud.least_privilege`; NEED version_control: Code host owners and repository administrators are listed; NEED password_manager: Password manager administrators are listed | IAM: Verity Admin role holders + `verity.identity.roles_from_groups` NEW | approval and need for each privileged account | P2 |
| `records-of-rotation-or-review` | D, E | `cloud.machine_credentials_rotated`; NEED identity_provider: Service principals and tokens with no use in 90 days are disabled | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P2 |

No system can prove: that each machine identity's stated purpose is true (IAM-10.C).

### IAM-11 Session timeout and management

SOC 2: CC6.1 (partial). ISO 27001:2022: A.8.5 (partial). Decision: keep.

The identity provider and cloud console sessions are settings (P2). The product's own session setting is a person's export.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `session-timeout-standard` | A, B | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `session-limit-settings-export` | B, C, D | `idp.session_timeout`; NEED cloud_infrastructure: Console role maximum session lengths are within the standard; NEED identity_provider: Sensitive admin actions require a fresh sign in; NEED identity_provider: Disabling a user revokes their sessions and refresh tokens | IAM: Verity's own session settings + `verity.identity.sign_in_settings` NEW | the product's session setting | P2 |
| `removal-records-for-a-sample-of` | D | NEED identity_provider: After an account is disabled, its sign in log shows no session or token use | IAM: Directory sync results + `verity.identity.leavers_removed_by_sync` NEW | none | P2 |

No system can prove: that the step up applies to every high risk action in the product (IAM-11.C, interview).

### IAM-12 Timely access removal

SOC 2: CC6.2 (partial), CC6.3 (partial). ISO 27001:2022: A.5.16 (partial), A.5.18 (partial). Decision: revise objectives.

Removal times come from the identity provider, but who left and when comes from HR, which is not signed, so the population stays P3 until an HR connector or a roster import exists. Verity's directory sync proves removal reached one application.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-removal-procedure-with-the-timeframe` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `joiner-mover-leaver-checklists` | P1 |
| `doc-access-control-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `doc-joiner-mover-leaver-checklists` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `joiner-mover-leaver-checklists` | P1 |
| `removal-records-for-a-sample-of` | B, C, D | `people.leavers_deprovisioned`; NEED identity_provider: Each disabled account has a disable time from the audit log; NEED version_control: Each leaver was removed from the code host organisation | IAM: Directory sync results + `verity.identity.leavers_removed_by_sync` NEW | HR export of leavers with last working days | P3 |
| `roster-of-joiners-and-leavers-with` | B, E | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `completed-offboarding-records-for-leavers-in` | D | `people.leavers_deprovisioned`; NEED ticketing: Every leaver has an offboarding ticket closed with each system checked | Tasks: Leaver checklist tasks from the leaver template | closed checklist for each leaver | P3 |
| `applications-inside-and-outside-single-sign-on` | D | `idp.sso_enforced`; `idp.connected_apps_known` | Vendors: Vendor register report (systems in scope) and discovered apps; IAM: Verity's own SSO setting + `verity.identity.sso_required` NEW | IT lead's list of applications outside single sign on and how each signs in | P2 |
| `account-list-export` | E | `idp.access_list_exported`; NEED cloud_infrastructure: Cloud users, roles and access keys are listed with the extraction time, including those of outside parties; NEED version_control: Code host members, outside collaborators and team permissions are listed with the extraction time; NEED identity_provider: Accounts with no sign in for the set number of days are listed | IAM: Verity members report: member, status, roles and their source, groups, last sign in, sign in method, second factor | exports from systems no connector reads, with the steps used | P2 |

No system can prove: access held outside every connected system (local accounts, shared credentials) is removed (IAM-12.D, interview).

### IAM-13 Segregation of duties in finance and payment processes (proposed)

SOC 2: CC5.1 (partial). ISO 27001:2022: A.5.3 (partial). Successor, see Proposed control changes.

Finance and payment systems are in no catalogue, so this successor stays on people and the review cadence.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `matrix-of-conflicting-duties` | A, D | none | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy`; the finance matrix sheet, approved by the finance lead | P1 |
| `review-of-people-who-hold-conflicting` | B, C, D | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | reviewer's comparison of the finance matrix with finance system roles | P1 |
| `group-and-role-membership-export` | B | NEED business_applications: Finance and payment system roles are listed per user | none | export from the finance and payment systems | P3 |

No system can prove: the finance roles, the matrix or the safeguards, which are all people's records.

### IAM-14 Product sign in protections for customer users (proposed)

SOC 2: CC6.1 (partial). ISO 27001:2022: A.5.17 (partial), A.8.5 (partial). Decision: add.

The product's own sign in is outside every connector. It rests on the standard, an engineering export and the pen test.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-engineering-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `engineering-security-standard` | P1 |
| `product-sign-in-settings (proposed)` | B, C | none | none | export of the product's authentication settings and hashing configuration | people-only |
| `penetration-test-report-from-an-independent` | D | none | Vulnerabilities: Findings imported from the report + `verity.vulns.within_sla` | report from the outside tester | people-only |
| `log-of-control-deficiencies-with-owner` | D | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |

No system can prove: how the product stores passwords (IAM-14.C), short of reading the code.

### EP-01 Endpoint EDR / anti-malware

SOC 2: CC6.8 (full). ISO 27001:2022: A.8.1 (partial), A.8.16 (partial), A.8.7 (partial). Decision: keep.

Everything automatable here needs an endpoint protection connector, which is not in the signed catalogue (P3).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `endpoint-protection-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `inventory-of-company-devices` | B | `endpoint.protection_active` (full); `devices.enrolled` | none | none | P3 |
| `asset-inventory` | B | `assets.resources_registered`; NEED endpoint_protection: Every server asset in the inventory runs a healthy agent | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P3 |
| `alerts-that-were-reviewed-and-acted` | C, D | NEED endpoint_protection: Detections are listed with device, severity, assignee, status and closed time, and none of high severity stays open past the response time | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | review notes for detections | P3 |
| `security-incident-register` | D | NEED endpoint_protection: Each high severity detection is linked to an incident record | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P1 |

No system can prove: that a reviewer's decision on an alert was right (EP-01.C).

### EP-02 Endpoint full-disk encryption

SOC 2: CC6.1 (partial), CC6.5 (partial), CC6.7 (partial). ISO 27001:2022: A.7.10 (partial), A.7.9 (partial), A.8.1 (partial), A.8.24 (partial). Decision: keep.

Device management proves encryption and key escrow (P3). Exceptions live in the risk register now.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `endpoint-encryption-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-cryptography-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cryptography-policy` | P1 |
| `inventory-of-company-devices` | B, C, D | `devices.disk_encrypted` (full); NEED device_management: Every encrypted device has its recovery key held in device management; NEED device_management: Encryption was on before a device's first assignment, and the compliance history shows unencrypted devices were fixed | none | none | P3 |
| `approved-exceptions` | D | NEED device_management: Every company device without full disk encryption is named in an exception in force | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |

No system can prove: that an exception's safeguard is real (EP-02.D).

### EP-03 Device management (MDM) enrollment

SOC 2: CC6.5 (partial), CC6.8 (partial). ISO 27001:2022: A.6.7 (partial), A.7.9 (partial), A.8.1 (partial), A.8.19 (partial). Decision: revise objectives.

Device management is the source for enrolment, assignment, baseline and software (P3). Reconciliation with the roster also needs HR.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `device-management-policy` | A, E | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-remote-working-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `remote-working-policy` | P1 |
| `inventory-of-company-devices` | B, C, D, E | `devices.enrolled` (full); NEED device_management: Each device was enrolled before its first assignment to a person; NEED device_management: Each device is assigned to a person, for comparison with the staff roster; NEED device_management: Installed software outside the permitted list is reported per device; NEED device_management: Devices out of the baseline are listed with the date found and fixed | none | none | P3 |
| `completed-checklists-for-a-sample-of` | B | `people.joiners_onboarded`; NEED device_management: Enrolment date precedes the joiner's start date | Tasks: Joiner checklist tasks from the joiner template | HR export of joiners | P3 |
| `roster-of-joiners-and-leavers-with` | C | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `patch-compliance-report` | D | `devices.os_current`; NEED device_management: Browser and installed application versions are within the patch timeframe | none | monthly report from the device tool | P3 |
| `screen-lock-setting-report` | D | `devices.screen_lock` (full) | none | none | P3 |

No system can prove: that the baseline itself is sensible.

### EP-04 Patch management

SOC 2: CC6.8 (partial), CC7.1 (partial). ISO 27001:2022: A.8.8 (partial). Decision: split.

After the split this is company devices only: device management (P3).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `patch-management-policy-with-timeframes` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy`; template `endpoint-security-standard` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `patch-compliance-report` | B, C, D | `devices.os_current`; NEED device_management: Browser and installed application versions are within the patch timeframe | none | monthly report from the device tool | P3 |
| `log-of-control-deficiencies-with-owner` | D | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |

No system can prove: that an exception for a device is justified.

### EP-05 Remote wipe on offboarding / loss

SOC 2: CC6.5 (partial). ISO 27001:2022: A.5.11 (partial), A.7.14 (partial), A.7.9 (partial), A.8.1 (partial). Decision: keep.

Wipe capability and wipe confirmation come from device management (P3). Credential rotation for a device that never reconnects is a person's record.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `procedure-for-lost-devices-and-offboarding` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard`; template `joiner-mover-leaver-checklists` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-asset-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `asset-management-policy` | P1 |
| `inventory-of-company-devices` | B | `devices.remote_wipe` (full) | none | none | P3 |
| `wipe-confirmations-for-recovered-or-lost` | C, D, E | NEED device_management: Each wipe command shows a confirmed completion time per device | Tasks: Lost device tasks | recycler reset certificate | P3 |
| `roster-of-joiners-and-leavers-with` | C | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `completed-offboarding-records-for-leavers-in` | C, E | `people.leavers_deprovisioned`; NEED ticketing: Every leaver has an offboarding ticket closed with each system checked | Tasks: Leaver checklist tasks from the leaver template | closed checklist for each leaver | P3 |

No system can prove: that credentials on a device that never reconnected were all rotated (EP-05.E, interview).

### EP-06 Screen lock policy

SOC 2: CC6.1 (partial). ISO 27001:2022: A.7.7 (partial), A.8.1 (partial). Decision: keep.

One device management setting (P3).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `screen-lock-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-endpoint-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `endpoint-security-standard` | P1 |
| `doc-acceptable-use-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `acceptable-use-policy` | P1 |
| `screen-lock-setting-report` | B, C, D | `devices.screen_lock` (full) | none | none | P3 |
| `inventory-of-company-devices` | B | `devices.enrolled` (full) | none | none | P3 |
| `log-of-control-deficiencies-with-owner` | D | `tickets.remediation_tracked`; NEED device_management: Devices out of the screen lock setting are listed with the date found and fixed | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | none | P1 |

No system can prove: nothing material once device management is connected; the standard's choice of timeout is a judgement.

### EP-07 Harmful website blocking

SOC 2: none. ISO 27001:2022: A.8.23 (partial). Decision: revise objectives.

Cloudflare Gateway, a signed Phase 2 provider, can show filter policies and client coverage; the device list to compare with still needs device management.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `web-filtering-standard-covering-blocked-categories` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `report-of-filter-coverage-and-blocked` | B, D, E | NEED network_edge: Secure web gateway policies block the named categories, and every enrolled device runs the gateway client; NEED endpoint_protection: Web protection is on in the endpoint agent | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW; Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P2 |
| `inventory-of-company-devices` | B | `devices.enrolled`; NEED network_edge: Every managed device runs the secure web gateway client, including newly enrolled ones | none | device management export or a sheet | P3 |
| `training-content-and-schedule` | E | none | Documents: Policy register + `verity.policies.reviewed` | template `competence-and-awareness-procedure`; course list or slide deck with the yearly plan | P1 |

No system can prove: that repeat hits led to sensible rule or training changes (EP-07.E).

### EP-08 Equipment and media wiping and disposal (proposed)

SOC 2: C1.2 (partial), CC6.5 (partial). ISO 27001:2022: A.7.10 (partial), A.7.14 (partial). Successor, see Proposed control changes.

Verity's decommissioned assets report fills most of this now; device management would show which devices left management.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `secure-disposal-procedure` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `asset-management-policy`; template `data-management-policy` | P1 |
| `doc-asset-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `asset-management-policy` | P1 |
| `disposal-records-or-certificates` | B, C | NEED device_management: Every device removed from device management in the period has a disposal or reissue record | Assets: Decommissioned assets report + `verity.assets.disposal_recorded` | disposal contractor certificates | P1 |
| `asset-inventory` | B | NEED device_management: Devices removed from device management in the period are listed | Assets: Decommissioned assets report + `verity.assets.disposal_recorded` | none | P1 |

No system can prove: that a wipe method fitted the data on the item, and the contractor's certificate is genuine (EP-08.C).

### PE-01 Cloud physical security (provider assurance review)

SOC 2: A1.2 (partial), CC6.4 (partial), CC9.2 (partial). ISO 27001:2022: A.5.23 (partial), A.7.1 (partial), A.7.11 (partial), A.7.12 (partial), A.7.13 (partial), A.7.14 (partial), A.7.2 (partial), A.7.3 (partial), A.7.4 (partial), A.7.5 (partial), A.7.6 (partial), A.7.8 (partial). Decision: keep.

Verity's vendors module already records SOC report reviews with period, complementary controls and reviewer, so this control is close to fully P1.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-cloud-services-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cloud-services-security-policy` | P1 |
| `cloud-provider-assurance-report-that-was` | B, C | none | Vendors: SOC report reviews of hosting providers linked to PE-01 + `verity.vendors.assurance_reviewed` NEW; Assets: Cloud assets with location | download of the report from the provider's compliance portal | P1 |
| `asset-inventory` | B | `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned`; Assets: Cloud assets with location | none | P1 |
| `review-of-the-carve-out-and` | C, D | none | Vendors: SOC report review: complementary user entity controls reviewed and notes + `verity.vendors.assurance_reviewed` NEW | mapping of each customer control to a company control | P1 |
| `doc-soc2-system-description` | E | none | Documents: Policy register + `verity.policies.reviewed` | template `soc2-system-description` | P1 |
| `statement-of-applicability-showing-every-decision` | E | none | Compliance: Statement of Applicability export (XLSX) + `verity.soa.complete` | none | P1 |

No system can prove: that the reviewer understood the exceptions in the report (PE-01.C, interview).

### PE-02 Office physical access controls

SOC 2: CC6.4 (partial). ISO 27001:2022: A.5.15 (partial), A.7.1 (partial), A.7.2 (partial), A.7.3 (partial), A.7.4 (partial), A.7.6 (partial), A.7.7 (partial). Decision: keep.

Office systems (badges, alarms, visitors) are in no catalogue. Verity proves cadence of reconciliations and walk throughs.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `physical-access-policy-for-offices` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `physical-security-policy` | P1 |
| `doc-physical-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `physical-security-policy` | P1 |
| `access-list-and-badge-records` | B | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | badge system export compared with the staff list | P1 |
| `roster-of-joiners-and-leavers-with` | B | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `visitor-log` | C | none | none | sign in book or visitor app export; observation | people-only |
| `alarm-or-camera-review-or-the` | D | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW; Onboarding: Company profile facts (office type) | alarm company reports, camera review note or the lease section on building security | P1 |
| `desk-and-secure-area-walk-through` | E | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | walk through checklist; observation | P1 |

No system can prove: that visitors were escorted (PE-02.C) and desks were clear (PE-02.E): observation only.

### PE-03 Environmental and equipment protection at own sites

SOC 2: none. ISO 27001:2022: A.7.11 (partial), A.7.12 (partial), A.7.13 (partial), A.7.5 (partial), A.7.8 (partial). Decision: keep.

Own site records are people's. Verity proves the yearly tests and inspections happened.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-site-and-equipment-protection-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `site-and-equipment-protection-standard` | P1 |
| `hazard-assessment-and-protections-for-each` | A, B | none | Documents: Policy register + `verity.policies.reviewed`; Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | template `site-and-equipment-protection-standard`; observation of the protections at each site | P1 |
| `service-and-fault-records-for-site` | C | none | none | service reports and fault records from the landlord or contractors | people-only |
| `power-alarm-and-suppression-test-results` | D | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | test reports from the landlord or contractors | P1 |
| `payment-device-list-and-tamper-inspections` | E | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW; Onboarding: Company profile facts (card data) | device list and inspection sheet | P1 |

No system can prove: that protections match the hazards (PE-03.B, observation) and that engineers were supervised (PE-03.C).

### NS-01 Encryption at rest

SOC 2: CC6.1 (partial). ISO 27001:2022: A.8.24 (partial). Decision: keep.

The AWS connector proves encryption per store (P2). Key type rules per contract are a comparison a person confirms.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `encryption-standard-stating-what-is-encrypted` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `cryptography-policy`; template `infrastructure-security-standard` | P1 |
| `doc-cryptography-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cryptography-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `data-store-encryption-settings` | B, C, D | `cloud.encryption_at_rest` (full); NEED cloud_infrastructure: Each data store records the key type used, customer managed or provider managed | none | none | P2 |
| `asset-inventory` | B | `assets.resources_registered`; `cloud.encryption_at_rest` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P2 |

No system can prove: that the key type matches what each contract demands (NS-01.C needs the contract).

### NS-02 Encryption in transit (TLS)

SOC 2: CC6.7 (partial). ISO 27001:2022: A.5.14 (partial), A.8.21 (partial), A.8.24 (partial). Decision: revise objectives.

Cloudflare and the cloud load balancers prove edge TLS (P2). Internal TLS needs the new settings artifact.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `encryption-in-transit-standard` | A, D | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `cryptography-policy` | P1 |
| `doc-cryptography-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cryptography-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `public-endpoint-tls-scan` | B, C, E | `edge.minimum_tls`; `cloud.tls_in_transit`; NEED network_edge: Each public hostname sends HSTS, and its certificate renews automatically and has more than 14 days left | Assets: Internet facing assets | TLS scan for endpoints no connector fronts | P2 |
| `asset-inventory` | B | `assets.resources_registered`; `edge.minimum_tls` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P1 |
| `internal-tls-enforcement-settings (proposed)` | D | NEED cloud_infrastructure: Database parameters refuse unencrypted connections, and load balancers reach targets over TLS | none | none | P2 |

No system can prove: that every internal path is covered, beyond the settings exported (NS-02.D interview).

### NS-03 Default-deny firewall rules

SOC 2: CC6.6 (full). ISO 27001:2022: A.8.20 (partial), A.8.23 (partial). Decision: revise objectives.

Cloud security group checks are strong here (P2). Owner and purpose per rule exist only if teams tag rules.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `firewall-rule-register-with-owner-and` | B, C, E | `cloud.default_deny_ingress`; `cloud.admin_ports_closed`; NEED cloud_infrastructure: Every allow rule carries an owner and purpose in a tag or description; NEED cloud_infrastructure: Outbound rules for workloads tagged high value allow only named destinations | none | owner and purpose for rules that carry none | P2 |
| `periodic-review-of-firewall-rules` | C, D | `cloud.default_deny_ingress` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |
| `asset-inventory` | D, E | `assets.resources_registered`; NEED cloud_infrastructure: Outbound rules for workloads tagged high value allow only named destinations; NEED cloud_infrastructure: No allow rule points at a retired service | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P1 |

No system can prove: that a justification for an open rule is good (NS-03.C).

### NS-04 Hardening baselines (CIS)

SOC 2: CC5.2 (partial), CC6.1 (partial), CC7.1 (partial). ISO 27001:2022: A.5.23 (partial), A.8.18 (partial), A.8.19 (partial), A.8.9 (partial). Decision: split.

The CIS benchmark check covers cloud accounts (P2). Built from the baseline is about images and infrastructure code, which a person points to.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `hardening-standard-such-as-cis-or` | A, E | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `operations-security-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `approved-configuration-baseline` | B | `cloud.hardening_baseline`; NEED version_control: The repositories holding infrastructure code are identified, and every change to them merged in the period was reviewed by someone other than its author | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; engineering lead confirms which images and templates are the baseline | P1 |
| `approved-exceptions-to-the-standard` | C, D | `cloud.hardening_baseline` | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |
| `alerts-on-drift-that-were-investigated` | C, D | `cloud.config_changes_recorded`; NEED cloud_infrastructure: Configuration rule findings are listed with first seen and resolved times, and each open past the response time is flagged | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | investigation notes or tickets for each drift alert | P2 |
| `asset-inventory` | D | `assets.resources_registered`; `cloud.hardening_baseline` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P1 |

No system can prove: that new systems were really built from the baseline rather than fixed later (NS-04.B, interview).

### NS-05 Infrastructure threat detection

SOC 2: CC6.8 (partial), CC7.2 (partial). ISO 27001:2022: A.8.16 (partial). Decision: keep.

Threat detection on and its findings both come from the cloud connector (P2). Triage decisions are people's.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `procedure-for-responding-to-threat-detection` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `incident-response-plan`; template `infrastructure-security-standard` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `asset-inventory` | B | `assets.resources_registered`; `cloud.threat_detection` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P2 |
| `alerts-on-drift-that-were-investigated` | B | `cloud.config_changes_recorded`; NEED cloud_infrastructure: Configuration rule findings are listed with first seen and resolved times, and each open past the response time is flagged; NEED cloud_infrastructure: Disabling the detection service, or an account without it, raises an alert | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | investigation notes or tickets for each drift alert | P2 |
| `sample-of-alerts-that-were-investigated` | C, D, E | NEED cloud_infrastructure: Threat detection findings are listed with severity, status, first seen and closed time, and who closed them; `alerts.acknowledged_in_time` | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | investigator's decision for each alert | P2 |
| `security-incident-register` | D | NEED cloud_infrastructure: Each finding of the severity the procedure names is linked to an incident record | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P1 |
| `review-of-alert-tuning` | E | NEED cloud_infrastructure: Suppression rules in the threat detection service are listed with a reason and author | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |

No system can prove: that triage decisions were right (NS-05.C).

### NS-06 Encryption key management

SOC 2: CC6.1 (partial). ISO 27001:2022: A.8.24 (partial). Decision: keep.

Rotation and key policies come from the cloud (P2). Retirement only after nothing depends on the key is hard to prove from APIs.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `key-management-policy` | A, D | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `cryptography-policy` | P1 |
| `doc-cryptography-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `cryptography-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `review-of-who-can-use-and` | B, C | NEED cloud_infrastructure: Key policies give administration and use to different roles, and no principal holds both | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P2 |
| `key-rotation-records` | D, E | `cloud.key_rotation`; NEED cloud_infrastructure: Disabled keys and keys pending deletion are listed with the stores and backups still using them | none | security lead's record of retirement steps | P2 |

No system can prove: that a retired key had no remaining dependency (NS-06.E, interview).

### NS-07 Network segmentation

SOC 2: CC6.1 (partial), CC6.6 (partial). ISO 27001:2022: A.8.20 (partial), A.8.22 (full). Decision: keep.

The cloud network configuration shows segments (P2). An active test of blocked paths stays with people or a pen tester.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `network-diagram-showing-segments-and-allowed` | A, B | `cloud.network_segmented` | Documents: Network diagram uploaded as a document linked to NS-07, with a yearly review date + `verity.policies.reviewed`; Assets: Assets by network segment with connects_to relationships | engineering draws and updates the diagram | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `segmentation-test-results` | B, D | `cloud.network_segmented`; NEED cloud_infrastructure: A reachability analysis between zones finds no path that the diagram forbids | none | scan from one segment to another, or the pen test section | P2 |
| `review-of-the-rules-between-segments` | C | `cloud.network_segmented` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |
| `penetration-test-report-from-an-independent` | D | none | Vulnerabilities: Findings imported from the report + `verity.vulns.within_sla` | report from the outside tester | people-only |

No system can prove: that the diagram matches reality in full; a test samples paths (NS-07.D).

### NS-08 No management ports exposed to the internet

SOC 2: CC6.6 (partial). ISO 27001:2022: A.8.20 (partial). Decision: keep.

The strongest automated control in the families: open admin ports are a cloud setting (P2).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `inbound-rules-export-admin-ports` | B, C | `cloud.admin_ports_closed` (full); NEED vulnerability_scanner: An external scan of the public address ranges finds no management port open | none | none | P2 |
| `approved-exceptions-for-exposed-management-access` | C | `cloud.admin_ports_closed` | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |
| `alerts-on-drift-that-were-investigated` | D | `cloud.config_changes_recorded`; NEED cloud_infrastructure: Configuration rule findings are listed with first seen and resolved times, and each open past the response time is flagged; NEED cloud_infrastructure: A change that opens a management port to a public range raises an alert | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla` | investigation notes or tickets for each drift alert | P2 |
| `remote-access-settings-and-members` | D | `edge.zero_trust_access`; NEED network_edge: Remote access members match current staff and approved contractors, and leavers were removed; NEED network_edge: Access policies grant per application or per system, not to whole networks; NEED network_edge: Remote session logs are retained and exported; NEED network_edge: Administrative SSH and RDP are reachable only through the zero trust or VPN tool | none | none | P2 |

No system can prove: that the approved route is the only route administrators use (NS-08.D).

### NS-09 Secrets management

SOC 2: CC6.1 (partial). ISO 27001:2022: A.5.17 (partial). Decision: keep.

The cloud secrets store shows presence and rotation dates (P2). Exposed secrets come from code host secret scanning.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `secrets-management-standard` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `engineering-security-standard` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `secret-store-rotation-list` | B, C, D | `cloud.secrets_managed`; NEED cloud_infrastructure: Each secret in the store has a last rotated date within the interval and an owner tag; values are never read | none | none | P2 |
| `records-of-exposed-secrets-that-were` | D | `vcs.secret_scanning_enabled`; NEED version_control: Secret scanning alerts are listed with created and resolved times and the resolution, and none stays open past the response time | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P2 |
| `security-incident-register` | D | none | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P1 |

No system can prove: that every secret used by services is in the store (NS-09.B, interview).

### NS-10 WAF and DDoS protection

SOC 2: CC6.6 (partial). ISO 27001:2022: A.8.21 (partial). Decision: keep.

Cloudflare proves WAF and DDoS in front (P2). Origin lockdown needs the cloud side too.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `review-of-web-application-firewall-rules` | B, C, D | `edge.waf_enabled`; NEED network_edge: Managed rule sets are in block mode, not log only, for each public hostname; NEED cloud_infrastructure: Each public origin accepts traffic only from the edge provider's ranges | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P2 |
| `asset-inventory` | B | `assets.resources_registered`; `edge.waf_enabled` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P2 |

No system can prove: that rule reviews passed genuine attack patterns to detection (NS-10.D).

### NS-11 VPN / zero-trust remote access

SOC 2: CC6.6 (partial). ISO 27001:2022: A.6.7 (partial), A.8.21 (partial). Decision: revise objectives.

Tailscale or Cloudflare Access prove settings and members (P2). Leaver removal needs a leaver source.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `remote-access-standard` | A, B | none | Documents: Policy register + `verity.policies.reviewed` | template `remote-working-policy`; template `infrastructure-security-standard` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `doc-remote-working-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `remote-working-policy` | P1 |
| `remote-access-settings-and-members` | B, C, D, E | `edge.zero_trust_access`; NEED network_edge: Remote access members match current staff and approved contractors, and leavers were removed; NEED network_edge: Access policies grant per application or per system, not to whole networks; NEED network_edge: Remote session logs are retained and exported | none | none | P2 |
| `roster-of-joiners-and-leavers-with` | C | `people.leavers_deprovisioned`; NEED hr_system: Joiners, movers and leavers are listed with effective dates | none | HR or payroll export | P3 |
| `review-of-privileged-access` | E | `idp.admins_limited` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |

No system can prove: that remote session reviews were meaningful (NS-11.E, interview).

### NS-12 Time synchronization

SOC 2: none. ISO 27001:2022: A.8.17 (full). Decision: keep.

Clock offset is rarely exposed by control plane APIs; the observability route is unverified. Mostly people and the quarterly check.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `trusted-time-sources-and-how-systems` | A, C, D | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `operations-security-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `clock-check-across-a-sample-of` | B, C | NEED observability: Each monitored host reports a clock offset within the allowed limit, and offsets beyond it raised an alert; NEED cloud_infrastructure: Each instance and managed service uses the provider's or a named time source | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | command output or monitoring view for systems no connector reads | P2 |
| `asset-inventory` | B | `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P1 |
| `evidence-logs-are-reviewed` | D | NEED observability: Log timestamps from every source are stored in UTC or carry an offset | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |

No system can prove: that every log source shares one time zone (NS-12.D) without reading each source.

### NS-13 Server and container image patching (proposed)

SOC 2: CC6.8 (partial), CC7.1 (partial). ISO 27001:2022: A.8.8 (partial). Successor, see Proposed control changes.

Servers and images: the cloud patch manager and image rebuilds can be read through the AWS connector (P2); scanners are Phase 3.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `patch-management-policy-with-timeframes` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy`; template `endpoint-security-standard` | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `patch-compliance-report` | B, C, D | NEED cloud_infrastructure: Each managed instance reports patch compliance from the cloud's patch manager, within the timeframe for its severity; NEED ci_cd: Running container images were rebuilt from a current base image within the set interval; `scanner.scans_current` | Vulnerabilities: Vulnerability SLA report + `verity.vulns.within_sla` | none | P2 |
| `log-of-control-deficiencies-with-owner` | D | `tickets.remediation_tracked` | Tasks: Remediation tasks report + `verity.tasks.remediation_in_sla`; Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |
| `emergency-changes-with-their-after-the` | E | `vcs.unreviewed_merges_recorded` | none | after the fact review notes | P2 |

No system can prove: that a manual emergency patch was reviewed with care (NS-13.E).

### NS-14 Network equipment hardening and firmware (proposed)

SOC 2: none. ISO 27001:2022: A.8.20 (partial), A.8.9 (partial). Successor, see Proposed control changes.

No network equipment connector exists in any catalogue. People and the review cadence only.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `hardening-standard-such-as-cis-or` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; template `operations-security-policy` | P1 |
| `doc-infrastructure-security-standard` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard` | P1 |
| `asset-inventory` | B, C | none | Assets: Network equipment assets (infrastructure type) with firmware and support dates in custom fields + `verity.assets.reviewed` | configuration backup log and firmware versions from each device | people-only |
| `approved-configuration-baseline` | B | none | Documents: Policy register + `verity.policies.reviewed` | template `infrastructure-security-standard`; device configuration backups | P1 |
| `approved-exceptions-to-the-standard` | C | none | Risk register: Control exceptions: risks linked to the control and accepted + `verity.exceptions.in_force` NEW | none | P1 |
| `alerts-on-drift-that-were-investigated` | D | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | comparison of running configuration with the backed up baseline | people-only |

No system can prove: the whole control, short of logging in to each device.

### DM-01 Breach notification process

SOC 2: P6.6 (full). ISO 27001:2022: A.5.5 (partial). Decision: revise objectives.

Notice decisions can be structured as an incident template subtask now. The decision itself is legal judgement.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `breach-notification-procedure-and-templates` | A, C, D, E | none | Documents: Policy register + `verity.policies.reviewed` | template `incident-response-plan`; template `security-communication-plan`; legal clearance of the notice templates | P1 |
| `doc-incident-response-plan` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `incident-response-plan` | P1 |
| `doc-security-communication-plan` | A, E | none | Documents: Policy register + `verity.policies.reviewed` | template `security-communication-plan` | P1 |
| `notification-decisions-for-each-incident-including` | B, C, E | none | Tasks: Incident notice decisions (notice decision subtask on each incident issue) + `verity.tasks.incident_notice_decided` NEW | legal lead's reasoning for each decision | P1 |
| `security-incident-register` | B | none | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty); Tasks: Incident notice decisions (notice decision subtask on each incident issue) + `verity.tasks.incident_notice_decided` NEW | none | P1 |
| `customer-contract-terms-on-breach-notification` | C, D | none | Documents: Uploaded standard customer agreement or data processing agreement, linked to CS-01 and DM-01 + `verity.policies.reviewed` | legal confirms the notice clause in the current standard terms | P1 |

No system can prove: whether an incident was notifiable and the deadline right (DM-01.A, D, legal interview).

### DM-02 Unauthorized-disclosure recordkeeping

SOC 2: P6.3 (full). ISO 27001:2022: none. Decision: keep.

The register is a filtered view of privacy incidents in Tasks. Near misses that never became an issue rely on people.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-personal-data-handling-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure` | P1 |
| `doc-incident-response-plan` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `incident-response-plan` | P1 |
| `register-of-unauthorized-disclosures-including-near` | B, C, D | none | Tasks: Privacy incidents and near misses (issues of category privacy from the incident template) + `verity.tasks.incident_notice_decided` NEW | near misses that never became an incident issue | P1 |
| `security-incident-register` | B | none | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P1 |

No system can prove: that every near miss was recorded (DM-02.B).

### DM-03 Consent and choice management

SOC 2: P2.1 (full), P3.2 (full). ISO 27001:2022: A.5.34 (partial). Decision: revise objectives.

Consent tools are business applications (Phase 3). Withdrawals can run as privacy request tasks now.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-personal-data-handling-procedure` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure` | P1 |
| `consent-withdrawal-process-and-records` | A, D | NEED business_applications: Withdrawals in the consent tool are listed with the time processing stopped | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | template `personal-data-handling-procedure`; written steps and the downstream notices | P1 |
| `consent-records-showing-when-what-and` | B, C, E | NEED business_applications: Consent records from the consent tool carry person or ID, time, purpose, notice version and capture method | none | export from the product database or consent tool | P3 |
| `current-privacy-notice` | E | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline`; observation of the live page matching the approved version | P1 |

No system can prove: that consent was freely given (DM-03.A).

### DM-04 Data classification policy

SOC 2: C1.1 (partial), CC2.1 (partial). ISO 27001:2022: A.5.10 (partial), A.5.12 (partial), A.5.13 (full), A.5.14 (partial), A.7.10 (partial). Decision: keep.

Classification per asset is a running Verity check; marking on files needs the productivity suite and is unverified.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `data-classification-policy` | A, C | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `doc-data-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `classification-applied-to-systems-and-data` | B, C | NEED identity_provider: Files and mail in the productivity suite carry a sensitivity label where the policy requires marking | Assets: Asset inventory report (classification column) + `verity.assets.classified` | observation of marked documents and records | P1 |
| `asset-inventory` | B | `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned`; Assets: Asset inventory report (classification column) + `verity.assets.classified` | none | P1 |
| `completion-records-for-all-staff` | D | none | Documents: Acknowledgement campaign for the data classification policy + `verity.policies.acknowledged` | training platform export or session sign in sheet | P1 |
| `doc-acceptable-use-policy` | D | none | Documents: Policy register + `verity.policies.reviewed` | template `acceptable-use-policy` | P1 |

No system can prove: that the level each data owner chose is right.

### DM-05 Personal-information correction

SOC 2: P5.2 (full), P7.1 (partial). ISO 27001:2022: A.5.34 (partial). Decision: keep.

Corrections as privacy request tasks (P1). Whether downstream systems were really corrected stays with people.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `correction-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `doc-privacy-requests-and-complaints-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `log-of-corrections-and-how-third` | B, C, D | NEED business_applications: Support tickets tagged as privacy requests carry received and answered times | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | third party notices | P1 |
| `data-inventory-and-data-map` | D | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |

No system can prove: that an identity check fitted the data (DM-05.B).

### DM-06 Data inventory and data map

SOC 2: C1.1 (full), CC2.1 (partial). ISO 27001:2022: A.5.12 (partial), A.5.9 (partial). Decision: keep.

The data map lives in Assets; a new check proves each data store carries what the map needs. Completeness against reality needs connectors.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-data-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `doc-asset-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `asset-management-policy` | P1 |
| `data-inventory-and-data-map` | B, C, D | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |
| `vendor-inventory-with-owner-data-and` | C, D | none | Vendors: Vendor register report + `verity.vendors.owner_and_tier`; Vendors: Vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | none | P1 |
| `dm-06-review-that-the-inventory-is-complete` | D | `assets.resources_registered` | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | none | P1 |
| `asset-inventory` | D | `assets.resources_registered`; `assets.resources_registered` | Assets: Asset inventory report + `verity.assets.owner_assigned` | none | P1 |

No system can prove: that the map shows every real flow (DM-06.C).

### DM-07 Data minimization

SOC 2: P3.1 (full). ISO 27001:2022: none. Decision: keep.

Reviews of collection points are people's; Verity proves the yearly cadence.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-personal-data-handling-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure` | P1 |
| `review-of-each-collection-point-against` | B, C | none | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW | sheet of forms, APIs and imports with fields and reasons | P1 |
| `register-of-the-purposes-personal-information` | B | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure`; privacy lead keeps the register current | P1 |
| `evidence-security-was-considered-in-the` | C | NEED version_control: Pull requests that add personal data fields carry a privacy review label or link | none | design review or threat model with a security and privacy section | people-only |

No system can prove: that a field is really needed (DM-07.B, C).

### DM-08 Data retention schedule

SOC 2: C1.2 (partial), P4.2 (full), PI1.5 (partial). ISO 27001:2022: A.5.33 (partial), A.8.10 (partial). Decision: revise objectives.

Lifecycle rules are visible in the cloud (P2); proof they ran is weaker. Legal holds are people's.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `data-retention-schedule` | A, B, C, D | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `doc-data-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `evidence-data-was-deleted-when-retention` | B, D | `cloud.storage_lifecycle`; NEED cloud_infrastructure: Lifecycle and expiry rules ran in the period, with deletion counts per store; `observability.processing_monitored` | Tasks: Manual deletion tasks | purge job logs and tickets for manual deletions | P2 |
| `backup-policy-covering-scope-frequency-and` | C | `cloud.backups_enabled` | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy`; template `business-continuity-and-disaster-recovery-plan` | P1 |

No system can prove: that legal holds were applied and lifted correctly (DM-08.D, legal interview).

### DM-09 Authorized-disclosure governance

SOC 2: P6.1 (partial), P6.2 (full), P6.7 (partial). ISO 27001:2022: A.5.14 (partial). Decision: keep.

Vendors flagged as holding personal data are the register; lawful basis has no field yet.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-personal-data-handling-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure` | P1 |
| `doc-third-party-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `third-party-management-policy` | P1 |
| `register-of-authorized-disclosures-to-third` | B, D | none | Vendors: Vendor register filtered to vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | none | P1 |
| `vendor-inventory-with-owner-data-and` | B | none | Vendors: Vendor register report + `verity.vendors.owner_and_tier`; Vendors: Vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | none | P1 |
| `consent-or-lawful-basis-for-each` | C | none | Vendors: Vendor approvals before first data transfer + `verity.vendors.personal_data_recorded` NEW | contract, consent record or legal note for each new recipient | P1 |
| `current-privacy-notice` | C | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline`; observation of the live page matching the approved version | P1 |
| `data-inventory-and-data-map` | D | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |

No system can prove: the lawful basis for each disclosure (DM-09.C).

### DM-10 Data processing agreements with vendors

SOC 2: CC9.2 (partial), P6.4 (partial). ISO 27001:2022: A.5.20 (partial), A.5.34 (partial). Decision: keep.

Already a running Verity check (dpa_on_file).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-third-party-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `third-party-management-policy` | P1 |
| `executed-data-processing-agreements-for-vendors` | B, C, D | none | Vendors: Vendor contracts of type dpa + `verity.vendors.dpa_on_file` | none | P1 |
| `vendor-inventory-with-owner-data-and` | B | none | Vendors: Vendor register report + `verity.vendors.owner_and_tier`; Vendors: Vendors flagged as holding personal data + `verity.vendors.dpa_on_file` | none | P1 |
| `security-terms-agreed-in-each-vendor` | C | none | Vendors: Vendor contracts: right to audit, subprocessor terms, breach hours, exit clause + `verity.vendors.breach_terms_recorded` NEW | none | P1 |

No system can prove: that each signed agreement carries adequate terms (DM-10.C reading).

### DM-11 Data-subject access request process

SOC 2: P5.1 (full), P6.7 (partial). ISO 27001:2022: A.5.34 (partial). Decision: revise objectives.

Requests as tasks with deadlines (P1). Completeness of each answer is a person's review.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `access-request-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `doc-privacy-requests-and-complaints-procedure` | A, E | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `log-of-requests-with-dates-and` | B, C, E | NEED business_applications: Support tickets tagged as privacy requests carry received and answered times | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | requests that arrived outside the intake point | P1 |
| `sample-responses-that-include-disclosure-accounting` | C, D | none | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW; Vendors: Vendor register filtered to vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | the answers sent, with the disclosures listed | P1 |
| `data-inventory-and-data-map` | D | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |
| `register-of-authorized-disclosures-to-third` | D | none | Vendors: Vendor register filtered to vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | none | P1 |

No system can prove: that an answer drew on every system holding the person's data (DM-11.D).

### DM-12 Limit personal-information use to purpose

SOC 2: P4.1 (full). ISO 27001:2022: A.5.34 (partial). Decision: keep.

New uses as approval tasks (P1). Whether data trained a model is not visible to any connector in the plan.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `register-of-the-purposes-personal-information` | A, B, D, E | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure`; privacy lead keeps the register current | P1 |
| `doc-personal-data-handling-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure` | P1 |
| `role-and-access-matrix` | B | `idp.groups_drive_access`; NEED identity_provider: Groups that grant access to systems holding personal data contain only the roles the purpose register allows | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy` | P1 |
| `review-of-new-uses-against-the` | C, D, E | none | Tasks: New use of personal data tasks with approval + `verity.tasks.approved_before_done` NEW | note for each new use | P1 |
| `current-privacy-notice` | C | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline`; observation of the live page matching the approved version | P1 |
| `data-inventory-and-data-map` | E | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |

No system can prove: that no personal data trained a model beyond the stated position (DM-12.D, interview).

### DM-13 No production data in lower environments

SOC 2: C1.1 (partial). ISO 27001:2022: A.8.33 (full). Decision: keep.

The cloud can show environments apart and production copies moving (P2). Fake versus real data is a person's look.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `policy-against-production-data-in-lower` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `secure-development-policy`; template `operations-security-policy` | P1 |
| `doc-secure-development-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `secure-development-policy` | P1 |
| `doc-data-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `evidence-test-data-is-masked-or` | B, C | `cloud.environments_separated`; NEED cloud_infrastructure: No production snapshot or database copy was restored into, or shared with, a non production account in the period | none | seed or masking script and a screenshot of test records; observation | P2 |
| `sample-of-masked-data-in-test` | C | NEED cloud_infrastructure: Data stores in non production accounts carry a masking or synthetic tag | Assets: Data assets in non production environments with owner and masking method (custom field) | sample showing the listed fields masked | P1 |

No system can prove: that test records are fake rather than real (DM-13.B, observation).

### DM-14 Privacy inquiry and complaint handling

SOC 2: P8.1 (partial). ISO 27001:2022: none. Decision: keep.

Inquiries as tasks (P1). The published contact point is observed by a person.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `privacy-inquiry-and-complaint-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `doc-privacy-requests-and-complaints-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-requests-and-complaints-procedure` | P1 |
| `current-privacy-notice` | B | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline`; observation of the live page matching the approved version | P1 |
| `log-of-inquiries-with-resolution-times` | B, C, D | NEED business_applications: Support tickets tagged as privacy inquiries carry received and resolved times | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | none | P1 |

No system can prove: that common causes were found and acted on (DM-14.D).

### DM-15 Privacy notice

SOC 2: P1.1 (full). ISO 27001:2022: A.5.34 (partial). Decision: keep.

Versions of the notice in Documents (P1). Whether it matches practice is a comparison a person makes.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `current-privacy-notice` | A, B, D | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline`; observation of the live page matching the approved version | P1 |
| `doc-privacy-notice-outline` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `privacy-notice-outline` | P1 |
| `data-inventory-and-data-map` | B | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |
| `register-of-the-purposes-personal-information` | B | none | Documents: Policy register + `verity.policies.reviewed` | template `personal-data-handling-procedure`; privacy lead keeps the register current | P1 |
| `register-of-authorized-disclosures-to-third` | B | none | Vendors: Vendor register filtered to vendors that hold personal data + `verity.vendors.personal_data_recorded` NEW | none | P1 |
| `data-retention-schedule` | B | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `notice-change-history-and-how-data` | C, D | none | Documents: Version history of the privacy notice document | the email or banner that announced each change | P1 |

No system can prove: that the notice matches practice (DM-15.B comparison).

### DM-16 Secure data disposal

SOC 2: C1.2 (partial), P4.3 (full). ISO 27001:2022: A.8.10 (full). Decision: split.

After the split this is data deletion. Lifecycle rules and purge jobs are partly visible (P2); deletion from vendor systems is not.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `secure-disposal-procedure` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `asset-management-policy`; template `data-management-policy` | P1 |
| `doc-data-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `evidence-data-was-deleted-when-retention` | D, E | `cloud.storage_lifecycle`; NEED cloud_infrastructure: Lifecycle and expiry rules ran in the period, with deletion counts per store; `observability.processing_monitored`; NEED cloud_infrastructure: Backups age out within the backup retention window, and no backup older than it exists | Tasks: Manual deletion tasks; Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | purge job logs and tickets for manual deletions | P2 |
| `data-inventory-and-data-map` | D | `assets.resources_registered`; NEED business_applications: Business applications that hold personal data are listed | Assets: Data stores and their relationships + `verity.assets.data_stores_mapped` NEW; Vendors: Vendor register filtered to vendors that hold personal data | flow diagram | P1 |
| `backup-policy-covering-scope-frequency-and` | D | `cloud.backups_enabled` | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy`; template `business-continuity-and-disaster-recovery-plan` | P1 |
| `log-of-requests-with-dates-and` | E | NEED business_applications: Support tickets tagged as privacy requests carry received and answered times | Tasks: Privacy request log (tasks from the privacy request templates) + `verity.tasks.privacy_requests_on_time` NEW | requests that arrived outside the intake point | P1 |

No system can prove: deletion inside vendor systems and analytics copies (DM-16.D).

### DM-17 Vendor breach-notification terms

SOC 2: P6.5 (partial). ISO 27001:2022: A.5.20 (partial). Decision: keep.

Contract breach hours are a vendor contract field already; a new check makes it a test.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `doc-third-party-management-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `third-party-management-policy` | P1 |
| `vendor-contract-terms-with-the-breach` | A, B, C | none | Vendors: Vendor contracts with breach notification hours + `verity.vendors.breach_terms_recorded` NEW | none | P1 |
| `executed-data-processing-agreements-for-vendors` | B | none | Vendors: Vendor contracts of type dpa + `verity.vendors.dpa_on_file` | none | P1 |
| `security-assessment-for-each-critical-vendor` | C | none | Vendors: Vendor assessments + `verity.vendors.assessed_in_cadence` | none | P1 |
| `record-of-vendor-notifications-received-and` | D | none | Tasks: Vendor breach notice tasks (category vendor) + `verity.tasks.incident_notice_decided` NEW; Vendors: Vendor signals of type breach | the vendor's notice email | P1 |
| `notification-decisions-for-each-incident-including` | D | none | Tasks: Incident notice decisions (notice decision subtask on each incident issue) + `verity.tasks.incident_notice_decided` NEW | legal lead's reasoning for each decision | P1 |

No system can prove: that the vendor's contact path works (DM-17.C).

### DM-18 Masking sensitive fields

SOC 2: none. ISO 27001:2022: A.8.11 (full). Decision: keep.

Masking is engineering work no connector sees; people and the role matrix.

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `masking-standard-listing-fields-methods-and` | A, B, D | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy`; engineering lead's field list with method per use | P1 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `data-classification-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `data-management-policy` | P1 |
| `change-requests-with-approval-for-a` | B | `vcs.merged_changes_reviewed`; `tickets.changes_linked` | none | none | P2 |
| `sample-of-masked-data-in-test` | C, E | none | Assets: Data assets in non production environments with owner and masking method (custom field) | sample showing the listed fields masked | P1 |
| `role-and-access-matrix` | D | `idp.groups_drive_access` | Documents: Policy register + `verity.policies.reviewed` | template `access-control-policy`; database or support tool roles that can see unmasked fields | P1 |

No system can prove: that masked data cannot be reversed (DM-18.E, test by engineering).

### DM-19 Outbound data leak controls

SOC 2: none. ISO 27001:2022: A.5.14 (partial), A.7.10 (partial), A.8.12 (full). Decision: keep.

Sharing settings in the productivity suite and public bucket blocks are connector checks (P2); removable storage needs device management (P3).

| Artifact | Objectives | Connected systems | Verity modules | People and documents | Phase |
|---|---|---|---|---|---|
| `leakage-prevention-and-sharing-settings-in` | A, B, C | NEED identity_provider: External sharing in the mail and file suite is limited as the rules set, public links are off or expire, and leak prevention rules are on; NEED cloud_infrastructure: Storage buckets block public access at account level; NEED device_management: Removable storage is blocked or limited to encrypted media by a device profile; NEED business_applications: Chat and file sharing tools restrict external sharing as the rules set | none | template `operations-security-policy`; screenshots for tools no connector reads | P2 |
| `doc-operations-security-policy` | A | none | Documents: Policy register + `verity.policies.reviewed` | template `operations-security-policy` | P1 |
| `inventory-of-company-devices` | C | `devices.enrolled`; NEED device_management: Removable storage is blocked or limited to encrypted media by a device profile | none | device management export or a sheet | P3 |
| `alerts-and-exceptions-that-were-reviewed` | D, E | NEED identity_provider: Leak prevention and sharing alerts in the mail and file suite are listed with severity, status and triage time | Tasks: Recurring review task linked to the control, with the signed record attached + `verity.tasks.reviews_on_cadence` NEW; Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | triage notes for each alert | P2 |
| `security-incident-register` | D | none | Tasks: Incident register (issues from the incident template, with a quarterly nil return when empty) | none | P1 |

No system can prove: that alert triage decisions were right (DM-19.D).

## What no system can prove, across the families

- **Judgements**: whether a role is least privilege, an access was needed, a review was careful, a
  compensating safeguard works, a field is needed, an incident was notifiable. These are interviews and a
  person's determination, always.
- **Physical facts**: visitors escorted, desks clear, protections matching hazards, engineers supervised.
  Observation only.
- **Outside parties' work**: the pen test, the disposal contractor's certificate, the provider's SOC
  report. Verity can record that it was read and followed up, not that it is right.
- **Absence**: an empty incident register, privacy request log or exception list proves nothing unless
  the source can show the population was empty. Those checks report insufficient information until a
  person files a dated nil return.
- **Anything outside the connected systems**: local accounts, shared credentials, vendor copies of data,
  the product's own password storage.

## Gaps and content problems found

| # | Problem | Where | Proposed fix |
|---|---|---|---|
| 1 | All 14 `checks.json` links from a connector check to a control in these families are `full` with the rationale "which is what the control states" (`cloud.encryption_at_rest` NS-01, `cloud.admin_ports_closed` NS-08, `idp.sso_enforced` IAM-04, `idp.password_policy` IAM-06, `idp.session_timeout` IAM-11, `people.leavers_deprovisioned` IAM-12, `vault.everyone_enrolled` IAM-05, `tickets.access_requests_approved` IAM-01, `edge.waf_enabled` NS-10, `edge.zero_trust_access` NS-11, `devices.enrolled` EP-03, `devices.disk_encrypted` EP-02, `devices.screen_lock` EP-06, `endpoint.protection_active` EP-01). Each control has design objectives and other operating objectives the check does not test, so EC-3 is broken. | `automation/checks.json` | Make all 14 partial with a rationale naming what remains (policy, exceptions, review, population outside the source). |
| 2 | `people.leavers_deprovisioned` needs an HR source, which is in no signed phase, and cannot see systems outside single sign on (IAM-12.D). Its full link to IAM-12 can never be met. | `checks.json`, IAM-12 | Partial, plus the CSV roster import of control-framework-requirements question 1. |
| 3 | 45 document artifacts used by these families list only a person as source, although a shipped template holds the text (for example `password-policy`, `screen-lock-standard`, `key-management-policy`). Many objectives name both the person artifact and the `doc-*` artifact for the same document (EP-01.A names `endpoint-protection-standard` and `doc-endpoint-security-standard`). | `objectives/artifacts.json` | Give each a `document` source with its template and section, or fold it into the `doc-*` artifact. The JSON here already maps each to its template. |
| 4 | Template text falls short of the objectives that rely on it: `access-control-policy` asks for a second factor only on privileged production access, has no single sign on rule and no session limits, and its example password minimum is eight characters against IAM-06.A's 12; `third-party-management-policy` has no data processing agreement requirement and no breach notice hours; `cryptography-policy` has no rotation or key service rule; `endpoint-security-standard` has no web filtering; `engineering-security-standard` has nothing on product sign in. No masking standard or backup policy template exists. | `policies/document_templates.json` | Add the sections (CL-6 work), or point the objectives at `infrastructure-security-standard` and `operations-security-policy`, which hold several of them. |
| 5 | Assets has no endpoint or device type (`ASSET_TYPES` is application, infrastructure, data, cloud, third party, business service), yet `inventory-of-company-devices` says it lives in Assets and laptop disposal records go there. | `modules/assets/models.py` | Add an endpoint type (migration) before device management connectors land, so the device inventory and EP-08 records have a home. |
| 6 | There is no staff roster in Verity and no HR connector in any signed phase. Seven controls compare against the roster (IAM-01, IAM-05, IAM-12, EP-03, EP-05, NS-11, PE-02). Verity members are not a roster. | capability `hr_system` | The CSV roster import (proposed, not built). |
| 7 | Device management and endpoint protection are not in the signed catalogue, so EP-01 to EP-06 and DM-19.C stay on people. | Appendix A | Owner decision (question 1 of control-framework-requirements). |
| 8 | `capabilities.json` has no `business_applications` (Appendix A lists it for Phase 3) and no `verity_identity`. Productivity suite sharing and leak prevention settings (Google Workspace, Microsoft 365) have no capability; this file files them under `identity_provider`. | `automation/capabilities.json` | Add both capabilities; decide whether the suite settings deserve their own. |
| 9 | Artifact key `access-request-procedure` is the data subject access request procedure, beside `access-request-and-approval-procedure` for IAM. | `artifacts.json` | Rename to `data-subject-access-request-procedure` (with a migration of any evidence that references it). |
| 10 | Tasks has no incident kind; `security-incident-register` relies on an incident template convention until the Incidents module (Phase 3.1). Tasks also has no custom fields, so a notice decision can only be a subtask. | `modules/tasks` | Incident template with notice decision and notice sent subtasks now; Incidents module later. |
| 11 | Vendors has no lawful basis field (DM-09), no sign in method per application (IAM-04.B); discovered apps wait for the identity connectors. | `modules/vendors` | Add lawful basis and sign in method fields when DM-09 and IAM-04 automation is built. |
| 12 | The data map needs retention and encryption per store, which Assets holds only as custom fields. | `modules/assets` | Accept custom fields with fixed keys, or add columns. |
| 13 | No objective tested deletion when a customer leaves or on an erasure request. | DM | DM-16.E (proposed). |
| 14 | Coverage cannot depend on applicability: a split with a conditional successor lowers ISO status when the successor is not applicable (A.5.3, A.8.9). | readiness engine, CL-3 | Model "full when the sibling is not applicable" before the splits ship. |
| 15 | Overlaps kept on purpose: DM-04.B and DM-06.B (classification per store); HR-05 and IAM-12 (leavers; HR family to settle); LM-11 and NS-13 (server remediation; LM family to settle). | | Note for the reviewers. |
| 16 | The runner for Verity checks is not built (ME-2), so every P1 check here, existing or new, is planned. | | |

## Sources

Internal only: `AUTHORING.md`; `seed/content/objectives/objectives.json` and `artifacts.json`;
`seed/content/automation/checks.json` and `capabilities.json`; `seed/content/soc2` and `iso27001`
`control_templates.json` and `template_requirements.json`; `seed/content/policies/document_templates.json`;
`docs/product/guided-onboarding/05-control-library-and-objectives.md`;
`docs/product/control-framework-requirements.md` (Appendices A to C); `docs/product/continuous-compliance-plan.md`
(sections 4 to 6); `docs/architecture/check-catalogue.md`; `docs/runbooks/keycloak-production.md` and
`sso-providers.md`; models in `backend/src/verity/modules/` (iam, assets, tasks, vendors, risk, links,
onboarding). This file makes no claim about a provider's API, scope or plan; NEED predicates say what must
be true, and the connector documents decide whether each provider can show it. Predicates whose feasibility
is in doubt are marked unverified in the JSON.
