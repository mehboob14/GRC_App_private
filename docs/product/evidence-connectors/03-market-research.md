# 3. Market research: how comparable platforms connect systems and judge evidence

Researched on 23 November 2026 from public help centres, developer docs, product pages, engineering
blogs and public code. It describes documented behaviour, not private implementation. It extends
section 4 of `docs/product/control-evidence-sufficiency.md` (Vanta's controls page and test evidence
view, Drata's readiness and approvals, Vanta's vulnerability guidance) and does not repeat it.

Citations are short ids in square brackets, for example [V1]. The full URLs are in section 3.13.
"Unverified" means I could not confirm the point on an official page.

**Names the owner gave.** "Intrata" is read as **Drata** (spoken as "in Drata"). "Like dot" is read as
**Laika**, the name Thoropass traded under until March 2023 [T1], so it is covered under Thoropass. If
the owner meant another product (for example Scytale or Delve), that platform is not in this document.

## 3.1 Comparison at a glance

| Platform | Integrations claimed | How an IdP connects | Own device agent | Push your own data | How tests reach controls | Freshness model | Does the IdP setup also give SSO into the platform? |
|---|---|---|---|---|---|---|---|
| Vanta | 400+ [V15] | Okta API Services app with six read scopes; Entra vendor app with admin consent; Google vendor OAuth app [V1][V2][V3] | Yes, a modified osquery build, closed source [V4] | Build Integrations API, full state push, custom resources and custom tests [V7][V8] | Built-in tests pre-mapped; custom tests mapped by the customer [V8] | Syncs about hourly; tests rerun as data arrives [V1][V8] | No. SAML app and SCIM app are separate setups [V1] |
| Drata | "Hundreds", 28 categories [D25] | Okta read-only admin token plus Drata OIDC app; Microsoft 365 admin consent; Google OAuth with delegated roles or domain-wide delegation [D1][D3][D4] | Yes, Electron and osquery, open source (Apache-2.0) [D6][D7] | Custom Connections and Tests, JSON records, Advanced and Enterprise plans [D19] | Tests are JSON documents; one test can serve many controls [D23] | Agent every 24 hours; MDM nightly [D6][D9] | Partly. The Okta connection carries the OIDC app credentials; other IdPs use a separate SSO connection through WorkOS [D1][D5] |
| Secureframe | 300+ [S13] | Okta OAuth (or API token); Google super admin with five scopes [S1][S2] | Yes, built on Fleet and osquery, free [S5][S6] | Custom Integrations by JSON or CSV, Complete plan [S11] | Tests mapped from either side; control operates when all its tests pass [S10] | Daily refresh; "At Risk" before "Failing"; upload tests have a next due date [S10] | No. SSO and SCIM are separate [S3][S4] |
| Sprinto | 300+ [P15] | Okta API token with two read scopes; Google super admin, three read scopes [P1][P2] | Yes, Dr. Sprinto [P4] | Custom integrations in sessions; evidence upload API; GraphQL developer API in beta [P11][P12][P13] | Checks mapped to controls; only mapped checks reach an audit [P9] | Due, Critical and Failing thresholds in days [P9][P10] | Not stated in the Okta guide [P1] |
| Thoropass (formerly Laika) | Not published in docs I could read (unverified) | API keys entered in Thoropass; details not public [T4] | None found; MDM listed as coming soon [T7] | Not found; an MCP server exists [T8] | Monitors generated per integration, tied to control owners [T3] | Not documented [T3] | No. Okta catalogue app is for sign in [T9] |
| Scrut | About 157 entries in 19 categories [C1] | Okta API Service Integration with three read scopes; Google OAuth [C2][C4] | Yes, Scrut Endpoint Agent (macOS page) [C5] | Not found in public docs (unverified) | Integration tests appear per application; MDM checks can map to controls [C6] | Google syncs every 24 hours [C4] | Google: yes, the same integration offers SSO. Okta: no, separate app [C3][C4] |
| Hyperproof | 200+ [H7] | Okta API token from a read-only service account [H1] | No | Hypersync SDK (TypeScript, MIT) [H5] | Automated tests on one proof each, on a control or a label [H2] | Scheduled Hypersyncs; tests run on demand or saved [H2] | No. Okta SAML app is separate [H8] |
| ServiceNow IRM, CAM, Policy and Compliance | Platform and Store, no single count [N6] | IntegrationHub spokes and Service Graph Connectors feed platform tables [N3] | No | Script indicators and platform integrations [N2] | CAM: control test plans built from NIST 800-53A assessment procedures [N1] | Indicators run on a collection frequency [N2] | No. Platform SSO is configured separately [N7] |

## 3.2 Question 1: connecting an identity provider

### Okta

| Platform | Method | Permissions requested | Admin role | Notes |
|---|---|---|---|---|
| Vanta | API Services app, OAuth 2.0 with a private key (default); SSWS API token as fallback [V1] | `okta.appGrants.read`, `okta.apps.read`, `okta.groups.read`, `okta.policies.read`, `okta.roles.read`, `okta.users.read`; FedRAMP adds two more [V1] | Super Administrator on the app, because role data needs it [V1] | Validation flags both missing and extra scopes. DPoP must be off. Admin URLs are rejected. One app per workspace [V1] |
| Drata | Service account token (SSWS) plus the "Drata OIDC" catalogue app [D1] | Catalogue app needs only `okta.users.read.self`; the token carries the service account's rights [D1] | Read-only Administrator on the service account [D1]; user access review needs a custom role [D2] | Hire date defaults to profile creation unless custom attributes are added; separation date is the deactivation date [D1] |
| Secureframe | OAuth app; API token as an alternative [S1] | Real time updates need `okta.eventHooks.manage` and `okta.eventHooks.read` [S1] | Connecting user must be assigned to the app [S1] | Refresh tokens can expire in some Okta setups and force a reconnect [S1] |
| Sprinto | API token [P1] | `okta.apps.read`, `okta.users.read` [P1] | Any role that can create tokens, Read-only Administrator included [P1] | Checks: leaver access removed, MFA enabled [P1] |
| Scrut | API Service Integration from the Okta catalogue, client id and secret [C2] | `okta.users.read`, `okta.groups.read`, `okta.roles.read` [C2] | Okta admin to install [C2] | SSO uses a different catalogue app [C3] |
| Hyperproof | API token from a service account [H1] | Inherits the account's rights [H1] | Read-only Administrator or a custom role [H1] | Proof types include group members, admins, API tokens, deactivated users, devices [H1] |

A third-party integrator reports that Okta's Read-only Administrator cannot read role assignments [O3].
That matches Vanta's demand for Super Administrator on its app. It is unverified on Okta's own pages.

### Microsoft Entra ID

| Platform | Method | Permissions | Admin role | Notes |
|---|---|---|---|---|
| Vanta | Vendor enterprise app, admin consent, app-only sync [V3] | `User.Read.All`, `Directory.Read.All`; `AuditLog.Read.All` optional [V3] | Global Administrator or Privileged Role Administrator; PIM roles must be active [V3] | Conditional Access on workload identities can silently stop sync [V3] |
| Drata | Microsoft sign in and admin consent; creates an enterprise app [D3] | `Directory.Read.All`, `Reports.Read.All`, `User.Read.All`, `Policy.Read.All`, `AuditLog.Read.All` [D3] | Global Admin whose domain matches the Drata tenant [D3] | Scoping works only with Microsoft 365 groups. A security group is ignored and everyone syncs [D3] |
| Others | Not documented in the pages I read (unverified) | | | |

### Google Workspace

| Platform | Method | Permissions | Admin role | Notes |
|---|---|---|---|---|
| Vanta | Vendor OAuth app; three client ids to trust when third-party apps are restricted [V2] | Read users, groups, admin roles; token data only if vendor discovery is on [V2] | Super Admin recommended; limited read roles work [V2] | If users sign in through an external SAML IdP, Vanta cannot see MFA enforced there [V2] |
| Drata | OAuth with delegated admin roles (recommended) or a super admin with domain-wide delegation [D4] | `admin.directory.user.readonly`, `.group.readonly`, `.orgunit.readonly`, `.domain.readonly` [D4] | User Management Admin, Group Admin, Directory Sync Admin, or super admin [D4] | Only top-level group members sync [D4] |
| Secureframe | OAuth app marked Trusted [S2] | `userinfo.email`, `userinfo.profile`, `admin.directory.user.readonly`, `admin.directory.user.security` (used only for token listing), `admin.directory.rolemanagement.readonly` [S2] | Super Admin [S2] | |
| Sprinto | OAuth [P2] | `admin.directory.group.readonly`, `admin.directory.user.readonly`, `admin.directory.customer.readonly` [P2] | Super Admin [P2] | |
| Scrut | OAuth [C4] | Read-only audit reports scope [C4] | Not stated | Same integration offers SSO for admins and staff [C4] |

### Does the same connection give single sign on to the platform?

| Platform | Answer |
|---|---|
| Vanta | No. The API integration, the SAML app and the SCIM app are three setups. Vanta tells customers that connecting an IdP is not enabling SSO [V1][V11] |
| Drata | For Okta, one connection form takes both the API token and the OIDC app's client id and secret [D1]. For other IdPs, SSO is a separate connection run through WorkOS that needs the IdP connection first [D5] |
| Secureframe | No. SSO and a separate SCIM app are configured in company settings [S3][S4] |
| Scrut | Google: yes. Okta: no [C3][C4] |
| Sprinto, Hyperproof, Thoropass, ServiceNow | Not combined in anything I found [P1][H8][T9][N7] |

**What this tells us.** Vendor apps with admin consent are the norm for Entra and Google. Okta is
split: half the field still uses SSWS tokens tied to a service account. Least privilege varies
widely: Vanta needs Okta Super Administrator, Secureframe asks for an event hook "manage" scope, and
Drata's own guide says its token gives administrative access to Okta data [V1][S1][D1].

## 3.3 Question 2: device evidence

| Platform | Own agent | Built on | Open source | Checks | Cadence | Distribution | MDM integrations |
|---|---|---|---|---|---|---|---|
| Vanta | Vanta Device Monitor [V4] | osquery, with risky tables removed [V4] | No public repo found | 28 named queries: disk encryption, installed apps, browser extensions, screen lock and timeout, local and admin users, SSH users, OS version, security products [V4] | Not stated | Employee installs from their task page [V4] | Jamf Pro (macOS only, no mobile), Kandji (now Iru), Intune (no iOS or Android) [V5][V6] |
| Drata | Drata Agent [D6] | Electron (TypeScript) and osquery [D6][D7] | Yes, Apache-2.0, since 16 June 2023 [D6][D7] | Disk encryption, screen lock, antivirus, password manager, automatic updates; app and extension lists; serial number [D6] | First network connection, then every 24 hours, not configurable [D6] | Magic link registration [D7] | Jamf (nightly, Jamf Now unsupported), Kandji, Intune, JumpCloud; several MDMs allowed, one source per device; the agent wins over Jamf [D8][D9][D10] |
| Secureframe | Secureframe Agent, free [S5][S7] | Fleet and osquery [S6] | Fleet is open source (mostly Go, MIT) [O1]; Secureframe's own changes not found | Disk encryption, password policy, firewall, native antivirus, screen lock; Linux gaps [S5] | Not stated | Not stated in the pages read | Kandji, Jamf Pro, Intune, JumpCloud, Kolide, Rippling and more, plus EDR such as CrowdStrike and SentinelOne [S7] |
| Sprinto | Dr. Sprinto [P4] | Not stated | No | OS version, screen lock (idle 15 minutes or less), disk encryption, antivirus from a supported list, firewall; a failing check shows the reason, last evidence, a rescan and an upload [P4][P5][P6] | Docs conflict: every 24 hours or every few hours [P4] | Elevated rights only at install [P4] | Hexnode (all three checks), Intune (screen lock, Windows antivirus), Jamf (screen lock only) [P5] |
| Scrut | Scrut Endpoint Agent [C5] | Not stated | Not stated | FileVault, XProtect, screen lock, Chrome password manager extension [C5] | Manual "Sync Now" shown [C5] | Employee portal download with email one-time code [C5] | 12 MDM tools; EDR such as CrowdStrike and Defender [C1] |
| Thoropass | None found | | | | | | MDM device support "coming soon" [T7] |
| Hyperproof | None | | | Okta device lists as proof [H1] | | | Not checked |
| ServiceNow | None | | | | | | Service Graph Connectors for Intune and Jamf fill the CMDB [N3][N4]; Configuration Compliance imports scanner results and matches failures to CMDB assets [N5] |

**Personal devices.** No vendor solves this technically. Drata's guidance is the clearest: write a
BYOD authorisation into an existing policy, keep phones and tablets away from customer data, upload a
screenshot when a setting cannot be read, and use a personnel exclusion for device checks that keeps
the person in audit scope [D11][D12]. Secureframe says mobile devices may appear in inventory but its
checks do not apply to them, so mark them out of scope [S7]. Secureframe pitches its agent as a step
for teams under 50 people with no MDM, not a lasting MDM replacement [S7]. When an MDM API cannot
supply a value, Secureframe turns that test into an upload test [S7]. I found no Vanta article on
personal devices.

**What this tells us.** osquery is the common base (Vanta, Drata, Secureframe through Fleet). The
check list has converged on five or six items. Publishing the code (Drata) or the query schedule
(Vanta lets anyone list it locally with its CLI [V4]) is how vendors earn trust for an agent.

## 3.4 Question 3: HR systems and people evidence

| Platform | HRIS route | Background checks | Training | Policy acceptance | Joiners and leavers |
|---|---|---|---|---|---|
| Vanta | Native HRIS integrations [V14] | Checkr [V14] | Its own training inside the onboarding page; a test per training [V12] | A test per assigned policy; recurring tasks for yearly re-acceptance [V12] | Offboarding starts only once Vanta sees the person as no longer employed; deleting an IdP user can drop their group-based tasks [V13]. Vanta ranks the HRIS above the IdP for start and end dates [V11] |
| Drata | Connections, some through Merge's unified API [D13][D14]; several HRIS since November 2025, first one primary [D15] | Checkr, updated by webhooks; Certn, not for EU customers [D16][D17] | Own training, including AI awareness; KnowBe4; HIPAA proof uploaded by the employee [D18] | Policy review in the employee portal [D18] | HRIS gives status, start and separation dates; people matched by exact email [D13] |
| Secureframe | Finch, 150+ HRIS and payroll systems [S8] | Checkr (Vetty legacy); employee consents first; report lands in the data room [S9] | Own videos with questions, per group [S8] | Per group, tracked on the personnel page and in acknowledgement tests [S8] | Auditors sample leavers and ask for tickets or screenshots; keep inactive people for the trail [S8] |
| Sprinto | HRMS or IdP import, CSV fallback [P7] | Checkr, Certn, OnGrid; a check opens for anyone with no report [P7][P8] | Assigned by group, scores and times kept [P7] | Signature tied to a specific policy version [P7] | A departure date in the HRMS starts offboarding and creates a revocation task per connected system [P7] |
| Scrut | 27 HRIS tools; name, email, hire and exit dates, department, manager [C1] | Certn, Checkr, SpringVerify, ZincWork [C1] | KnowBe4, EC Council, Phished, ThreatCop [C1] | Not checked | |
| Hyperproof | HRIS and ATS proof types, many through Merge [H6] | | | | |
| Thoropass | Not documented publicly | Vetty and Checkr partner listings [T10] | | | |
| ServiceNow | Not covered by the IRM pages I read (unverified) | | | | |

**What this tells us.** Every SaaS competitor treats HRIS, background checks and training as core.
Two of them (Drata through Merge, Secureframe through Finch) buy HRIS breadth from a unified API
vendor instead of building each one.

## 3.5 Question 4: tests, controls, coverage, freshness, exclusions and auditors

| Platform | Mapping | Result states | Partial coverage | Freshness | Exclusions | Auditor side |
|---|---|---|---|---|---|---|
| Vanta | Built-in tests pre-mapped; custom tests mapped by the customer [V8] | OK, NEEDS_ATTENTION, DEACTIVATED, IN_PROGRESS, INVALID, NOT_APPLICABLE [V8] | No public coverage weight per mapping found | Tests rerun as synced data arrives [V8] | Built-in tests can be deactivated, not edited [V8] | A separate "Conduct an Audit" API [V7] |
| Drata | One test can satisfy many controls [D23] | Pass, fail, exclusion | Not found | Agent daily, MDM nightly [D6][D9] | Per finding with a business reason; by source tags (an Azure tag must be exactly `DrataExclude`); only some roles may exclude; disable a test only when it does not apply [D20][D21][D22] | Every AI-generated test was reviewed by auditors before release [D23] |
| Secureframe | From the control's testing tab or the test's controls tab [S10] | Passing, Failing, At Risk, Not Applicable [S10] | A control operates as designed only when all its tests pass [S10] | All tests refresh daily; upload tests have an interval and a next due date; a daily job archives stale evidence and fails the test [S10] | Not applicable needs a written reason; duplicates are "Disabled by Secureframe" [S10] | An auditor finding on evidence stops an upload test passing [S10] |
| Sprinto | Evidence counts from the check's creation date but reaches an audit only through a mapped control linked to that audit [P9] | Passing, Due, Critical, Failing [P9] | Not found | Day thresholds for Due, Critical, Failing; reminder, escalation and non-compliance offsets for recurring evidence [P9][P10] | Not checked | Audit Partner API with an evidence request lifecycle [P14] |
| Hyperproof | A test sits on a control or on a label shared by many controls [H2]; the control's testing status follows its tests only when set to "Calculated value" [H3] | Passed, Failed, Needs review [H2] | **Pass threshold**: the share of records that must pass [H2] | Scheduled Hypersyncs | **Empty proof behaviour**: defaults to Failed, can be set to Passed or Needs review [H2] | Proof header shows the criteria used; footer names the API call [H4] |
| ServiceNow CAM | Control test plans from NIST 800-53A assessment procedures, mapped to 800-53 Rev 5 [N1] | Each procedure: effective, ineffective, none, not applicable [N1] | A failed control test also fails its assessment objective [N1] | Indicators run on a set frequency [N2] | | Examine, Interview and Test descriptions are read-only during testing [N1] |
| ServiceNow Policy and Compliance | Indicators linked through templates to policy statements [N2] | Pass or fail against a target (percentage or count) [N2] | Target threshold [N2] | Collection frequency; nightly queues [N2] | | Supporting records kept up to a sample size [N2] |
| Thoropass | Monitors per integration, tasks to control owners [T3] | Healthy, Violations found, Connection errors [T5] | | | Data Rules filter what is monitored, for example only production tagged assets [T6] | Uploaded files are frozen snapshots [T5] |

**Test criteria and objectives.** Drata stores tests as JSON: a provider, target resource types and an
evaluator of conditions over JSON paths [D23]. Vanta's custom test logic runs per record, and one
failing record fails the test unless the customer changes the rule [V8]. Only ServiceNow publishes a
structure below the control: assessment objectives with examine, interview and test methods, rolled
up to the control [N1]. None of the SaaS vendors publishes a per mapping coverage level or an
objective layer that I could find.

## 3.6 Question 5: custom integrations

| Platform | Push data | Data shape | Custom tests | Evidence file API | SDK | Plan |
|---|---|---|---|---|---|---|
| Vanta | `PUT /v1/resources/<type>` with the full current state, typically hourly [V7] | Built-in types (`UserAccount`, `Computer`, `Vulnerability`, `BackgroundCheck`, `TrainingRecord`) or `CustomResource` [V7] | Dashboard only, no create API; immutable once saved; one primary and one secondary resource; flat properties only [V8][V9] | PDFs and similar can be uploaded [V7] | None; private apps use client credentials, public apps use the authorization code grant [V7] | Custom tests may need an upgrade [V9] |
| Drata | JSON records over the API, upsert by `id` [D19] | Schema from JSON Schema or sample data; one top-level string or number for display [D19] | Test Builder plus an advanced editor [D19] | Not checked | None | Advanced and Enterprise [D19] |
| Secureframe | JSON through the public API, or CSV [S11] | Schemas map to Secureframe models or custom ones [S11] | Custom Automated Tests and Custom Upload Tests [S10][S11] | `POST /tests/{test_id}/evidences`, multipart [S12] | None | Complete plan [S11] |
| Sprinto | Sessions: open, send pages, close to apply [P11] | Entities keyed by type, 100 items a page, about 5 MB; one bad record rejects the page [P11] | Automated checks with a test mode that never counts as evidence [P9] | REST upload API; GraphQL mutation for workflow checks (beta) [P12][P13] | None | Not stated |
| Hyperproof | A custom Hypersync app imported with the Hyperproof CLI [H5] | Declarative JSON for data sources, proof types and criteria [H5] | Automated control tests on any proof [H2] | Not checked | `@hyperproof/hypersync-sdk`, TypeScript, MIT, Node.js 22 [H5] | Not stated |
| ServiceNow | Script indicators, IntegrationHub, Service Graph Connectors [N2][N3] | Platform tables | Script indicators [N2] | Platform | Platform | Licensed per product |
| Scrut, Thoropass | Not found (unverified). Thoropass has an MCP server with OAuth [T8] | | | | | |

**Design details worth noting.** Vanta's full state push lets it see deletions without a delete call
[V7]. Sprinto's sessions make a sync atomic and allow only one at a time per integration [P11].
Drata caps payloads at 5 MB and 500 requests a minute per source IP [D19]. Hyperproof's SDK checks
connection health through `validateCredentials` or `validateAccessToken` hooks [H5].

## 3.7 Question 6: setup guides and connection health

| Platform | In product guidance | Health shown as |
|---|---|---|
| Vanta | A Quickstart and a longer Integration Guide per provider [V1]; a nine point checklist before connecting (right admin, company account, org-level scope, service account, IP allowlist, licence, clean reconnect, scoping, credentials) [V10]; a recommended order: cloud and IdP, then MDM, code and scanners, then HRIS and tickets, then training and background checks [V11] | Error label on the integration tile with "View error" and Reconnect [V10]; validation names missing or extra Okta scopes [V1]; a connection can succeed with partial data [V10] |
| Drata | Active and Available tabs; per category "Manage Account" pages to pick which accounts are monitored [D24] | Healthy or Unhealthy chip derived from sync steps; an AI summary explains failing steps [D24] |
| Secureframe | Step by step guide inside each integration; a "Permissions and Data" tab lists scopes [S1][S2] | Request logs and errors for custom integrations [S11] |
| Sprinto | Each integration page tabulates permission, resource, purpose and the checks it supports [P3] | Last sync and errors; manual sync button [P1][P15] |
| Thoropass | Scoping call marks in-scope systems; disable monitors for unused services [T3] | Connection errors shown per monitor on the control; weekly digest to watchers [T3][T5] |
| Scrut | Region specific base URL in the guide [C3] | "Connected" flag after submit [C2] |
| Hyperproof | Connect an app once, then create many Hypersyncs [H1] | Static IPs published; SDK health hooks [H5] |

## 3.8 Question 7: how collectors are built

| Platform | What is public |
|---|---|
| Vanta | An "Automations" team owns the integrations platform for 400+ integrations [V16]. Partner integrations need a server side OAuth client and a sync job per customer; tokens last one hour [V7]. The agent is a trimmed osquery [V4]. Backend language not public (unverified) |
| Drata | Agent in TypeScript on Electron with osquery (C++) [D7][O2]. Tests are JSON with JSON path conditions; an AI pipeline built on Vellum and Airflow wrote over 1,000 cloud tests, stored in DynamoDB, each reviewed by auditors [D23]. HRIS through Merge [D14]. A job listing names NestJS and TypeScript [D26] (third party, unverified) |
| Secureframe | Agent on Fleet, whose code is mostly Go [S6][O1]. HRIS through Finch [S8] |
| Hyperproof | Node.js 22 and TypeScript SDK; JSONata transforms; outbound calls are guarded against server side request forgery [H5]. Many Hypersyncs through Merge [H6] |
| Sprinto | Session based ingestion with 409 on a second session and 429 with Retry-After [P11]. Language not public |
| ServiceNow | Indicators run on schedules through dedicated nightly queues [N2]; the Jamf connector supports delta sync [N4] |

No vendor states that its cloud collectors are written in Go. Fleet, which Secureframe builds on, is
the one large Go code base in this space [O1]. Nothing here argues against Verity's Go collector plan
in `01-evidence-model.md` section 1.5.

## 3.9 Question 8: counts and categories Verity's catalogue does not cover

**Counts are marketing figures.** Vanta 400+ [V15], Secureframe 300+ [S13], Sprinto 300+ [P15],
Hyperproof 200+ [H7], Drata "hundreds" across 28 categories [D25], Scrut about 157 entries [C1],
Thoropass not stated, ServiceNow a whole platform. Many counts include unified API long tails (Merge,
Finch), so they are not like for like with Verity's hand built connectors.

Categories competitors list that `docs/architecture/integrations.md` (Phase 2 and Phase 3) does not:

| Category | Who lists it | Verity controls it would help |
|---|---|---|
| HRIS (BambooHR, Workday, HiBob, Rippling, ADP, Personio) | All SaaS vendors [V14][D25][S8][C1] | Joiner, leaver and screening controls; start and end dates for access reviews |
| Device management (Jamf, Kandji or Iru, Intune, JumpCloud, Hexnode) | Vanta, Drata, Secureframe, Sprinto, Scrut [V5][D8][S7][P5][C1] | Endpoint encryption, screen lock, patching |
| Own endpoint agent | Vanta, Drata, Secureframe, Sprinto, Scrut [V4][D6][S5][P4][C5] | Same, for teams with no MDM |
| Endpoint detection and response (CrowdStrike, SentinelOne, Defender) | Secureframe, Scrut, Vanta [S7][C1] | Malware protection |
| Background checks (Checkr, Certn) | Vanta, Drata, Secureframe, Sprinto, Scrut [V14][D16][S9][P7][C1] | Screening |
| Security awareness training (KnowBe4 and others) | Drata, Scrut, plus built-in training at Vanta, Drata, Secureframe [D18][C1][V12][S8] | Awareness and training |
| Policy import (Confluence, BambooHR) | Drata, Scrut [D25][C1] | Policy management |
| User access review across SaaS apps | Drata (a long list) [D25] | Periodic access review |
| Other SSO providers (JumpCloud, OneLogin, Ping, Auth0, Duo) | Drata [D5] | Sign in and identity controls |
| Cloud storage, data export, cyber insurance, ATS, CRM, accounting | Drata, Hyperproof [D25][H6] | Mostly reporting, low control value |

## 3.10 What Verity should adopt

1. **Vendor app with admin consent for Entra and Google; an Okta catalogue API Service Integration
   rather than a personal SSWS token** (Vanta, Scrut) [V1][V3][C2]. This matches the "vendor app"
   credential type in `02-integration-model.md` section 2.2.
2. **Validate the grant, both ways.** Flag missing scopes and extra scopes after connecting, as Vanta
   does for Okta [V1]. A missing scope is `error` for the checks that need it, never `fail`.
3. **A prerequisites checklist and a recommended connection order** in the setup guide (Vanta)
   [V10][V11]. Put it in guided onboarding: identity and cloud first, then devices and code, then HR.
4. **Health per sync step, not one flag** (Drata) [D24], and show "could not connect" next to the
   check on the control page, apart from violations (Thoropass) [T5].
5. **State empty population and threshold in every check** (Hyperproof's empty proof behaviour and
   pass threshold) [H2]. This is AUTHORING rule 4 made visible to the customer.
6. **A warning state before failing for dated evidence** (Secureframe "At Risk", Sprinto "Due" and
   "Critical") [S10][P9].
7. **Exclusions need a reason, a limited set of roles and a review date**; accept source tags as an
   exclusion input (Drata, Thoropass Data Rules) [D20][D22][T6].
8. **HRIS outranks the IdP for start and end dates** (Vanta, Drata) [V11][D13]. Decide whether to buy
   breadth through a unified API (Merge, Finch); that is a new dependency and needs an ADR.
9. **An osquery based agent for teams with no MDM, with its code or query list public** (Drata open
   source, Vanta's local schedule command) [D7][V4]. Fleet (Go, MIT) is a possible base [O1]; an ADR
   decides build or adopt.
10. **Personal devices by policy, exclusion and upload** (Drata) [D11][D12]: the person stays in scope,
    the device check is excluded with a reason, and a document or screenshot fills the artifact.
11. **A push API with full state or session semantics** so deletions are seen and a sync is atomic
    (Vanta, Sprinto), and upsert by id (Drata) [V7][P11][D19].
12. **A separate auditor surface** (Vanta's audit API, Sprinto's Audit Partner API) [V7][P14].

## 3.11 Where Verity can differ and be better

1. **Objective level traceability.** Only ServiceNow shows assessment objectives under a control, and
   only for NIST [N1]. Verity already has 591 objectives with methods (examine, interview, observe,
   test) for SOC 2 and ISO 27001. Show, per check, which objectives and artifacts it fills and which
   stay with a person. No SaaS competitor shows this publicly.
2. **Honest partial coverage.** Secureframe treats a control as operating when all its tests pass
   [S10], and Drata's own guidance concedes policy-only readiness can mislead (section 4 of the
   sufficiency note). Verity's `coverage: partial` with a rationale can say, on the control page, what
   still needs a document or a person.
3. **"Could not check" and "insufficient information" as first class results.** Competitors show
   unhealthy connections [D24] and Hyperproof lets an empty proof pass if configured [H2]. Verity can
   refuse to pass any check that cannot see the whole population (AUTHORING rule 3).
4. **Own words content, published.** Drata's tests were drafted by an LLM and then reviewed [D23].
   Verity's checks are hand written with population, predicate and period. Publish the generated
   `check-catalogue.md` so buyers and auditors can read every rule before they connect anything.
5. **Sign in, joiners and leavers, and evidence in one setup through Keycloak.** Vanta, Secureframe,
   Scrut (Okta), Hyperproof and ServiceNow keep sign in separate [V1][S3][C3][H8][N7]. Drata comes
   closest for Okta only [D1]. Verity can run one connect flow per provider that sets up Keycloak
   sign in, the leaver feed and the read only evidence app, while keeping two credentials as
   `docs/runbooks/sso-providers.md` section 7 requires.
6. **Least privilege by default, labelled per check.** Offer a base scope set and show which checks
   each extra permission unlocks (Sprinto documents this in tables [P3]; Verity can do it in the
   connect screen). Avoid Super Administrator style grants where a narrower role works [V1].
7. **Versioned checks.** Vanta's custom tests cannot be edited once saved [V8]. Verity's sealed,
   versioned content can show which rule version produced each result.
8. **An open agent from day one**, rather than opening it years later [D6].

## 3.12 Gaps in this research

- Thoropass keeps most integration detail behind its login. Its section is thin.
- Scrut's custom integration API and Sprinto's agent internals were not found.
- Vanta's guidance on personal devices and its backend language were not found.
- ServiceNow's identity evidence path for IRM was not documented in the pages read.
- Entra ID details were found only for Vanta and Drata.
- Integration counts are vendor claims and change often.
- Several Vanta MDM, custom test and Secureframe API points came from search summaries of the cited
  pages ([V5], [V6], [V9], [S12]); open them before building on those details.

## 3.13 Sources

Vanta
- [V1] Okta integration guide: https://help.vanta.com/en/articles/15082003-okta-integration-guide
- [V2] Google Workspace integration guide: https://help.vanta.com/en/articles/14977969-google-workspace-integration-guide
- [V3] Connecting Vanta and Microsoft Entra: https://help.vanta.com/en/articles/11345655-connecting-vanta-microsoft-entra
- [V4] What the device monitor queries: https://help.vanta.com/en/articles/11345405-what-information-does-the-vanta-device-monitor-query
- [V5] Connecting Jamf Pro: https://help.vanta.com/en/articles/11345770-connecting-vanta-jamf-pro
- [V6] Connecting Intune: https://help.vanta.com/en/articles/11345786-connecting-vanta-microsoft-endpoint-manager-intune-mdm
- [V7] Integrations concepts (developer docs): https://developer.vanta.com/docs/concepts/integrations
- [V8] Tests concepts (developer docs): https://developer.vanta.com/docs/concepts/tests
- [V9] Creating custom tests: https://help.vanta.com/en/articles/11345522-creating-custom-tests
- [V10] Integration prerequisites checklist: https://help.vanta.com/en/articles/15292833-before-you-connect-integration-prerequisites-checklist
- [V11] What to connect first: https://help.vanta.com/en/articles/15878233-integration-journey-what-to-connect-first-in-vanta
- [V12] Personnel tasks: https://help.vanta.com/en/articles/11345600-personnel-tasks
- [V13] Offboarding personnel: https://help.vanta.com/en/articles/11345609-offboarding-personnel
- [V14] Integrations directory: https://www.vanta.com/integrations
- [V15] Vanta compared with Drata (count claim): https://vanta.com/compare/drata
- [V16] Integrations platform job listing: https://www.purpose.jobs/discover/companies/vanta-com/jobs/90321370-senior-backend-software-engineer-integrations-platform

Drata
- [D1] Okta identity guide: https://help.drata.com/en/articles/5608136-okta-integration-guide-identity-management-provider
- [D2] Okta user access review guide: https://help.drata.com/en/articles/8542832-okta-integration-guide-user-access-review
- [D3] Microsoft 365 guide: https://help.drata.com/en/articles/4797766-microsoft-365-integration-guide
- [D4] Google Workspace guide: https://help.drata.com/en/articles/4663303-google-workspace-integration-guide
- [D5] Single sign on connection: https://help.drata.com/en/articles/5209416-single-sign-on-connection
- [D6] How the Drata Agent works: https://help.drata.com/en/articles/4742932-how-does-the-drata-agent-work
- [D7] Drata Agent source: https://github.com/drata/drata-agent
- [D8] Multiple MDM support: https://help.drata.com/en/articles/5990364-multiple-mdm-support
- [D9] Jamf guide: https://help.drata.com/en/articles/5456409-jamf-integration-guide
- [D10] Intune for Mac guide: https://help.drata.com/en/articles/5899473-microsoft-intune-integration-guide-mac-devices
- [D11] BYOD and audits: https://help.drata.com/en/articles/6297649-how-do-bring-your-own-device-byod-devices-affect-my-audit
- [D12] Personnel exclusions: https://help.drata.com/en/articles/13521706-personnel-exclusions
- [D13] Connect your HRIS: https://help.drata.com/en/articles/8699680-connect-your-hris-to-drata
- [D14] Merge case study on Drata: https://merge.dev/case-studies/how-drata-increases-customer-value-and-spends-80-less-time-managing-integrations
- [D15] Multiple HRIS support: https://drata.com/blog/introducing-multiple-hris-support
- [D16] Checkr guide: https://help.drata.com/en/articles/5409416-checkr-integration-guide
- [D17] Certn guide: https://help.drata.com/en/articles/4972294-certn-integration-guide-background-check
- [D18] My Drata overview: https://help.drata.com/en/articles/13442440-my-drata-overview-complete-your-personal-compliance-tasks-new-experience
- [D19] Custom connections and tests: https://help.drata.com/en/articles/11117161-custom-connections-and-tests
- [D20] Exclude findings from tests: https://help.drata.com/en/articles/13521711-exclude-findings-from-tests
- [D21] Exclusions compared with disabling a test: https://help.drata.com/en/articles/4939181-exclusions-vs-disabling-a-test
- [D22] Exclusion tags in Azure: https://help.drata.com/en/articles/5352047-exclusion-tags-within-azure
- [D23] Building AI compliance tests (engineering blog): https://drata.com/blog/building-ai-compliance-tests
- [D24] Understanding connections: https://help.drata.com/en/articles/13273728-understanding-connections-in-drata
- [D25] Integrations directory: https://drata.com/platform/integrations?tab=all
- [D26] Job listing naming the stack: https://builtin.com/job/staff-software-engineer-remote/2442002

Secureframe
- [S1] Integrations FAQ (Okta): https://support.secureframe.com/en/articles/15111609-faqs-integrations-beyond-core-apps-sync-connections-and-vendor-specific-setup
- [S2] Google Workspace permissions: https://support.secureframe.com/en/articles/15111500-permissions-google-workspace
- [S3] Logging in with an IdP: https://support.secureframe.com/en/articles/15111019-logging-into-secureframe-with-an-idp-saml-oidc
- [S4] SCIM provisioning: https://support.secureframe.com/en/articles/15111037-scim-provisioning
- [S5] Agent fields pulled: https://support.secureframe.com/en/articles/15111648-secureframe-agent-fields-pulled
- [S6] Agent and Fleet: https://support.secureframe.com/en/articles/15111670-secureframe-agent-fleet-logo-partnership
- [S7] Supported MDMs: https://support.secureframe.com/en/articles/15111590-supported-mdms-and-their-endpoint-security-capabilities
- [S8] Personnel management FAQ: https://support.secureframe.com/en/articles/15111170-faqs-personnel-management-hris-onboarding-and-common-scenarios
- [S9] Background checks with Checkr: https://support.secureframe.com/en/articles/15111161-integrate-and-initiate-background-checks-checkr
- [S10] Tests page overview: https://support.secureframe.com/en/articles/15111248-tests-page-overview-test-types-uploading-evidence-filtering
- [S11] Create custom integrations: https://support.secureframe.com/en/articles/15111548-create-custom-integrations
- [S12] API and custom integrations: https://secureframe.com/features/api
- [S13] Integrations page: https://secureframe.com/integrations

Sprinto
- [P1] Okta integration: https://docs.sprinto.com/integrations/overview/okta-integration
- [P2] Google Workspace employee groups: https://docs.sprinto.com/integrations/overview/google-workspace-employee-groups-integration
- [P3] Permissions and resource usage: https://docs.sprinto.com/integrations/overview/permissions-and-resource-usage-in-sprinto-integrations
- [P4] Staff devices, how it works: https://docs.sprinto.com/data-library/staff-devices/how-it-works
- [P5] Extended checks in MDM tools: https://docs.sprinto.com/monitors/extended-checks-in-mdm-tool-comms
- [P6] Monitor device compliance checks: https://docs.sprinto.com/data-library/staff-devices/dashboard-actions/monitor-device-compliance-checks
- [P7] People, how it works: https://docs.sprinto.com/data-library/people/how-it-works
- [P8] Certn integration: https://docs.sprinto.com/integrations/overview/certn-integtation
- [P9] Create automated checks: https://docs.sprinto.com/monitoring/dashboard-actions/create-automated-checks
- [P10] June 2026 product update: https://docs.sprinto.com/product-updates/june-2026
- [P11] Custom integrations: https://docs.sprinto.com/settings/custom-integrations
- [P12] Upload evidence API: https://docs.sprinto.com/api-reference/upload-evidence-api
- [P13] Evidence for a workflow check: https://docs.sprinto.com/api-reference/sprinto-cookbooks/add-evidence-for-workflow-check
- [P14] Audit partner integration: https://docs.sprinto.com/settings/audit-partner-integration
- [P15] Home page (count): https://sprinto.com/

Thoropass
- [T1] Laika is now Thoropass: https://thoropass.com/blog/laika-is-now-thoropass
- [T3] Monitors and collectors: https://help.thoropass.com/en/articles/6295763-how-do-i-set-up-monitors-and-collectors
- [T4] What are integrations: https://help.thoropass.com/en/articles/5967185-what-are-integrations
- [T5] Connected tools: https://help.thoropass.com/en/articles/12390004-what-are-connected-tools
- [T6] Data rules: https://help.thoropass.com/en/articles/10261249-thoropass-data-rules
- [T7] Asset intelligence: https://help.thoropass.com/en/articles/11887300-asset-intelligence
- [T8] MCP server: https://help.thoropass.com/en/articles/16976070-connecting-to-the-thoropass-mcp-server
- [T9] Okta catalogue listing: https://www.okta.com/integrations/thoropass/
- [T10] Vetty partner listing: https://thoropass.partnerpage.io/tech-partners/vetty and Checkr partner page: https://checkr.com/company/partners/thoropass

Scrut
- [C1] Integrations overview: https://help.scrut.io/docs/integrations-overview
- [C2] Okta (IdP): https://help.scrut.io/docs/integrating-okta-idp
- [C3] Okta (SSO): https://help.scrut.io/docs/integrating-okta
- [C4] Google Workspace: https://help.scrut.io/docs/integrating-google-workspace
- [C5] Scrut Agent for macOS: https://help.scrut.io/docs/scrut-agent-installation-guide-for-macos
- [C6] Kolide: https://help.scrut.io/docs/integrating-kolide

Hyperproof
- [H1] Okta proof types and permissions: https://intercom.help/hyperproofio/en/articles/14303959-okta-proof-types-and-permissions
- [H2] Creating an automated control test: https://help.hyperproof.app/en/articles/14303789-creating-and-running-an-automated-control-test
- [H3] Control testing status: https://help.hyperproof.app/en/articles/14303635-control-maintenance-testing
- [H4] What Hypersync proof looks like: https://help.hyperproof.app/en/articles/14303904-what-does-hypersync-proof-look-like
- [H5] Hypersync SDK (README, docs 002 and 003): https://github.com/Hyperproof/hypersync-sdk
- [H6] HRIS apps and proof types: https://help.hyperproof.app/en/articles/14304202-hris-apps-and-proof-types
- [H7] Integrations page: https://hyperproof.io/integrations/
- [H8] Okta catalogue listing: https://www.okta.com/integrations/hyperproof/

ServiceNow
- [N1] Controls and assessment objectives in CAM: https://www.servicenow.com/docs/r/aUYojakX2btrvRdtS_~doA/ByMCHZhSfEYZMACy~sxKLQ
- [N2] Manage indicators: https://www.servicenow.com/docs/r/governance-risk-compliance/policy-and-compliance-management/manage-indicators-policy-comp.html
- [N3] Service Graph Connector for Intune: https://www.servicenow.com/docs/r/servicenow-platform/service-graph-connectors/cmdb-integration-intune.html
- [N4] Service Graph Connector for Jamf: https://www.servicenow.com/docs/r/servicenow-platform/service-graph-connectors/cmdb-integration-jamf.html
- [N5] Configuration Compliance data sheet: https://www.servicenow.com/content/dam/servicenow-assets/public/en-us/doc-type/resource-center/data-sheet/ds-configuration-compliance.pdf
- [N6] CAM product page: https://www.servicenow.com/products/continuous-authorization-monitoring.html
- [N7] Entra ID and user provisioning (KB0635951): https://support.servicenow.com/kb?id=kb_article_view&sysparm_article=KB0635951

Other
- [O1] Fleet source (MIT; language breakdown from the GitHub API, mostly Go): https://github.com/fleetdm/fleet
- [O2] osquery source (C++): https://github.com/osquery/osquery
- [O3] Third-party report that Okta's read-only admin cannot read roles: https://developer.sailpoint.com/discuss/t/iiq-8-4p1-okta-integration-read-only-task-errors/199714
