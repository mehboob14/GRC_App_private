# Bitbucket Cloud

| | |
|---|---|
| Capabilities | version_control, ci_cd |
| Delivery phase | Phase 2 (signed catalogue). Bitbucket Data Center is not in scope |
| Auth model | Workspace access token (Premium) or repository access tokens, read scopes only. App passwords are gone. Reading branch restrictions needs an admin scope: decision D-BB-1 |
| Shares setup with | Atlassian (Jira) OAuth app in `02-integration-model.md` is a separate credential; a Forge or OAuth consumer shared with Jira is a later option (unverified: not researched, and no check depends on it) |
| Go library | Atlassian publishes an OpenAPI 3 spec for REST 2.0 [B8] and lists no official Go SDK (still unverified, because absence cannot be shown from one page; only community libraries were seen). Use the REST API 2.0 directly with `net/http` |

## 1. What it proves

Merged pull requests and who approved them, pipelines and build statuses on each change, deployments
to environments, and the workspace member list. Bitbucket can enforce merge rules (approvals, passing
builds) only on Premium; on Standard and Free the same checks warn but still let people merge [B5], so
the connector proves the setting on Premium and the practice everywhere.

Bitbucket has no built in dependency alerting. Bitbucket Cloud has no built in secret scanning either:
for Cloud, Atlassian documents a `git-secrets-scan` Pipelines pipe, and built in secret scanning is a
Data Center feature [B9]; the REST 2.0 spec has no secret scanning endpoint [B8]. Those checks need
another source.

## 2. Connecting: method, credentials and permissions

### 2.1 Credential options

| Option | Plans | Notes |
|---|---|---|
| App password | none | New app passwords stopped on 9 September 2025; existing ones were to stop on 9 June 2026, later moved to brownouts ending 28 July 2026 [B1]. Not supported |
| **Workspace access token** (recommended on Premium) | Premium only [B2] | Scoped to the workspace with chosen scopes; up to 25 per workspace; optional expiry; not tied to a person [B2] |
| **Repository access tokens** (Standard and Free) | Atlassian names only workspace and project tokens as Premium; no plan limit is stated for repository tokens [B2] | One per repository, 25 per repository. Workable for a handful of repositories; the customer creates one per in scope repository. A repository token reaches only its own repository, and its scope list has no `account` scope, so it cannot read workspace members or list other repositories [B2] [B8] |
| API token of a dedicated Atlassian account | all | Scoped at creation; expiry required, at most one year; Basic auth with the account email, or Bearer [B8] [B1]. A person shaped account (may take a seat: unverified, the billing pages were not read) |
| OAuth 2.0 consumer | all | Grants: authorization code, implicit, client credentials and the Bitbucket JWT grant; a client credentials token acts as the owner of the consumer, not an end user [B8]. Later option |

Access tokens raise rate limits: scaled limits (1,000 per hour plus 10 per paid user over 100, up to
10,000 per hour for `/2.0/repositories/*`) apply to Standard and Premium workspaces with at least 100
paid users that call with a workspace, project or repository access token, or as a Forge app [B6].

### 2.2 Scopes

| Scope (API token naming) | Read only | Needed for | Plan |
|---|---|---|---|
| `read:repository:bitbucket` (access token: Repositories Read, `repository`) | yes (it also reads source code) | repositories, default branch, branching model, commits, commit build statuses (`GET .../commit/{sha}/statuses` needs this scope, per the spec [B8]): `ci.required_checks_passed` | all [B3] |
| `read:pullrequest:bitbucket` (access token: Pull requests Read, `pullrequest`) | yes for API tokens; the access token label also allows creating and resolving tasks [B10] | merged pull requests, participants, activity, pull request statuses: `vcs.merged_changes_reviewed`, `vcs.unreviewed_merges_recorded`, `ci.required_checks_passed` | all [B3] |
| `read:pipeline:bitbucket` (access token: Pipelines Read, `pipeline`) | yes | pipelines, steps, code insights: `ci.required_checks_passed`; deployments and environments (confirmed: the spec lists this scope for `/environments` and `/deployments` [B8]): `ci.deployment_history_recorded` | all [B3] |
| `read:workspace:bitbucket` (access token: Account Read, `account`, offered on workspace tokens only [B8] [B10]) | yes | workspace members and permissions: `vcs.access_list_exported` | all [B3]; with access tokens, Premium only, because repository and project tokens have no `account` scope |
| `admin:repository:bitbucket` (OAuth and access token `repository:admin`) | **no: it can edit branch restrictions, the branching model and default reviewers** | listing branch restrictions: `vcs.default_branch_protected`, `vcs.review_required`, `vcs.status_checks_required`, `vcs.approval_resets_on_change`, `vcs.protection_bypass_limited` | all [B3][B4]. Confirmed in the spec: `GET /repositories/{w}/{r}/branch-restrictions` requires `repository:admin` (API token `admin:repository:bitbucket`) [B8]. This scope does not include reading repository contents, so it is added to the read scopes, not instead of them [B3] |

There is no read only scope for branch restrictions. Atlassian's own tracker has a request to lower it
(BCLOUD-24231); as of 23 November 2026 the published spec still lists only the admin scope, so it has
not shipped [B4] [B8]. Verity's rule is read only, least privilege, and a
connector that needs write access needs an ADR (`docs/architecture/integrations.md`). Hence D-BB-1.

## 3. Customer setup guide (draft product text, without branch restrictions)

**Premium**

1. Sign in to Bitbucket as a workspace administrator.
2. Open the workspace's **Settings**, then **Access tokens**, **Create access token**.
3. Name it `Verity`, set an expiry date, and tick only these read permissions: **Repositories: Read**,
   **Pull requests: Read**, **Pipelines: Read**, **Account: Read** [B10] (corrected 2026-11-23: the
   last label was "Workspace membership: Read", which Bitbucket does not offer).
4. Create it and copy the token. Bitbucket shows it once.
5. In Verity, open Integrations, choose Bitbucket, paste the token and the workspace id, then click
   **Check connection**.
6. Choose the repositories that are part of your audited system and mark the ones that deploy to
   production.

**Standard or Free**: create a repository access token with the same read permissions in each in scope
repository (**Repository settings**, **Access tokens**), and paste them in Verity one by one.
Repository tokens have no Account permission [B8], so the member list (`vcs.access_list_exported`) needs
an API token of a dedicated account with `read:workspace:bitbucket`, or stays with a person.

If the owner approves D-BB-1, an optional step adds **Repositories: Admin**, with the warning in the
screen that this permission could change settings and Verity never uses it to write.

## 4. What Verity collects

| Resource | API (REST 2.0) | Fields kept | Paging and limits | Provider retention |
|---|---|---|---|---|
| Repositories | `GET /2.0/repositories/{workspace}` | uuid, slug, private, main branch, project, updated | `pagelen`, `next` links | live |
| Branch restrictions (only with D-BB-1) | `GET /2.0/repositories/{w}/{r}/branch-restrictions` | kind, pattern, value (number of approvals), users and groups exempted | paged | live |
| Merged pull requests | `GET /2.0/repositories/{w}/{r}/pullrequests?state=MERGED&q=destination.branch.name="main" AND updated_on>...` | id, author, `closed_by`, `merge_commit`, destination, `updated_on`; `participants` with `approved`, `state` and `participated_on` (for an approver, the time of the approval) [B8]; activity approval events with date (activity item fields not in the spec schema) | 30 days, 100 per repository | live |
| Build results | `GET /2.0/repositories/{w}/{r}/commit/{sha}/statuses` (state is FAILED, INPROGRESS, STOPPED or SUCCESSFUL); `GET /2.0/repositories/{w}/{r}/pipelines?target.commit.hash=` (confirmed: a documented query parameter of that endpoint, not a `q` filter) [B8] | key, state, `updated_on`; pipeline state, trigger, creator, `created_on`, `completed_on` | per change | the workspace's pipeline retention (unverified: not found in the docs read) |
| Environments and deployments | `GET /2.0/repositories/{w}/{r}/environments`, `GET /2.0/repositories/{w}/{r}/deployments` | environment `uuid` and `name`; deployment state (COMPLETED carries `deployer`, `status`, `start_date`, `completion_date`), release (`commit`, `created_on`) [B8]. The environment type (Test, Staging, Production) is not in the spec schema (unverified field name; test on a fixture) | 30 days | live |
| Members | `GET /2.0/workspaces/{w}/members`, `GET /2.0/workspaces/{w}/permissions` (both need the `account` scope, API token `read:workspace:bitbucket`) | account, permission (owner, collaborator, member; Atlassian is removing `collaborator` from the API) [B8] | paged | live |

Rate limits: 1,000 requests per hour per user or token for repository data, scaled as in 2.1 for large
paid workspaces; rolling one hour window; back off on 429 and prefer sequential requests [B6].

## 5. Checks

Population, outcomes and period as in `github.md` section 5.

| Check | Bitbucket feasibility and meaning | Population | Predicate on Bitbucket | pass / fail / error / insufficient | Frequency | Evidence | Controls |
|---|---|---|---|---|---|---|---|
| `vcs.default_branch_protected` | Only with D-BB-1 | main branch of each repository | restrictions block pushes except named users or groups, and block force pushes and deletion | as GitHub; `error` "permission not granted" without D-BB-1 | daily | restrictions | SD-06 partial, SD-01 partial |
| `vcs.review_required` | Only with D-BB-1. On Standard and Free, merge checks are warnings and can be ignored; only Premium's "Prevent a merge with unresolved merge checks" enforces them [B5] | same | a restriction requires at least one approval to merge, and merge checks are enforced | pass; fail; fail `reason: plan` on Standard or Free | daily | restrictions | SD-06 partial, SD-01 partial |
| `vcs.status_checks_required` | Only with D-BB-1, Premium to enforce | same | a restriction requires passing builds, and merge checks are enforced | as above | daily | restrictions | SD-02 partial |
| `vcs.merged_changes_reviewed` | Yes, all plans, `read:pullrequest` | pull requests merged into the main branch in 30 days | each had an approval from a participant other than the author, dated before the merge (approval date: `participants[].participated_on` where `approved` is true [B8]) | as GitHub | daily | changes, approvers, times | SD-01 partial, SD-06 partial |
| `vcs.secret_scanning_enabled` | Not implementable: Bitbucket Cloud has no built in secret scanning (a Pipelines pipe only; built in scanning is Data Center) and no API for it [B9] [B8] | | | another provider or a person | | | SD-11 |
| `vcs.dependency_alerts_enabled` | Not implementable: no native dependency alerts | | | another source (scanner, Phase 3) | | | SD-03, LM-11 |
| `vcs.org_two_factor_required` | Not implementable: workspace two step enforcement is a Premium setting [B11], and neither the workspace object nor any REST 2.0 endpoint exposes it [B8] | | | identity provider covers it when sign in is through Atlassian Guard or SSO | | | IAM-03 |
| `vcs.code_scanning_enabled` | Not implementable natively | | | | | | SD-05 |
| `vcs.unreviewed_merges_recorded` | Yes for unapproved merges. Direct pushes: `GET .../commit/{sha}/pullrequests` (`read:pullrequest`) finds the pull request of a commit, but only after the Pull Request Commit Links app is installed in the workspace, which happens when someone first clicks "Go to pull request" on a commit in the web interface [B8]. Without it the direct push part is `insufficient information`, never a pass | merged changes without approval, and main branch commits with no pull request, in 30 days | each has a Verity review record | as GitHub | daily | items and reviews | SD-04 partial, SD-06 partial |
| `ci.required_checks_passed` | Yes, `read:pullrequest` (pull request statuses) or `read:repository` (commit statuses), plus `read:pipeline` [B8] (corrected 2026-11-23: was `read:pullrequest` and `read:pipeline` only; the commit statuses endpoint needs `read:repository`) | merged pull requests in 30 days | every build status on the merged source commit was SUCCESSFUL before the merge, and at least one exists | pass, fail, error, insufficient | daily | change, statuses | SD-02 partial |
| `ci.production_deploys_controlled` | Not implementable by API today. Deployment permissions (admins only, or named users and groups) are Premium [B7], but the REST 2.0 spec has no field or endpoint for them, and the environment object documents only `uuid` and `name` [B8]; the permissions page does not mention branch limits (corrected 2026-11-23: was "partly", with API exposure unverified). The check reads `error` "not readable" and the setting stays with a person's screenshot | production environments | deployments limited to admins or named users, and to named branches | pass, fail, fail `reason: plan`, error when not readable | daily | environment settings | SD-13 partial |
| `ci.deployment_history_recorded` | Yes | deployments to Production type environments in 30 days | each has commit, state and time; the person or trigger is shown where the pipeline records it | pass, fail, insufficient for deploying repositories with no records | daily | deployments | SD-13 partial, SD-14 partial |
| `vcs.approval_resets_on_change` (NEW) | Only with D-BB-1 | same | the restriction that resets approvals when the source branch changes is on (kind `reset_pullrequest_approvals_on_change`, or `smart_reset_pullrequest_approvals` [B8]) | pass, fail, error | daily | restrictions | SD-06 partial, SD-01 partial |
| `vcs.protection_bypass_limited` (NEW) | Only with D-BB-1 | same | no users or groups are exempted from the approval and build restrictions beyond the customer's allowed list | pass, fail, error | daily | exemptions | SD-06 partial, SD-04 partial |
| `vcs.access_list_exported` (NEW) | Yes with a workspace access token (Premium) or an API token with `read:workspace:bitbucket`; not with repository tokens, which have no `account` scope [B8] (added 2026-11-23) | workspace members and their permission | full list read | pass when complete, insufficient | weekly | dated list | IAM-02 partial, IAM-07 partial, IAM-12 partial |
| `ci.production_deploys_approved` (NEW) | Not implementable: Bitbucket has deployment permissions, not per deployment approvals. A deployment held by permissions waits for a permitted user to resume it [B7], and the REST 2.0 spec has no approval record for it [B8] | | | | | | SD-13 |

New check definitions are in `github.md` section 5.2.

## 6. Artifacts and objectives it fills

Without D-BB-1: `sample-of-reviewed-changes` (SD-01.B, SD-01.D, SD-06.B, SD-06.D, SD-14.C),
`change-requests-with-approval-for-a` (SD-01), `unreviewed-merge-log` and `emergency-changes-with-their-after-the`
(SD-04.B to D, SD-06.E), `test-run-results-for-a-sample` (SD-02.C, SD-02.D), `deployment-history-for-a-sample-of`
(SD-12.D, SD-13.B, C, E), `change-records-linking-request-review-and` (SD-14), `account-list-export`
(IAM-02.B, IAM-12.E), `list-of-privileged-accounts-with-approval` (IAM-07.B, partial). Each changes from
person to person + check.

With D-BB-1, also `branch-protection-settings` (SD-02.B, SD-06.C, SD-13.B).

Without D-BB-1, SD-06.C and SD-02.B (the merge gate settings) stay with a person: a screenshot or export
of the branch restrictions, dated, which the guide tells the customer how to take.

## 7. Framework reach

Controls: SD-01, SD-02, SD-04, SD-06, SD-13, SD-14, IAM-02, IAM-07, IAM-12.

- **SOC 2:** CC5.2, CC6.2, CC6.3, CC8.1, PI1.3.
- **ISO 27001:2022 Annex A:** A.5.3, A.5.16, A.5.18, A.8.2, A.8.4, A.8.18, A.8.19, A.8.25, A.8.28, A.8.29,
  A.8.30, A.8.32.

## 8. Limits and false assurance traps

- **Merge checks that only warn.** On Standard and Free a "require 2 approvals" restriction can be merged
  past [B5]. The setting check fails with `reason: plan`; `vcs.merged_changes_reviewed` shows what people
  actually did.
- **Merged outside the pull request.** If someone merges locally and pushes the merge commit to the
  target branch, Bitbucket marks the open pull request MERGED without its merge checks [B13]. Approvals
  are still read from the pull request, so the review check is unaffected, but the push restriction is
  what stops this.
- **The admin scope.** Granting `admin:repository:bitbucket` gives Verity's token the power to remove the
  very restrictions it checks. If granted, the token is stored like every credential and Verity never
  calls a write endpoint (enforced in the collector by allowing only GET); the customer still carries the
  risk of a stolen token.
- **Repository tokens per repository.** A new repository is invisible until someone adds a token for it.
  A repository token cannot list the workspace's other repositories (it reaches only its own [B2]), so
  with repository tokens the scope is only what was given, and the result says so (corrected 2026-11-23:
  was "the inventory comes from the workspace listing where any token can list it").
- **No alerting sources.** Secret, dependency and code scanning checks need GitHub, GitLab Ultimate or a
  scanner. A Bitbucket only customer has people's evidence for SD-03, SD-05 and SD-11.

## 9. Product and UI

Connect form: workspace id, token (workspace token) or a list of repository tokens; plan (Free, Standard,
Premium) asked once, because the workspace object has no plan field [B8]. Optional "also read branch restrictions" switch, off by
default, visible only if D-BB-1 is approved, with the warning text. Health: token expiry, missing scope,
repository without a token, rate limited. In product guide needed: yes (token type by plan, which boxes to
tick, why the admin box is not ticked).

## 10. Implementation notes

- REST 2.0 with `net/http`; follow `next` links; `pagelen` 100, the general maximum (default 10;
  individual endpoints may set other values) [B8].
- A GET only transport wrapper in the collector, so a token with admin scope can never be used to write.
- Rate limits: one request at a time per token by default [B6], `X-RateLimit-NearLimit` to slow down.
- Error mapping: 401 expired or revoked token; 403 missing scope (only the checks that need it are
  `error`); 404 repository removed (leaves scope with `last_seen`).
- Fixtures: a Standard workspace and a Premium workspace on the 30 day evaluation that every plan
  starts with [B12], recorded and scrubbed.

## 11. How comparable platforms do it

Not researched this round: the web search budget ran out before the Bitbucket pages of Vanta, Drata,
Secureframe and Sprinto were read (still unverified: competitor pages are outside the provider
documentation checked on 2026-11-23). Worth checking specifically how they read branch
restrictions without the admin scope.

## 12. Sources

- [B1] App password deprecation and API tokens: https://www.atlassian.com/blog/bitbucket/bitbucket-cloud-transitions-to-api-tokens-enhancing-security-with-app-password-deprecation ; brownout schedule: https://community.atlassian.com/forums/Bitbucket-articles/Deprecation-notice-Bitbucket-Cloud-app-password-brownout/ba-p/3237429 ; https://support.atlassian.com/bamboo/kb/bitbucket-cloud-repository-configuration-fails-in-bamboo-with-api-tokens/
- [B2] Access tokens (workspace, project, repository): https://support.atlassian.com/bitbucket-cloud/docs/access-tokens/ , https://support.atlassian.com/bitbucket-cloud/docs/workspace-access-tokens/ , https://support.atlassian.com/bitbucket-cloud/docs/repository-access-tokens/
- [B3] API token permissions: https://support.atlassian.com/bitbucket-cloud/docs/api-token-permissions/
- [B4] Branch restrictions REST: https://developer.atlassian.com/cloud/bitbucket/rest/api-group-branch-restrictions/ ; request to lower the scope: https://jira.atlassian.com/browse/BCLOUD-24231
- [B5] Bitbucket Premium (enforced merge checks): https://www.atlassian.com/software/bitbucket/premium ; custom merge checks: https://support.atlassian.com/bitbucket-cloud/docs/set-up-and-use-custom-merge-checks/
- [B6] API request limits: https://support.atlassian.com/bitbucket-cloud/docs/api-request-limits/ ; https://support.atlassian.com/bitbucket-cloud/kb/bitbucket-cloud-rate-limit-troubleshooting/
- [B7] Deployment permissions: https://support.atlassian.com/bitbucket-cloud/docs/set-custom-deployment-permissions-for-your-environments/
- REST API 2.0 reference (pull requests, pipelines, deployments, workspaces): https://developer.atlassian.com/cloud/bitbucket/rest/
- [B8] REST 2.0 OpenAPI spec, read 2026-11-23 for per endpoint scopes, schemas and query parameters: https://dac-static.atlassian.com/cloud/bitbucket/swagger.v3.json ; authentication, access token scope lists, API token expiry and OAuth grants: https://developer.atlassian.com/cloud/bitbucket/rest/intro/
- [B9] Secret scanning: Cloud pipe https://support.atlassian.com/bitbucket-cloud/kb/how-to-scan-only-the-latest-commits-for-secrets-using-the-git-secrets-scan-pipe/ ; Data Center built in scanning https://support.atlassian.com/bitbucket-data-center/kb/how-to-test-and-validate-bitbucket-secret-scanning-rules/
- [B10] Workspace access token permission labels: https://support.atlassian.com/bitbucket-cloud/docs/workspace-access-token-permissions/
- [B11] Required two step verification (Premium): https://support.atlassian.com/bitbucket-cloud/docs/control-access-to-private-content-in-a-workspace/
- [B12] 30 day evaluation on every plan: https://support.atlassian.com/bitbucket-cloud/docs/manage-your-plan-and-billing/
- [B13] Merge checks warn without Premium; `enforce_merge_checks`: https://support.atlassian.com/bitbucket-cloud/docs/suggest-or-require-checks-before-a-merge/ ; local merge bypass: https://support.atlassian.com/bitbucket-cloud/kb/why-a-pull-request-is-merged-despite-failing-the-merge-checks/

## Decisions for the owner

- **D-BB-1.** Branch restrictions need `admin:repository:bitbucket`, which can edit them. Options: (a) do
  not read them; the merge gate settings stay with people and Bitbucket proves practice only
  (recommended for Phase 2); (b) offer it as an opt in with an ADR, a GET only collector and a warning;
  (c) ask Atlassian, and revisit if a read scope ships.
- **D-BB-2.** Standard and Free workspaces: support repository tokens one by one (recommended for small
  teams), or require Premium workspace tokens. Note (2026-11-23): repository tokens cannot read the
  workspace member list, so option one also needs an API token of a dedicated account with
  `read:workspace:bitbucket` for `vcs.access_list_exported`, or leaves that check to a person.
- **D-BB-1 status (2026-11-23):** confirmed against the spec; branch restrictions still need the admin
  scope, so the recommendation (a) stands.
