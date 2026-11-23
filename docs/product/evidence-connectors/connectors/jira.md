# Jira (Jira Cloud and Jira Service Management)

| | |
|---|---|
| Capabilities | ticketing |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | Recommended first: an Atlassian service account with a scoped API token, read only scopes, called through `api.atlassian.com`. Later: Verity's OAuth 2.0 (3LO) app with granular read scopes and `offline_access` |
| Shares setup with | Nothing. Atlassian is not a Verity sign in provider |
| Go library | No official Atlassian Go SDK found (unverified that none exists) [J18]. Community: `github.com/ctreminiom/go-atlassian` (has Jira v3 and service management clients, OAuth 2.0) [J19], `github.com/andygrunwald/go-jira` [J20]. Recommended: plain `net/http` against the REST v3 and `servicedeskapi` specs, because the surface is small and rate limit headers need direct handling |

Shared definitions, feasibility matrix and owner decisions: [operations-checks.md](operations-checks.md).

## 1. What it proves

Jira is where many customers approve changes, request access, take security reports and track the work
that fixes findings. The connector proves facts that never pass through Verity:

- a change ticket was approved **before** it was released, and not by the person who asked for it or
  did it (SD-01, IAM-09);
- an emergency change was reviewed by someone else within the window after it went out (SD-04);
- an access request was approved by someone other than the requester, and by an owner for privileged
  access (IAM-01, IAM-09), and, joined with the identity provider, that each grant matched an approved
  request (`tickets.access_requests_approved`);
- a security report got its first answer in time (CS-03);
- findings tracked in Jira closed by their due date, including those closed late (GOV-08, LM-05);
- every incident raised in Jira reached Verity's incident register (LM-04, LM-07).

What it does **not** prove:

| Trap | Why it is not proof | What the check does |
|---|---|---|
| A ticket key in a pull request title | Mentioning a ticket is not an approval (continuous compliance plan, section 7) | Only an approval recorded on the ticket, dated before release, counts |
| A status called "Approved" | Anyone with the transition permission may set it, unless the workflow restricts who can | The approver's identity and independence are checked; whether the workflow limits who may approve is a design question a person answers (SD-01.A) |
| A transition made by an automation rule | No person decided | Transitions made by an app or automation actor do not count as approval. The user object's `accountType` is `atlassian`, `app`, `customer` or `unknown` [J6]. A rule runs as the "Automation for Jira" user by default, but its actor can be set to a real person, and then the history shows that person [J25] (corrected 2026-11-23: was "actor type: unverified field"; account type alone cannot catch a rule that runs as a person, see section 10) |
| Jira shows a ticket was released | Jira does not deploy | Release time comes from the ticket's mapped status; the deployment itself is `ci.deployment_history_recorded` |
| Every change has a ticket | Jira cannot see code that changed without one | `tickets.changes_linked` starts from merged code (version control) and looks for the ticket |
| An access request was approved | Approval is not the grant | The grant comes from the identity provider (identity research) |
| A Jira incident ticket | Not the incident record the plan requires | Reconciled against Verity's register (`tickets.incidents_registered`) |

Where Verity already holds the evidence: remediation raised inside Verity is judged by
`verity.tasks.remediation_in_sla`; Jira adds the findings that live only in Jira and the ones closed
late. See [operations-checks.md](operations-checks.md) section 5.

## 2. Connecting: method, credentials and permissions

### 2.1 Two methods

| | Service account, scoped API token (recommended first) | Verity OAuth 2.0 (3LO) app |
|---|---|---|
| Who creates it | A customer org admin creates the service account and its token [J9] | Verity creates one app in the developer console; a customer user consents [J1] |
| Credential | Scoped API token, basic auth against `https://api.atlassian.com/ex/jira/{cloudId}` [J8] | Authorization code grant; `offline_access` gives a rotating refresh token [J1] [J2] |
| Lifetime | 1 to 365 days, chosen at creation; default one year for tokens created after 15 December 2024 [J8] | Refresh token expires after 90 days unused [J1]; each refresh issues a new one and disables the old [J2]. Access token lifetime is given by `expires_in` (value unverified: Atlassian documents the field but publishes no number for 3LO; the service account client credentials page gives 60 minutes) [J1] [J10] |
| Rate limits | Token traffic is outside the points quota; burst limits only (100 GET and 100 POST requests per second per tenant per endpoint) [J14] | From 2 March 2026, one quota of 65,000 points per hour shared across **all** tenants of the app, unless Atlassian assigns a per tenant tier after review [J14] (confirmed 2026-11-23: applies to Forge, Connect and 3LO apps, resets at the top of each UTC hour; the per tenant tier ranges from 65,000 on Free to at most 500,000 points per hour) |
| Vendor duties | None | Turn on sharing for other sites; an unreviewed app shows users a warning; apps that store personal data must report account ids every cycle (`POST https://api.atlassian.com/app/report-accounts/`, default 7 days) [J1] [J3] |
| Seat | Service accounts do not count toward Jira user limits; 5 free, more with Atlassian Guard (whether Guard is needed for the first 5 stays unverified: the page says 5 are free but its "who can do this" box lists only Guard Standard and Enterprise) [J9] | Acts as the consenting user, so it sees what that user sees |
| Customer effort | Create the account, give it project access, create the token, paste it | Click connect, consent |

Recommendation: service account with a scoped API token first. A shared 65,000 point hourly quota
across every Verity customer is a real ceiling for a daily changelog read, and the token does not
depend on one employee. Move to the OAuth app when Atlassian grants a per tenant tier (owner decision 1).
Service accounts can also use OAuth 2.0 client credentials (access token valid 60 minutes) [J10]; whether
that traffic counts against the app quota or as token traffic is unverified (neither the rate limiting
page nor the credential page says) [J14] [J10], so it is not the first choice.

A classic (unscoped) API token used with the site URL also works but cannot be limited to read; it is
offered only as a fallback with a warning.

### 2.2 Scopes and permissions

Granular scopes are preferred because the classic scopes force an admin scope for two reads: audit
records and workflow search need `manage:jira-configuration` in classic form [J6]. All granular scopes
are marked beta in the spec [J6] [J7] (confirmed: state `Beta` on every granular scope set). Atlassian's
scopes page recommends classic scopes and granular ones only where classic cannot be used [J4]. Whether
classic and granular scopes can be mixed in one app is unverified (no official statement found).

| Scope (granular) | Read only | Needed for (check keys) | Who can grant |
|---|---|---|---|
| `read:issue:jira`, `read:issue-details:jira`, `read:issue-meta:jira`, `read:field:jira`, `read:field-configuration:jira`, `read:status:jira`, `read:avatar:jira` | yes | every `tickets.*` check (search and issue fields) | org admin (token) or consenting user |
| `read:issue.changelog:jira` | yes | `tickets.changes_approved_before_release`, `tickets.emergency_changes_reviewed`, `tickets.changes_linked`, `tickets.remediation_tracked` (status history and times) | same |
| `read:issue.remote-link:jira`, `read:issue-link-type:jira` | yes | `tickets.changes_linked` (links to pull requests) | same |
| `read:comment:jira` | yes | `tickets.security_reports_answered` without JSM SLAs (first agent reply) | same |
| `read:project:jira`, `read:workflow:jira` | yes | scope discovery, status mapping screen | same. Corrected 2026-11-23: `workflows/search` and `statuses/search` also need Administer Jira or Administer projects (View read only workflow is enough for project scoped workflows) [J6]; with Browse projects only, read statuses from `GET /rest/api/3/project/{projectIdOrKey}/statuses` (`read:status:jira`, `read:issue-status:jira`, `read:issue-type:jira`) [J6] |
| `read:user:jira`, `read:group:jira` | yes | approver identity and owner group checks (`tickets.access_approver_independent`) | same |
| `read:request:jira-service-management`, `read:servicedesk:jira-service-management`, `read:requesttype:jira-service-management` | yes | JSM request types for access requests, security reports, incidents | same |
| `read:request.approval:jira-service-management` | yes | JSM approvals for change and access checks | same |
| `read:request.sla:jira-service-management` | yes | `tickets.security_reports_answered`, `tickets.remediation_tracked` (JSM SLA cycles) | same |
| `read:audit-log:jira` | yes | optional: workflow and permission changes shown next to SD-01 results | same, **and** the account needs the Administer Jira global permission [J6] |

Classic equivalents, for the OAuth app if granular scopes cannot be used: `read:jira-work`,
`read:jira-user`, `read:servicedesk-request` [J4] [J5]; no read only classic scope reaches audit records.
Note the JSM SLA endpoint is listed under `read:jira-work` in classic form, not the service desk scope
[J7].

Product permissions the service account needs inside Jira:

| Permission | Needed for | Note |
|---|---|---|
| Browse projects on each in scope project | all checks | the population is only what this account can browse, so scope is per project |
| Permission to view the customer request | JSM approvals [J7] | |
| Agent on each in scope service desk | JSM SLA endpoint [J7] | an agent seat is a paid JSM licence |
| Administer Jira (global) | audit records only [J6] | optional; off by default because it is an admin permission even if the token is read only |

### 2.3 Plan and edition requirements

| Feature | Requirement | Source |
|---|---|---|
| Jira audit log | Not available when all Jira apps are on Free; from Standard | [J13] [J15] |
| JSM change management (change work type, queues, calendar), major incidents, post incident reviews | Premium or Enterprise since 16 October 2024 | [J16] |
| JSM incident work type and queues | Free and Standard keep them | [J16] |
| JSM approvals and SLAs on Free | unverified: the official pricing page did not render a per plan feature table; it confirms Free allows 3 agents, which caps the agent seats the SLA endpoint needs | [J26] |
| Service accounts beyond 5 | Atlassian Guard Standard (250) or Enterprise (1,000) | [J9] |

A missing plan feature is reported once per connection ("Jira audit log is not available on the Free
plan"), not per check.

## 3. Customer setup guide (draft)

1. In Atlassian Administration, open **Directory**, then **Service accounts**, and create one named
   "Verity (read only)".
2. Give it access to Jira, and to Jira Service Management if you use it. Add it to a group that can
   browse each project Verity should check. For JSM SLAs, make it an agent on those service desks.
3. Create an **API token with scopes** for the service account. Pick Jira and, if used, Jira Service
   Management, and tick only the read scopes Verity lists on the connect screen. Set the expiry, up to
   one year, and note the date.
4. In Verity, open **Connections**, choose **Jira**, and paste your site address, the service account's
   email, the token and its expiry date.
5. Choose the projects in scope. For each, tell Verity what the tickets mean: which work types are
   changes, emergency changes, access requests, security reports, incidents or findings, and which
   statuses mean approved and released. Verity shows a preview of the tickets each choice matches.
6. Run the test. Each check shows ready, missing permission or needs mapping.

Verity never creates, edits or comments on tickets.

## 4. What Verity collects

Base for tokens and the app: `https://api.atlassian.com/ex/jira/{cloudId}` [J1] [J8].

| Resource | API | Fields kept | Paging and rate limits | Provider retention |
|---|---|---|---|---|
| Projects | `GET /rest/api/3/project/search` [J6] | id, key, name, type | `startAt` paging | while the project exists |
| Workflows and statuses | `GET /rest/api/3/workflows/search`, `GET /rest/api/3/statuses/search` [J6]. Old `GET /rest/api/3/workflow/search` removed 1 June 2026 [J6]. Both need Administer Jira or Administer projects; `GET /rest/api/3/project/{projectIdOrKey}/statuses` needs only Browse projects [J6] | status ids, names, categories, transitions | `startAt`, `maxResults` (statuses default 200) | |
| Tickets in scope | `GET` or `POST /rest/api/3/search/jql` [J6]. The old `/rest/api/3/search` is marked deprecated and "currently being removed" under changelog entry CHANGE-2046 [J6]; the removal date is unverified (the changelog entry did not load, and community posts give conflicting 2025 dates) | id, key, project, work type, status, created, resolution date, reporter, assignee, mapped fields (impact, test, rollback, severity, beneficiary, system, due date), labels | `nextPageToken`, absent on the last page; up to 5,000 per page when only ids are asked for [J6] | until deleted |
| History | `POST /rest/api/3/changelog/bulkfetch` (up to 1,000 issues, 10 fields per call) or `GET /rest/api/3/issue/{id}/changelog` [J6] | per change: author account id, created, field, from, to | `nextPageToken`; one bulk call replaces up to 1,000 single calls | kept with the issue |
| Links to code | `GET /rest/api/3/issue/{id}/remotelink` [J6] | URL, title, relationship | per issue | with the issue |
| Comments | `GET /rest/api/3/issue/{id}/comment` [J6] | author, created, public or internal | | with the issue |
| JSM request types | `GET /rest/servicedeskapi/servicedesk`, `/servicedesk/{id}/requesttype` [J7] | ids, names | `start`, `limit` | |
| JSM approvals | `GET /rest/servicedeskapi/request/{issueIdOrKey}/approval` [J7] | name, final decision, each approver and decision, created and completed dates | per ticket | with the ticket |
| JSM SLAs | `GET /rest/servicedeskapi/request/{issueIdOrKey}/sla` [J7] | SLA name, ongoing cycle (start, breach time, breached, paused), completed cycles (start, stop, breached, goal, elapsed) | per ticket | with the ticket |
| Audit records (optional) | `GET /rest/api/3/auditing/record` [J6] | time, author, category, summary, changed values | `offset`, `limit` (default 1,000), `from`, `to` | configurable in audit log settings; the options and the default are unverified (the Cloud page gives only "6 months" as an example) [J13] |

Population note: `GET /rest/servicedeskapi/request` returns only requests the calling user owns, joined
or shares through an organisation [J7]. It is never used for a population. Tickets are found by JQL and
then read per ticket.

Development information (pull requests and commits shown in Jira's development panel) has no public
read API: the documented development information API is for tools that write it [J12]. Links between
tickets and code therefore come from the version control side and from remote links.

Rate limits: 429 responses carry `Retry-After`, `X-RateLimit-Limit`, `X-RateLimit-Remaining`,
`X-RateLimit-Reset` and `RateLimit-Reason` [J14].

## 5. Checks

Period: every check runs daily over a rolling 30 day window of tickets that changed state, so the daily
results are the history for a Type 2 window (evidence model rule 5). Approval rules used by several
checks:

- **Approval** is, per mapped project, one of: a JSM approval whose final decision is approved (approver
  and time from the approval) [J7]; a transition into a mapped approved status (approver is the
  changelog author, time is the changelog time) [J6]; or a mapped approver field set (time from the
  changelog). The last approval before release counts. Limit (added 2026-11-23): an automation rule
  whose actor is set to a person records its transitions under that person [J25], so a status
  approval made by such a rule looks like a human approval; see section 10.
- **Release** is the first transition into a mapped released status.
- **Independent** means the approver's account id differs from the reporter's, the assignee's at
  release, and any mapped implementer field.

| Check | Population | Predicate | Pass, fail, error, insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|
| `tickets.changes_linked` (existing) | Production changes from version control (merged to the default branch in scope, last 30 days) | Each references a change ticket (key in title, branch or commits, or a remote link to the change) in a mapped project, and that ticket has an approval dated before the merge | pass: all; fail: any without a ticket or approved only after merge; error: Jira or version control unreadable; insufficient: change population truncated, or a referenced ticket not browsable | daily | change, ticket key, approval time and approver | SD-01 partial, SD-14 partial (existing rationales) |
| `tickets.access_requests_approved` (existing) | Grants in the identity provider in the period (identity research), against access request tickets resolved in the period | Each grant matches an approved request for the same person and system, approved before the grant | Jira alone: insufficient (no grant side). With an identity provider: pass, fail as stated; error on either side unreadable | daily | grants, matched requests, unmatched grants | IAM-01 (propose partial, see operations-checks section 2) |
| `tickets.remediation_tracked` (existing) | Tickets the customer marks as findings or postmortem actions, open or closed in the period | Each closed by its due time: JSM SLA cycle not breached, or resolution date on or before the due date; open ones not past due | pass: none late or overdue; fail: list; error: unreadable; insufficient: no mapping, or no due date or SLA on a ticket. Empty: insufficient, the dated nil return stays with people | daily | tickets with due, resolved, SLA state | GOV-08 partial; propose LM-05 partial |
| NEW `tickets.changes_approved_before_release` | Change tickets in mapped projects that reached a released status in the last 30 days | Approval before release, approver independent, mapped required fields (impact, testing, rollback) not empty | pass: all; fail: any unapproved, approved late, self approved or missing a required field; error: scope or permission missing; insufficient: mapping not set, history truncated. Empty: insufficient (no released change tickets does not show no changes happened) | daily | per ticket: approval, approver, release time, required fields | SD-01 partial, IAM-09 partial |
| NEW `tickets.emergency_changes_reviewed` | Change tickets carrying the mapped emergency marker, released in the last 30 days, whose review window has closed | A review approval (as above) by someone other than the implementer and requester, dated by the end of the next business day after release in the workspace time zone (SD-04 parameter `retrospective_review_window`) | pass: all; fail: missing, late or self review; error; insufficient: no emergency marker mapped. Tickets still inside their window are listed as pending, not judged. Empty: pass only with a marker mapped, and the result says emergency changes without tickets are `vcs.unreviewed_merges_recorded` | daily | emergency tickets, release and review times, reviewer | SD-04 partial |
| NEW `tickets.access_approver_independent` | Access request tickets (mapped JSM request types or work types) approved or resolved in the last 30 days | At least one approving decision from someone who is neither the requester nor the beneficiary; for request types marked privileged, an approver in the mapped system owner group | pass; fail: self approval, beneficiary approval, privileged request without an owner's approval; error; insufficient: no beneficiary field mapped where requests are raised on someone's behalf | daily | requests, approvers, owner group used | IAM-01 partial, IAM-09 partial |
| NEW `tickets.security_reports_answered` | Requests of the mapped security report types created in the last 30 days, plus any still open | The mapped first response SLA has no breached cycle; without JSM, the first public comment or transition by someone other than the reporter came within the set time (default 2 business days, owner decision 6). Closed ones have a resolution | pass; fail: late or no response, closed without a resolution; error; insufficient: no SLA or response rule mapped. Empty: insufficient, the dated nil return stays with people | daily | reports, first response time, resolution | CS-03 partial |
| NEW `tickets.incidents_registered` | Incident tickets (mapped JSM incident work type, or work types and labels) created in the period, filtered to security incidents by the mapped category | Each has a Verity register entry (synced with `source` jira and the issue id, or linked by a person) or a recorded "not an incident" decision | pass; fail: list of unregistered incidents; error; insufficient: mapping not set. Empty: insufficient | daily | incident tickets and the matching register entries | LM-07 partial, LM-04 partial |

Full definitions of the new checks: [operations-checks.md](operations-checks.md) section 3.1.

## 6. Artifacts and objectives it fills

| Artifact | Objectives | Control | Change |
|---|---|---|---|
| `change-requests-with-approval-for-a` | SD-01.B, C, D, E | SD-01 | person + `tickets.changes_linked` + new `tickets.changes_approved_before_release` (both partial) |
| `change-records-linking-request-review-and` | SD-14.B, C, D, E | SD-14 | person + `tickets.changes_linked` now implemented (partial). SD-14.D retention: Jira keeps tickets until deleted, Verity keeps the observation |
| `emergency-changes-with-their-after-the` | SD-04.B, C, D | SD-04 | person + `vcs.unreviewed_merges_recorded` + new `tickets.emergency_changes_reviewed` (partial). SD-04.C (authorized at the time) stays with people |
| `approved-requests-for-a-sample-of` | IAM-01.B, C, D, E; IAM-08.C | IAM-01 | person + `tickets.access_requests_approved` (with an identity provider) + new `tickets.access_approver_independent` (partial) |
| `log-of-control-deficiencies-with-owner` | GOV-08.B, C, D, E and others | GOV-08 | `tickets.remediation_tracked` now implemented (partial); GOV-08.C (people told) stays with people |
| `corrective-actions-tracked-to-closure` | LM-05.C | LM-05 | person + `tickets.remediation_tracked` (partial, proposed mapping) |
| `sample-of-reports-received-and-how` | CS-03.C, CS-03.D | CS-03 | person + new `tickets.security_reports_answered` (partial) |
| `security-incident-register` | LM-07.D, LM-04.C and others | LM-07 | person + new `tickets.incidents_registered` (partial: completeness) |

## 7. Framework reach

SOC 2: CC8.1 and CC5.2 (SD-01, SD-04, SD-14), CC6.2 and CC6.3 (IAM-01), CC5.1 (IAM-09), CC4.2
(GOV-08), CC2.2 and CC2.3 (CS-03), CC7.3, CC7.4, CC7.5 and P6.5 (LM-04, LM-05, LM-07).
ISO 27001:2022: A.8.19 and A.8.32 (changes), A.5.15, A.5.16, A.5.18 and A.8.34 (access), A.5.3
(segregation of duties), clause 10.2 (nonconformity), A.5.24, A.5.25, A.5.26, A.5.27, A.5.28 and A.6.8
(incidents and reporting). Most mappings are partial; see [operations-checks.md](operations-checks.md)
section 7.

## 8. Limits and false assurance traps

- **The mapping is the control.** A status mapped as approved that anyone can set, or a project left
  out of scope, makes a clean result meaningless. Every result prints the mapping it used, and a mapping
  change is audited.
- **Deleted tickets vanish with their history.** A ticket deleted after release is gone from Jira.
  Verity's stored observations keep it, and the next result reports it as no longer visible.
- **Moved tickets change key.** The issue id is the stable id; keys are display only.
- **Browse permission defines the population.** A project the service account cannot browse is
  invisible, not empty. Scope discovery lists every project the account sees, so the customer can
  compare it with their list.
- **JSM change management needs Premium or Enterprise** [J16]. On lower plans, change approval must be
  modelled with statuses or fields, which is weaker evidence of who may approve.
- **The audit log needs an admin permission.** Workflow changes that weaken approval are therefore not
  watched by default.
- **Emails may be hidden.** Independence uses account ids, which needs no email. Matching approvers to
  Verity members or identity provider users needs an email, which Jira returns as null when the
  user's privacy setting hides it [J6].

## 9. Product and UI

- **Connect form:** site address, service account email, scoped API token, token expiry date, and the
  cloud id (looked up from `https://<site>.atlassian.net/_edge/tenant_info`, which returns `cloudId`
  [J27]; the form also accepts it pasted, and admin.atlassian.com shows it in the site URL after `/s/`).
- **Scope:** projects and service desks the account can browse, each in or out with a reason.
- **Mapping (required for most checks):** per project, the work types or JQL for changes, emergency
  changes, access requests, security reports, incidents and findings; the statuses for approved,
  released and reviewed; fields for impact, testing, rollback, beneficiary, system, severity, due date;
  the JSM SLA names for first response and resolution; the system owner group for privileged requests.
  A live preview lists matched tickets.
- **Health:** connected; missing scope or permission (per check); not on plan (audit log, change
  management); mapping incomplete (the checks that need it read insufficient information, with a link to
  the mapping); token expiring (30 and 7 days, from the typed date).
- **In product guide:** yes. The token scopes and the mapping are both easy to get wrong.

## 10. Implementation notes

- **Auth.** Basic auth with email and scoped token against `api.atlassian.com/ex/jira/{cloudId}` [J8].
  For the later OAuth app: authorization code at `https://auth.atlassian.com/authorize`, token at
  `https://auth.atlassian.com/oauth/token`, cloud id from `GET
  https://api.atlassian.com/oauth/token/accessible-resources` [J1]; store each new refresh token
  atomically because the old one is disabled after use [J2] (10 minute reuse leeway [J1]); a 403
  `invalid_grant` means reconnect [J2].
- **Collection.** One JQL search per mapped purpose with `updated >= -30d`, ids only, then fields in
  batches, then `changelog/bulkfetch` for the status and mapped fields. JSM approvals and SLAs per
  ticket. Never rely on JQL history operators without a recorded fixture proving them.
- **Rate limits.** Honour `Retry-After`. Keep a per tenant limiter at well under 100 requests per second
  per endpoint. For the OAuth app, a global limiter across tenants against the shared hourly points
  [J14].
- **Actor type.** Automation and app actors must not count as approvers. The user object has
  `accountType` (`atlassian`, `app`, `customer`, `unknown`) [J6]; that the default "Automation for Jira"
  user reads as `app` is unverified, test on a fixture. A rule's actor can also be a real person [J25],
  and then no field on the changelog author tells the two apart; the changelog's `historyMetadata`
  (actor, generator, cause) [J6] may, unverified. Until a fixture proves a marker, the result says that
  status approvals cannot exclude rules running as a person, and the mapping screen asks the customer
  to confirm no rule sets the approved status.
- **Scope drift.** Each run calls one endpoint per scope family and records which failed; only the
  checks needing that scope go to `error`.
- **Fixtures.** Record against a test Jira Cloud site with a JSM project, a change workflow, an
  automation rule that transitions tickets, a deleted ticket and a moved ticket.
- **Personal data.** If the OAuth app ships, implement account reporting on the cycle Atlassian returns
  and erase account ids Atlassian reports as closed [J3].

## 11. How comparable platforms do it

| Platform | Auth | What they test |
|---|---|---|
| Vanta | OAuth; connecting user needs Browse projects and Browse users and groups; service account recommended; write optional for creating tasks | Jira accounts removed for leavers, incident management and resolution tasks completed, security issues resolved within SLA [J21] |
| Drata | Jira integration lists view and optional update scopes (names differ from Atlassian's current strings); a separate Atlassian integration uses a customer created OAuth app with `read:me`, `read:account`, `read:jira-work`, `read:jira-user` | Security issues prioritised (assignee and priority, no SLA); user access review [J22] |
| Secureframe | OAuth 2.0, not a personal token; read `read:jira-user`, `read:jira-work`, `offline_access`, with write scopes for task sync | Vulnerability and incident tracking and resolution, change tracking to deployment, access tracking against SLA [J23] |
| Sprinto | Own OAuth app (including `manage:jira-configuration` and write scopes) or a service account with client credentials and granular scopes | Change ticketing set up, change tickets have an assignee, incidents closed, no new change tickets in 30 days, access removed for leavers [J24] |

None of the public pages describes checking that the approval came **before** release or from someone
other than the requester. That is where Verity's checks differ.

## 12. Sources

- [J1] https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/
- [J2] https://developer.atlassian.com/cloud/oauth/getting-started/refresh-tokens/
- [J3] https://developer.atlassian.com/cloud/jira/platform/user-privacy-developer-guide/
- [J4] https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/
- [J5] https://developer.atlassian.com/cloud/jira/service-desk/scopes-for-oauth-2-3LO-and-forge-apps/
- [J6] https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json (Jira REST v3 OpenAPI: scopes, permissions, paging, deprecations)
- [J7] https://developer.atlassian.com/cloud/jira/service-desk/swagger.v3.json (JSM REST OpenAPI)
- [J8] https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
- [J9] https://support.atlassian.com/user-management/docs/understand-service-accounts/
- [J10] https://support.atlassian.com/user-management/docs/create-oauth-2-0-credential-for-service-accounts/
- [J11] https://support.atlassian.com/atlassian-cloud/kb/401-unauthorized-error-when-service-account-accesses-jira-or-confluence-api/
- [J12] https://developer.atlassian.com/cloud/jira/software/rest/api-group-development-information/
- [J13] https://support.atlassian.com/jira-cloud-administration/docs/audit-activities-in-jira-applications/
- [J14] https://developer.atlassian.com/cloud/jira/platform/rate-limiting/
- [J15] https://support.atlassian.com/jira-cloud-administration/docs/explore-jira-cloud-plans/
- [J16] https://support.atlassian.com/jira-service-management-cloud/docs/updating-your-incident-problem-and-change-management-capabilities/
- [J17] https://developer.atlassian.com/cloud/jira/platform/changelog/
- [J18] https://github.com/orgs/atlassian/repositories?language=go
- [J19] https://github.com/ctreminiom/go-atlassian
- [J20] https://github.com/andygrunwald/go-jira
- [J21] https://help.vanta.com/en/articles/14441707-jira-integration-guide, https://help.vanta.com/en/articles/11345519-tracking-incident-management-and-resolution-tickets-in-vanta-jira
- [J22] https://help.drata.com/en/articles/4663378-jira-integration-guide, https://help.drata.com/en/articles/4806017-jira-security-tickets-label-vs-jql, https://help.drata.com/en/articles/9242322-atlassian-integration-guide
- [J23] https://support.secureframe.com/en/articles/15111698-jira, https://support.secureframe.com/en/articles/15111613-faqs-product-integrations-apis-webhooks-slack-jira-and-related-tools
- [J24] https://docs.sprinto.com/integrations/overview/jira-integration.md
- [J25] https://support.atlassian.com/cloud-automation/docs/what-is-a-rule-actor/
- [J26] https://www.atlassian.com/collections/service/pricing
- [J27] https://support.atlassian.com/jira/kb/retrieve-my-atlassian-sites-cloud-id/
