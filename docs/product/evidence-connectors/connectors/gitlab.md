# GitLab (GitLab.com and self managed)

| | |
|---|---|
| Capabilities | version_control, ci_cd |
| Delivery phase | Phase 2 (signed catalogue) |
| Auth model | A group access token (GitLab.com Premium or Ultimate; any self managed licence) or a group service account's personal access token (all tiers), scope `read_api`, on the top level group. OAuth application as the later "connect with GitLab" option |
| Shares setup with | Nothing. Note: GitLab is also Verity's own main repository host since 2026-11-06; that is unrelated to this connector |
| Go library | `gitlab.com/gitlab-org/api/client-go`, the GitLab owned successor of `github.com/xanzy/go-gitlab` (import path change only) [L14] |

## 1. What it proves

The same change control story as GitHub, in GitLab's terms: protected branches, merge request approval
rules, merged merge requests and who approved them (with the time of each approval), pipelines that must
pass, protected environments and deployment approvals, the group's two factor rule, the member list and,
on Ultimate, the vulnerability report for secrets and dependencies. GitLab's tiers decide most of what
can be enforced, so the connector says per check whether the customer's tier offers it.

`docs/product/continuous-compliance-plan.md` section 7 asks that GitLab reuse the check intent but prove
GitLab's own semantics. Where a GitLab setting does not mean the same as the GitHub one, this document
says so on the check.

## 2. Connecting: method, credentials and permissions

### 2.1 Credential options

| Option | Where it works | Notes |
|---|---|---|
| **Group access token** on the top level group (recommended where available) | GitLab.com Premium and Ultimate (not during a trial); self managed and Dedicated with any licence [L1] | Created by a group Owner; GitLab creates a non billable bot member; role chosen at creation; expires by default 365 days after creation, which is also the default maximum (administrators can change it from 17.6) [L1] |
| **Service account** with a personal access token | All tiers on GitLab.com, self managed and Dedicated; on GitLab.com only top level group Owners create them [L2] | The fallback for GitLab.com Free (up to 100 service accounts per top level group on Free). Not tied to a person. Default and maximum token life 365 days (400 days configurable from 17.6); non expiring only where expiry is not required [L2] |
| Personal access token of a person | All tiers | Ties the connection to a person and reaches everything they can see. Not offered |
| OAuth application | All tiers | Authorization code with PKCE or device flow; example tokens last 7,200 seconds; refreshing invalidates the old pair [L3]. No client credentials grant is documented, so it acts as the person who consented. Later option for a one click "Connect with GitLab" |

Scope: **`read_api`**, which grants read access to the API only, so the token is read only whatever its
role [L4]. `read_repository` is not needed. `read_api` does let the token read repository files through
the API, and the Maintainer role manages project CI/CD variables, so it can read their values
(`GET /projects/:id/variables`) [L15]; the collector never calls those endpoints. Fine grained personal
access tokens are generally available on all tiers since GitLab 19.2 [L16]; group access tokens and
service account tokens are exempt from their enforcement and keep working. Whether a service account can
hold a fine grained token is not stated (unverified).

Role: the lowest role that can read each item. The API pages for protected branches, approval settings
and protected environments state no minimum role to read them (still unverified per endpoint); the
permissions table gives managing all three to Maintainer [L15], so **Maintainer** is proposed. **Owner** is
needed for the group's audit events of all users (Premium; Developers and Maintainers see only their own
actions) and to see members' `two_factor_enabled` [L5] [L17]; offer it as an opt in. Project audit events
of all users need only Maintainer [L5].

### 2.2 Permissions by check

| Item read | Scope and role | Tier | Needed for |
|---|---|---|---|
| Groups, projects, default branches | `read_api`, Reporter or above | all | every per project check |
| Protected branches `GET /projects/:id/protected_branches` | `read_api`, Maintainer (the API states no role; Maintainer manages them [L15]) | all; `code_owner_approval_required`, and `user_id` and `group_id` in access levels, are Premium and Ultimate; `deploy_key_id` is on Free since 18.10 [L6] | `vcs.default_branch_protected`, `vcs.protection_bypass_limited` |
| Project approval configuration `GET /projects/:id/approvals`, approval rules | `read_api` (the API states no role; Maintainer manages approval rules [L15]; exact read role unverified) | Premium and Ultimate (confirmed) [L7] | `vcs.review_required`, `vcs.approval_resets_on_change` |
| Merge request approvals `GET /projects/:id/merge_requests/:iid/approvals` | `read_api`, Reporter | all tiers [L7] | `vcs.merged_changes_reviewed`, `vcs.unreviewed_merges_recorded` |
| Merged merge requests, pipelines, jobs | `read_api`, Reporter | all | `vcs.merged_changes_reviewed`, `ci.required_checks_passed`, `vcs.secret_scanning_enabled`, `vcs.code_scanning_enabled`, `vcs.dependency_alerts_enabled` |
| Project merge settings (`only_allow_merge_if_pipeline_succeeds`, `allow_merge_on_skipped_pipeline`) | `read_api` (Projects API fields vary by the caller's permissions; exact role unverified, Maintainer covers it) | all tiers (confirmed) [L18] | `vcs.status_checks_required` |
| Commits on the default branch and their merge requests | `read_api`, Reporter | all | `vcs.unreviewed_merges_recorded` |
| Environments and deployments `GET /projects/:id/deployments` | `read_api`, Reporter | all; approvals and `approval_summary` Premium [L8] | `ci.deployment_history_recorded`, `ci.production_deploys_approved` |
| Protected environments `GET /projects/:id/protected_environments` | `read_api`, Maintainer (the API states no role; Maintainer manages them [L15]). Returns 403 when CI/CD is off for the project [L9] | Premium and Ultimate (confirmed) [L9] | `ci.production_deploys_controlled` |
| Vulnerabilities (GraphQL; the REST API is being deprecated) | `read_api`, a role that can view the vulnerability report: Developer, Maintainer, Owner or Security Manager, not Reporter [L15] | Ultimate (confirmed) [L10] | `vcs.secret_alerts_closed_in_time`, `vcs.dependency_alerts_within_sla` |
| Secret push protection setting (Projects API attribute `secret_push_protection_enabled`) | `read_api` | Ultimate (confirmed) [L11] | `vcs.push_protection_enabled` |
| Group settings `require_two_factor_authentication`, `two_factor_grace_period` | `read_api` (responses vary by the caller's permissions) | all [L12] | `vcs.org_two_factor_required` |
| Group members `GET /groups/:id/members/all` (access levels 10 to 50) | `read_api`, Reporter; `two_factor_enabled` is visible only to group Owners and administrators [L17] | all | `vcs.access_list_exported` |
| Group audit events `GET /groups/:id/audit_events` | `read_api`, Owner for every user's events (confirmed); project audit events of all users need Maintainer [L5] | Premium and Ultimate; keyset paging (offset paging deprecated in 17.8, removal planned for 19.0) [L5] | optional evidence of protection changes; no check depends on it |

Vendor side prerequisites: none for tokens. An OAuth application, if built, is registered by Verity on
GitLab.com (and once per self managed instance by its administrator).

## 3. Customer setup guide (draft product text)

**GitLab.com Premium or Ultimate, or self managed**

1. Sign in to GitLab as an Owner of the top level group that holds your production code.
2. Open the group, then **Settings**, **Access tokens**, **Add new token**.
3. Name it `Verity`, set an expiry date (Verity reminds you 30 and 7 days before), choose the role
   **Maintainer** (or **Owner** if you want Verity to read audit events), and tick only **read_api**.
4. Create the token and copy it. GitLab shows it once.
5. In Verity, open Integrations, choose GitLab, paste the token, and for self managed GitLab type your
   GitLab address. Click **Check connection**.
6. Choose the projects that are part of your audited system, give a reason for each one you leave out,
   and mark the projects that deploy to production.

**GitLab.com Free**

1. As an Owner of the top level group, create a service account (**Settings**, **Service accounts**).
2. Add it to the group with the **Maintainer** role.
3. Create a personal access token for the service account with only **read_api**, then continue at step 5
   above.

## 4. What Verity collects

| Resource | API | Fields kept | Paging and limits | Provider retention |
|---|---|---|---|---|
| Group and projects | `GET /groups/:id`, `GET /groups/:id/projects?include_subgroups=true` | ids, path, archived, default branch, merge settings, two factor rule | keyset or offset paging | live |
| Protected branches | `GET /projects/:id/protected_branches` | name pattern, push and merge access levels (role, user, group, deploy key), `allow_force_push`, `code_owner_approval_required` [L6] | per project | live |
| Approval settings | `GET /projects/:id/approvals`, `GET /projects/:id/approval_rules` | `merge_requests_author_approval`, `merge_requests_disable_committers_approval`, `reset_approvals_on_push` [L7], rules with approvals required and branches | per project | live |
| Merged merge requests | `GET /projects/:id/merge_requests?state=merged&target_branch=&updated_after=` then `.../approvals` | iid, author, merged at, merge user, SHA, merge commit SHA; approvals with `approved_by[].user` and `approved_at` [L7] | 30 days, 100 per project (same caps as GitHub) | live |
| Pipelines | `GET /projects/:id/merge_requests/:iid/pipelines`, `GET /projects/:id/pipelines?ref=&sha=`, pipeline jobs | status, SHA, finished at; job names and report artifact types (confirmed: each job's `artifacts[].file_type`; report types include `sast`, `dependency_scanning` and `secret_detection` [L19]) | per change, bounded | the project's artifact and pipeline retention |
| Deployments | `GET /projects/:id/environments`, `GET /projects/:id/deployments?environment=&finished_after=&order_by=finished_at` (`finished_after` without `order_by=finished_at` or `status=success` returns 400 [L8]) | environment and `tier` (production, staging, testing, development, other; from the environments API, which cannot filter by tier [L20]), SHA, ref, user, status, created, finished (`finished_at` sits in the `deployable` job); `approval_summary` on Premium when several approval rules exist [L8] | 30 days | live |
| Protected environments | `GET /projects/:id/protected_environments` | name, deploy access levels, required approval count [L9] | per project | live |
| Vulnerabilities (Ultimate) | GraphQL `project.vulnerabilities` (or `group.vulnerabilities` for all projects at once), filtered by `reportType`, `state`, `severity` | `reportType` (`SECRET_DETECTION`, `DEPENDENCY_SCANNING`), `severity`, `state` (DETECTED, CONFIRMED, RESOLVED, DISMISSED), `detectedAt`, `resolvedAt`, `dismissedAt`, `dismissalReason` (field names confirmed [L21]) | GraphQL cursors | live |
| Members | `GET /groups/:id/members/all` | username, access level, expiry, state; `two_factor_enabled` only when the token is a group Owner (or an administrator on self managed) [L17] | paged | live |
| Audit events (optional, Premium) | `GET /groups/:id/audit_events?created_after=` | event type, author, target, time | keyset | retention not stated [L5] |

Rate limits on GitLab.com: plan based limits per user and per top level group are published but are a
proposal, not yet in effect; today's current limits apply, and when both exist the lower wins
(corrected 2026-11-23: was "now depend on the plan"). The proposed figures: per user 5,000, 15,000 and
25,000 per hour for Free, Premium and Ultimate; per top level group 5,000 per hour on Free (Premium and
Ultimate "not yet confirmed"), with group bursts of 400, 5,000 and 10,000 per minute [L13]. Self
managed limits are the instance's settings. The collector honours the headers GitLab sends on every
response (`RateLimit-Limit`, `RateLimit-Name`, `RateLimit-Observed`, `RateLimit-Remaining`,
`RateLimit-Reset`) and on a 429 (`Retry-After`, `RateLimit-ResetTime`) [L22], and records `truncated` when
it cannot finish.

Self managed: the customer gives the base URL; Verity reads the version (`GET /version` or `GET /metadata`, confirmed [L23]) to
know which fields exist, accepts a custom CA if the customer uploads one, and must reach the instance
from the internet (or the customer allowlists Verity's egress address).

## 5. Checks

Population, outcomes and period as in `github.md` section 5. A setting the tier does not offer is `fail`
with `reason: plan` and the ways out (upgrade, or leave the project out with a reason).

| Check | GitLab feasibility and meaning | Population | Predicate on GitLab | pass / fail / error / insufficient | Frequency | Evidence | Controls |
|---|---|---|---|---|---|---|---|
| `vcs.default_branch_protected` | Yes, all tiers | default branch of each project | a protected branch rule matches it, force push is off, and push access is **No one**, or limited to named users, groups or deploy keys (the counterpart of GitHub's push restrictions). A role that may push (Developers, Maintainers) means direct pushes are possible: `fail`. Named users and groups in access levels are Premium and Ultimate, so on Free only **No one** or a deploy key (Free since 18.10) passes [L6] | as GitHub | daily | protected branch rule | SD-06 partial, SD-01 partial |
| `vcs.review_required` | Premium and Ultimate. On Free approvals are optional and cannot be required | same | an approval rule covering the default branch requires at least one approval, and authors cannot approve their own changes | pass; fail; fail `reason: plan` on Free | daily | approval settings and rules | SD-06 partial, SD-01 partial |
| `vcs.status_checks_required` | Yes, all tiers (confirmed [L18]) | projects | "Pipelines must succeed" is on and skipped pipelines do not count as success | pass, fail, error | daily | merge settings | SD-02 partial |
| `vcs.merged_changes_reviewed` | Yes, all tiers: the approvals endpoint gives each approver and `approved_at` [L7] | merge requests merged into the default branch in 30 days | each had an approval from someone other than its author with `approved_at` before `merged_at`. The endpoint shows current approvals, so a withdrawn approval simply disappears (correct for the purpose); approvals by committers count unless the project bars them, and the evidence says which | as GitHub | daily | changes, approvers, times | SD-01 partial, SD-06 partial |
| `vcs.secret_scanning_enabled` | Partly. Pipeline secret detection runs on all tiers and produces a JSON report; only Ultimate shows results in the vulnerability report [L11] | projects | the latest default branch pipeline in 30 days ran a job that produced a secret detection report | pass, fail, error, insufficient when no pipeline ran | daily | job and report type | SD-11 partial |
| `vcs.dependency_alerts_enabled` | Ultimate only: dependency scanning itself is an Ultimate feature [L24] (corrected 2026-11-23: was "partly, tier unverified, believed Ultimate for results"). Free and Premium are `fail` `reason: plan`. Scanning by SBOM uploads CycloneDX reports, so accept a `cyclonedx` report as well as `dependency_scanning` [L19] | projects | the latest default branch pipeline produced a dependency scanning report | pass, fail, fail `reason: plan`, error | daily | job and report type | SD-03 partial, LM-11 partial |
| `vcs.org_two_factor_required` | Yes, all tiers | top level group | `require_two_factor_authentication` is true. The grace period is printed | pass, fail, error | daily | group settings | IAM-03 partial |
| `vcs.code_scanning_enabled` | Partly. SAST runs on all tiers and gives a downloadable JSON report; the vulnerability report and merge request findings are Ultimate [L25] | projects | the latest default branch pipeline produced a SAST report | pass, fail, error | daily | job and report type | SD-05 partial |
| `vcs.unreviewed_merges_recorded` | Yes. Commits on the default branch are readable with `read_api`, so direct pushes can be found without a new permission | merged changes without approval, and commits on the default branch in 30 days with no merge request | each has a Verity review record as on GitHub | as GitHub | daily | items and reviews | SD-04 partial, SD-06 partial |
| `ci.required_checks_passed` | Yes | merged merge requests in 30 days | the merge request's head pipeline for the merged SHA finished `success` before `merged_at` | pass, fail, error, insufficient | daily | change, pipeline, status, time | SD-02 partial |
| `ci.production_deploys_controlled` | Premium and Ultimate (protected environments) | the environment with tier production (or named in settings) in projects marked as deploying | the environment is protected, deploy access is limited to named users, groups or roles the customer allows, and at least one approval is required | pass; fail; fail `reason: plan` on Free | daily | protected environment | SD-13 partial |
| `ci.deployment_history_recorded` | Yes, all tiers | production deployments in 30 days | each has SHA, ref, user, created and finished times and a final status | pass, fail, insufficient for a deploying project with no records | daily | deployments | SD-13 partial, SD-14 partial |
| `vcs.protection_bypass_limited` (NEW, see `github.md`) | Partly. GitLab has no separate bypass list; who can push or merge is the access levels | default branch rule | no role above the customer's allowed set may push or merge without the approval rule, and no user is allowed to push directly except named automation | pass, fail, error | daily | access levels | SD-06 partial, SD-04 partial |
| `vcs.approval_resets_on_change` (NEW) | Premium and Ultimate | projects | `reset_approvals_on_push` is true, or committers cannot approve (`merge_requests_disable_committers_approval`) | pass, fail, fail `reason: plan` | daily | approval settings | SD-06 partial, SD-01 partial |
| `vcs.push_protection_enabled` (NEW) | Ultimate [L11] | projects | secret push protection is on | pass, fail, fail `reason: plan` | daily | project setting | SD-11 partial, NS-09 partial |
| `vcs.secret_alerts_closed_in_time` (NEW) | Ultimate (vulnerability report) | secret detection vulnerabilities open now or closed in 30 days | none open longer than the setting | pass, fail, fail `reason: plan`, error | daily | vulnerabilities without the secret | SD-11 partial, NS-09 partial |
| `vcs.dependency_alerts_within_sla` (NEW) | Ultimate | dependency scanning vulnerabilities | none open past the workspace's timeframe for its severity | pass, fail, fail `reason: plan`, error | daily | vulnerabilities | SD-03 partial, LM-11 partial |
| `vcs.access_list_exported` (NEW) | Yes | members of the top level group and its projects, with access level | full list read | pass when complete, insufficient | weekly | dated member list | IAM-02 partial, IAM-07 partial, IAM-12 partial |
| `ci.production_deploys_approved` (NEW) | Premium and Ultimate (deployment approvals) | production deployments in 30 days | each ran from the default branch or a tag and, where approvals are required, was approved by someone other than the deployer | pass, fail, fail `reason: plan`, error | daily | deployment, approvals | SD-13 partial, SD-12 partial |

New check definitions are in `github.md` section 5.2; GitLab is added to their planned providers.

## 6. Artifacts and objectives it fills

Same artifacts as `github.md` section 6, with GitLab as a second implementation: `branch-protection-settings`
(SD-02.B, SD-06.C, SD-13.B), `sample-of-reviewed-changes` (SD-01.B, SD-01.D, SD-06.B, SD-06.D, SD-14.C),
`change-requests-with-approval-for-a`, `unreviewed-merge-log` and `emergency-changes-with-their-after-the`
(SD-04.B to D, SD-06.E), `test-run-results-for-a-sample` (SD-02.C, SD-02.D), `deployment-history-for-a-sample-of`
(SD-12.D, SD-13.B, C, E), `change-records-linking-request-review-and` (SD-14), `open-alerts-triaged-within-the-timeframe`
(SD-03, Ultimate), `records-of-exposed-secrets-that-were` (SD-11, Ultimate for the alert half),
`evidence-validation-was-tested` (SD-05.B), `account-list-export` (IAM-02.B, IAM-12.E),
`list-of-privileged-accounts-with-approval` (IAM-07.B), and `second-factor-enforcement-and-enrolled-users` (IAM-03.B).

One GitLab specific gain: on Premium, group audit events can show that a protected branch or approval
rule was not changed during the period. No artifact asks for that today:
`NEED version_control: a log of changes to branch protection and approval rules over the period`
(supports SD-06.C "throughout the period").

## 7. Framework reach

Controls: SD-01 to SD-06, SD-11, SD-13, SD-14, LM-11, IAM-02, IAM-03, IAM-07, IAM-12 (and LM-02 if
audit events become evidence).

- **SOC 2:** CC5.2, CC6.1, CC6.2, CC6.3, CC6.8, CC7.1, CC8.1, PI1.2, PI1.3 (CC2.1 and CC7.2 only through
  LM-02, if adopted).
- **ISO 27001:2022 Annex A:** A.5.3, A.5.16, A.5.17, A.5.18, A.5.21, A.5.32, A.8.2, A.8.4, A.8.5, A.8.8,
  A.8.18, A.8.19, A.8.25, A.8.26, A.8.28, A.8.29, A.8.30, A.8.32 (A.5.28 and A.8.15 only through LM-02).

## 8. Limits and false assurance traps

- **Free tier cannot require approvals.** A Free customer passes `vcs.default_branch_protected` but fails
  `vcs.review_required` with `reason: plan`. `vcs.merged_changes_reviewed` still shows whether people
  approved in practice, which is the operating evidence an auditor samples.
- **"Maintainers can push" is a common default.** It fails `vcs.default_branch_protected` here, while
  GitHub's equivalent (named push restrictions) passes. The difference is intended: a role is everyone
  in it.
- **Scanner jobs are configuration, not coverage.** A secret detection job that ran proves it ran on that
  pipeline. On Free there is no alert list to show results were handled.
- **Approvals endpoint shows the current state.** An approval given and withdrawn leaves no trace there;
  audit events (Premium) are the only history.
- **Enrolled users need Owner.** `two_factor_enabled` on members is shown only to group Owners and
  administrators [L17]. With the default Maintainer token, `second-factor-enforcement-and-enrolled-users`
  gets the group rule but not the enrolled list; that half stays `insufficient information`.
- **Self managed reachability.** A private instance Verity cannot reach is `error` on every check, never
  a fail.
- **Token reach.** `read_api` with Maintainer can read files and, for Maintainers, CI variables. The
  collector does not call those endpoints, and the setup guide says so; the residual risk is Verity's
  own credential handling (envelope encrypted, never logged).

## 9. Product and UI

Connect form: GitLab address (default `https://gitlab.com`), token, optional CA certificate. After
connect: project picker with reasons (archived out by default, forks out by default), "deploys
production" per project, production environment name. The tier is detected where the API exposes it:
on GitLab.com from the namespace's `plan` and `trial` attributes (`GET /namespaces/:id`; the page is
unclear whether a non Owner token sees them) [L26], on self managed from `plan` in `GET /metadata`
(GitLab 19.6 and later; null on GitLab.com) [L23]; otherwise asked once, so plan limited results read
correctly. Health: token expiry (from
the token's own metadata where readable, else typed), missing role, instance unreachable, rate limited.
In product guide needed: yes (token role and scope, Free tier path through a service account).

## 10. Implementation notes

- Go: `gitlab.com/gitlab-org/api/client-go`; one client per connection with the base URL.
- Paging: keyset where offered (audit events, projects), offset elsewhere; stop at the caps and record
  `truncated`.
- Error mapping: 401 token expired or revoked -> connection `error`; 403 -> role too low for that item,
  only the checks that need it are `error`; 404 on Premium endpoints for Free groups -> `reason: plan`, not
  `error` (confirm the response for each endpoint in fixtures).
- Fixtures: recorded against a GitLab.com Free group, a Premium trial is not usable for group access
  tokens [L1], and a self managed instance in a container (license dependent features stubbed).
- Scope drift: a lowered role or a removed scope shows "missing access: X" with the checks it blocks.
- Deletion: projects archived or removed leave `connection_resources` with `last_seen`.

## 11. How comparable platforms do it

Not researched this round: the web search budget for this session ran out before the GitLab pages of
Vanta, Drata, Secureframe and Sprinto were read (still unverified: competitor pages are outside the
provider documentation checked on 2026-11-23). To be filled before build.

## 12. Sources

- [L1] Group access tokens: https://docs.gitlab.com/user/group/settings/group_access_tokens/
- [L2] Service accounts: https://docs.gitlab.com/user/profile/service_accounts/
- [L3] OAuth 2.0 identity provider API: https://docs.gitlab.com/api/oauth2/
- [L4] Access token scopes: https://docs.gitlab.com/security/tokens/access_token_scopes/
- [L5] Audit events API: https://docs.gitlab.com/api/audit_events/
- [L6] Protected branches API: https://docs.gitlab.com/api/protected_branches/
- [L7] Merge request approvals API: https://docs.gitlab.com/api/merge_request_approvals/
- [L8] Deployments API: https://docs.gitlab.com/api/deployments/
- [L9] Protected environments API: https://docs.gitlab.com/api/protected_environments/
- [L10] Vulnerabilities API: https://docs.gitlab.com/api/vulnerabilities/
- [L11] Secret detection and pipeline secret detection: https://docs.gitlab.com/user/application_security/secret_detection/ and https://docs.gitlab.com/user/application_security/secret_detection/pipeline/ ; Projects API: https://docs.gitlab.com/api/projects/
- [L12] Groups API: https://docs.gitlab.com/api/groups/
- [L13] GitLab.com rate limits: https://docs.gitlab.com/user/gitlab_com/rate_limits/ and https://docs.gitlab.com/user/gitlab_com/
- [L14] Go client migration: https://gitlab.com/gitlab-org/api/client-go/-/issues/2060
- [L15] Roles and permissions tables (protected branches, approval rules, protected environments, CI/CD variables, vulnerability report, audit events, 2FA status): https://docs.gitlab.com/user/permissions/
- [L16] Fine grained personal access tokens (GA in 19.2, enforcement exemptions): https://docs.gitlab.com/auth/tokens/fine_grained_access_tokens/
- [L17] Group and project members API (`two_factor_enabled` visibility): https://docs.gitlab.com/api/group_members/
- [L18] Pipelines must succeed and skipped pipelines (all tiers): https://docs.gitlab.com/user/project/merge_requests/auto_merge/
- [L19] Jobs API (`artifacts[].file_type`): https://docs.gitlab.com/api/jobs/ ; Job artifacts API report types: https://docs.gitlab.com/api/job_artifacts/ ; artifacts report types: https://docs.gitlab.com/ci/yaml/artifacts_reports/
- [L20] Environments API (`tier`): https://docs.gitlab.com/api/environments/
- [L21] GraphQL `Vulnerability` object and `vulnerabilities` arguments: https://docs.gitlab.com/api/graphql/reference/ (objects page)
- [L22] Rate limit response headers: https://docs.gitlab.com/administration/settings/user_and_ip_rate_limits/
- [L23] Metadata and version API (`plan` from 19.6): https://docs.gitlab.com/api/version/
- [L24] Dependency scanning (Ultimate): https://docs.gitlab.com/user/application_security/dependency_scanning/
- [L25] SAST tiers: https://docs.gitlab.com/user/application_security/sast/
- [L26] Namespaces API (`plan`, `trial`): https://docs.gitlab.com/api/namespaces/

## Decisions for the owner

- **D-GL-1.** Token role: Maintainer by default (reads the settings) with Owner as opt in for audit
  events. Both can read more than Verity uses (files, CI variables). Accept, or move to fine grained
  personal access tokens (generally available on all tiers since 19.2 [L16]; whether a service account
  can hold one, and whether group access tokens can be fine grained, is not stated: unverified)? Note:
  Owner is also the only role that sees members' two factor state [L17].
- **D-GL-2.** GitLab.com Free customers: support them through a service account (recommended), or require
  Premium.
- **D-GL-3.** Self managed instances behind a firewall: in Phase 2 scope (allowlisting Verity's egress
  address), or later.
