# GitHub

| | |
|---|---|
| Capabilities | version_control (available), ci_cd (planned) |
| Delivery phase | Phase 2 (signed catalogue). Built: 7 checks on a fine grained token (`backend/src/verity/modules/connectors/github.py`, `README.md`) |
| Auth model | Today: fine grained personal access token, read only. Planned: a Verity GitHub App installed per organization, read permissions only |
| Shares setup with | Nothing. GitHub is not a Verity sign in provider |
| Go library | `github.com/google/go-github/v93/github` (hosted under Google's organization; GitHub's library page lists it as a third party library and names no official Go SDK [G14]). App auth: `github.com/jferrl/go-githubauth` is what the go-github README points to; `github.com/bradleyfalzon/ghinstallation/v2` is the common alternative (community; maintenance status unverified, not a GitHub documented library) |

## 1. What it proves

GitHub is where code changes are proposed, reviewed and merged, and for many customers where they are
tested and released. It proves the change control half of CC8.1 better than any other source: whether
the default branch only takes reviewed changes, whether each merged change was approved by someone else
before it merged, whether tests had to pass and did pass, how production deployments were gated, and
whether secret and dependency alerting is on and acted on. It also gives the account list for the code
system (members, owners, outside collaborators) and the two factor rule for it.

It does not prove that a change was authorised as a business decision (that is the ticket,
`tickets.changes_linked`), that tests are meaningful, or that anything outside GitHub (a laptop deploy,
another CI) followed the same path.

## 2. Connecting: method, credentials and permissions

### 2.1 What is built (review)

The token is fine grained and read only: Repository Metadata, Administration and Pull requests, and
Organization Administration for the two factor check. A missing permission makes only the checks that
need it `error`. Scope is per repository with reasons (AU-9), archived and forks out by default, 300
repositories and 100 merged changes per repository per run at most, with the population stated on the
result. One evidence file per check. This matches the authoring rules. Findings of the review:

| Finding | Effect | Proposal |
|---|---|---|
| A ruleset's bypass list is not read (README says so) | `vcs.default_branch_protected` can pass on a ruleset that every admin bypasses | Read `GET /repos/{o}/{r}/rulesets/{id}` (Metadata read) and add `vcs.protection_bypass_limited` |
| Direct pushes to the default branch are not looked for | `vcs.merged_changes_reviewed` reads merged pull requests only. A push that bypassed protection is not a pull request, so the check can pass while unreviewed code reached the branch (rule 4, empty is not proof) | Read rule suites (`GET /repos/{o}/{r}/rulesets/rule-suites`, Administration read, filter `rule_suite_result=bypass`, window up to a month) [G4]; and, if the owner accepts Contents read (D-GH-3), commits on the default branch not linked to a pull request. Feed both into `vcs.unreviewed_merges_recorded` |
| `vcs.status_checks_required` passes when any context is required | A required lint job satisfies "tests must pass" | Keep the predicate (it is the setting), print the required contexts on the result so a reviewer sees them, and judge the operating side with `ci.required_checks_passed` |
| Stale approvals are reported but not judged | An approval before later commits still counts (correct for GitHub's semantics) | Add `vcs.approval_resets_on_change` for the setting, keep the note on the evidence |
| The plan versus permission inference uses the repository's `permissions.admin` | With a GitHub App, that flag describes the installation, not a person (unverified). GitHub shows `security_and_analysis` only to repository admins, organization owners and security managers, and does not say whether an installation token with Administration read sees it [G15] | Re-derive for the App: the App holds Administration read on every installed repository, so an absent `security_and_analysis` means the plan. Test on a fixture first: if an installation token never sees the block, this inference would turn every repository into `reason: plan`, so the check must read `error` instead |
| Personal tokens tie the connection to one person | A leaver's token stops the connection; the token can see the person's own repositories | Move to a GitHub App (2.2) |

### 2.2 Why a GitHub App

GitHub's own reasons to prefer an app over a personal or OAuth token: narrow permissions (read only
where asked), the installer chooses which repositories, short lived tokens, the app is not tied to a
person (keeps working when they leave, uses no paid seat), rate limits that grow with the installation,
and one webhook setup for every repository [G1]. Concretely:

- **Installation.** An organization owner installs the app on the organization and selects all or some
  repositories. Each organization is one installation, so a customer with three organizations installs
  three times (one Verity connection each). A personal account can also install it.
- **Tokens.** Verity signs a JSON Web Token with the app's private key and exchanges it at
  `POST /app/installations/{installation_id}/access_tokens` for an installation token that lasts one hour.
  The token can be narrowed to listed repositories (up to 500) and permissions, never beyond the grant
  [G2]. Nothing long lived is held for the customer.
- **Rate limits.** Personal tokens share 5,000 requests per hour. Installation tokens start at 5,000,
  gain 50 per hour for each repository over 20 and each organization user over 20, up to 12,500; an
  installation on a GitHub Enterprise Cloud organization gets 15,000. Secondary limits: 100 concurrent
  requests, 900 points per minute for REST [G3].
- **Vendor side prerequisites.** The app is registered by a Verity owned GitHub organization and must be
  public to be installable on customer accounts: a private app installs only on the account that owns
  it [G16]. Organization owners install apps; a repository admin can install only an app that asks for
  no organization permissions and not for repository Administration. Verity's app asks for both, so only
  an organization owner can install it [G17]. The app's private key is Verity's most sensitive integration
  secret: kept in the runtime secret store, rotated, never in the database (`01-evidence-model.md` 1.5).
  Given the November 2026 incident on Verity's GitHub branches, the owner organization needs its own
  hardening before it hosts the app (D-GH-1).
- **Webhooks** are not needed: runs are daily pulls. Leave them off until continuous monitoring needs
  push events.

The fine grained token stays as the fallback (GitHub Enterprise Server without the app, or a customer who
refuses apps). Organization owners can require approval of each fine grained token (on by default,
except tokens created by owners), can block fine grained tokens altogether, and can cap their lifetime
(default 366 days); a token over the cap is blocked from the organization, not revoked [G18].

### 2.3 Permissions (GitHub App, all read)

Permission names are GitHub's. "Fine grained token" gives the same name where one exists [G4][G5].
Checked against [G5] on 2026-11-23: rule suites, classic branch protection, `vulnerability-alerts` and
code scanning default setup need Administration read; rules for a branch, rulesets and collaborators
need Metadata read; environments and run review history need Actions read; members and outside
collaborators need Members read; check runs need Checks read.

| Permission | Read only | Needed for (check keys) | Who grants it |
|---|---|---|---|
| Repository: Metadata (always granted) | yes | listing repositories, `GET .../rules/branches/{b}`, `GET .../rulesets/{id}`, repository collaborators: `vcs.default_branch_protected`, `vcs.review_required`, `vcs.status_checks_required`, `vcs.protection_bypass_limited`, `vcs.access_list_exported` | organization owner, at install |
| Repository: Administration | yes | classic branch protection, `vulnerability-alerts`, rule suites, code scanning default setup, `security_and_analysis`: `vcs.default_branch_protected`, `vcs.review_required`, `vcs.status_checks_required`, `vcs.approval_resets_on_change`, `vcs.protection_bypass_limited`, `vcs.dependency_alerts_enabled`, `vcs.secret_scanning_enabled`, `vcs.push_protection_enabled`, `vcs.code_scanning_enabled`, `vcs.unreviewed_merges_recorded` | organization owner |
| Repository: Pull requests | yes | merged pull requests and reviews: `vcs.merged_changes_reviewed`, `vcs.unreviewed_merges_recorded`, `ci.required_checks_passed` | organization owner |
| Repository: Checks | yes | check runs for a commit: `ci.required_checks_passed` (GitHub App only; not listed for fine grained tokens) | organization owner |
| Repository: Commit statuses | yes | combined status: `ci.required_checks_passed` | organization owner |
| Repository: Actions | yes | workflow runs, environments and their protection rules, deployment review history (`GET .../actions/runs/{run_id}/approvals`): `ci.production_deploys_controlled`, `ci.production_deploys_approved` | organization owner |
| Repository: Deployments | yes | deployments and statuses: `ci.deployment_history_recorded`, `ci.production_deploys_approved` | organization owner |
| Repository: Dependabot alerts | yes | `vcs.dependency_alerts_within_sla` | organization owner |
| Repository: Secret scanning alerts | yes | `vcs.secret_alerts_closed_in_time` | organization owner |
| Repository: Code scanning alerts | yes | code scanning analyses and alerts: `vcs.code_scanning_enabled` | organization owner |
| Organization: Members | yes | members with roles and the two factor filters, outside collaborators: `vcs.access_list_exported` | organization owner |
| Organization: Administration | yes | `two_factor_requirement_enabled`: `vcs.org_two_factor_required`; the audit log on Enterprise Cloud (`GET /orgs/{org}/audit-log` needs Organization Administration read, confirmed [G19]) | organization owner |
| Repository: Contents | yes, but it reads source code | only if D-GH-3 accepts it: commits on the default branch for direct push detection | organization owner |

Plan and edition requirements [G6][G7][G8][G9]:

| Feature | Public repositories | Private repositories |
|---|---|---|
| Branch protection and rulesets | all plans | GitHub Pro, Team, Enterprise Cloud, Enterprise Server |
| Environments, deployment branch rules, environment secrets | all plans | Pro, Team, Enterprise |
| Required reviewers and wait timers on environments | all plans | Enterprise only: on Free, Pro and Team both are for public repositories only (confirmed 2026-11-23 [G8]). The plan FAQ line "required reviewers in private repositories" sits in a 2020 downgrade list and does not mention environments, so it is not taken as a conflict |
| Secret scanning, push protection | free | requires GitHub Secret Protection, sold to Team and Enterprise Cloud since 1 April 2025 |
| Code scanning | free | requires GitHub Code Security, sold to Team and Enterprise Cloud since 1 April 2025 |
| Dependabot alerts | all plans | all plans: GitHub documents alerts for public, private and internal repositories with no plan condition; only assigning alerts needs Code Security [G20] |
| Organization audit log API | | GitHub Enterprise Cloud only: web events for 180 days, Git events for 7 days (`read:audit_log` for classic tokens) |

A feature the plan does not offer is `fail` with `reason: plan` and the ways out, as built (README
"Outcomes"). The same rule applies to the new checks.

## 3. Customer setup guide (draft product text, GitHub App)

1. In Verity, open Integrations, choose GitHub and click **Connect**. You need to be an owner of the
   GitHub organization.
2. GitHub opens the Verity app's install page. It lists every permission Verity asks for. All are read
   only, and none of them can read your code.
3. Choose the organization, then **All repositories** or **Only select repositories**, and click
   **Install**.
4. GitHub returns you to Verity. Verity lists the repositories it can see. Untick any that are not part of
   the system you are audited on and give a reason (archived repositories and forks are already left out).
5. Mark which repositories deploy to production, and the name of your production environment if it is
   not "production".
6. Click **Run checks**. Results appear on the controls within a few minutes.

Repeat for each GitHub organization. To change which repositories Verity sees, use the app's settings in
GitHub (Settings, GitHub Apps, Verity, Configure). To disconnect, uninstall the app; Verity keeps the
history.

## 4. What Verity collects

| Resource | API (endpoint) | Fields kept | Paging and limits | Provider retention |
|---|---|---|---|---|
| Account | `GET /orgs/{org}` | login, name, `two_factor_requirement_enabled` | single | live |
| Repositories | `GET /orgs/{org}/repos` or `GET /installation/repositories` | id, name, private, fork, archived, default branch, `security_and_analysis` | 100 per page, 300 in scope cap (built) | live |
| Branch policy | `GET /repos/{o}/{r}/branches/{b}/protection`, `GET /repos/{o}/{r}/rules/branches/{b}`, `GET /repos/{o}/{r}/rulesets/{id}` | protection, rules, ruleset bypass actors | per repository | live |
| Bypassed and evaluated pushes | `GET /repos/{o}/{r}/rulesets/rule-suites?ref=&time_period=month&rule_suite_result=bypass` | actor, ref, before and after SHA, pushed at, result | `time_period` is hour, day (the default), week or month; `rule_suite_result` is pass, fail, bypass or all [G10] | at most a month through the filter (how long GitHub keeps rule suites is not stated: unverified) |
| Merged changes and reviews | `GET /repos/{o}/{r}/pulls?state=closed&base=`, `GET .../pulls/{n}/reviews` | as built: number, author, merged at, head SHA, every review (user, state, submitted at, commit) | 500 closed read, 100 merged kept per repository | live |
| CI results | `GET /repos/{o}/{r}/commits/{sha}/check-runs`, `GET /repos/{o}/{r}/commits/{sha}/status`, `GET /repos/{o}/{r}/actions/runs?head_sha=` | check name, app, conclusion, completed at; status contexts and state | per merged change, bounded by the rate limit floor | Actions artifacts and logs: 90 days by default (public 1 to 90, private 1 to 400); since 1 October 2026 workflow run records follow the same setting [G21] |
| Environments | `GET /repos/{o}/{r}/environments` | name, `protection_rules` (`required_reviewers` with reviewers and `prevent_self_review`, `wait_timer`, branch policy), `deployment_branch_policy` (`protected_branches`, `custom_branch_policies`) [G8] | per repository | live |
| Deployments | `GET /repos/{o}/{r}/deployments?environment=`, `GET .../deployments/{id}/statuses`, `GET .../actions/runs/{run_id}/approvals` | sha, ref, creator, created at, environment, latest state; approvals: `environments`, `state` (approved, rejected, pending), `user`, `comment`. An approval carries no timestamp of its own [G22] (corrected 2026-11-23: was "comment time"); the gate holds the job until approved, so order is implied, not dated | last 30 days, 100 per repository | live |
| Dependabot alerts | `GET /repos/{o}/{r}/dependabot/alerts?state=open` (and dismissed, fixed in window) | number, state, severity, advisory id (GHSA, CVE), package, created, dismissed, dismissed reason, fixed, auto dismissed | paginated | live |
| Secret scanning alerts | `GET /repos/{o}/{r}/secret-scanning/alerts?hide_secret=true` | number, state, resolution, secret type, validity, push protection bypassed, created, resolved, publicly leaked, multi repository. **The `secret` field holds the secret itself unless `hide_secret=true`** [G11]; Verity always sets it and drops the field if present | paginated | live |
| Code scanning | `GET /repos/{o}/{r}/code-scanning/default-setup`, `GET .../code-scanning/analyses?ref=` | state, languages, last analysis date | paginated | live |
| People | `GET /orgs/{org}/members?role=admin`, `?filter=2fa_disabled`, `?filter=2fa_insecure` (owners only), `GET /orgs/{org}/outside_collaborators`, `GET /repos/{o}/{r}/collaborators?permission=admin` | login, role, two factor state where visible, repository admin | paginated | live |
| Audit log (Enterprise Cloud only, optional) | `GET /orgs/{org}/audit-log` | branch protection and ruleset changes, membership changes, bypass events | default three months of results unless a date is given | 180 days web, 7 days Git [G9] |

Nothing is written to GitHub. Code, issues, comments and secrets are not read.

## 5. Checks

Population for every per repository check: in scope repositories (AU-9 scope, archived out). Outcomes as
built (README): `error` for permission or outage, `fail` with `reason: plan` for a plan limit,
`not_applicable` for an empty repository, `insufficient_information` when the population was cut short
(the built connector reports this as `error`; `01-evidence-model.md` 1.3 names the outcome). Period:
settings are read daily and the history is the Type 2 record; event checks use a 30 day window.

### 5.1 Existing checks

| Check | Status on GitHub | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls |
|---|---|---|---|---|---|---|---|
| `vcs.default_branch_protected` | built | default branch of each repository | direct and force pushes blocked by classic protection or a ruleset | as built | daily | protection, rules | SD-06 partial, SD-01 partial (as shipped) |
| `vcs.review_required` | built | same | at least one approving review required | as built | daily | review settings | SD-06 partial, SD-01 partial |
| `vcs.status_checks_required` | built | same | at least one required status check | as built; add the contexts to the summary | daily | required contexts | SD-02 partial |
| `vcs.merged_changes_reviewed` | built | pull requests merged into the default branch in 30 days | each had an approval before merge by someone other than the author (last decision per reviewer) | as built | daily | `merged_changes` | SD-01 partial, SD-06 partial |
| `vcs.secret_scanning_enabled` | built | repositories | secret scanning on | as built (plan aware) | daily | `security_and_analysis` | SD-11 partial |
| `vcs.dependency_alerts_enabled` | built | repositories | Dependabot alerts on | as built | daily | `vulnerability_alerts` | SD-03 partial, LM-11 partial |
| `vcs.org_two_factor_required` | built | the organization | organization requires two factor | as built; add counts from `2fa_insecure` to the evidence when visible | daily | account | IAM-03 partial |
| `vcs.code_scanning_enabled` | feasible | repositories with a language CodeQL supports: C and C++, C#, Go, Java and Kotlin, JavaScript and TypeScript, Python, Ruby, Rust, Swift, and GitHub Actions workflows [G23] | default setup is `configured`, or an analysis of the default branch exists from the last 30 days | pass; fail; fail `reason: plan` for a private repository without Code Security; error | daily | setup state, last analysis | SD-05 partial (as shipped) |
| `vcs.unreviewed_merges_recorded` | feasible, needs a Verity record | merged changes in 30 days without an approving review (from `vcs.merged_changes_reviewed`), rule suite bypasses on the default branch, and direct pushes if D-GH-3 allows | each item is linked in Verity to an after the fact review: a task linked to the change, closed by someone other than the change's author within the window the emergency procedure sets (setting, default 5 working days) | pass (all reviewed, or none found with a complete population); fail with the items; error; insufficient when rule suites could not be read | daily | items, linked review, reviewer, date | SD-04 partial, SD-06 partial (as shipped). Depends on the `links` primitive between a task and an external change |
| `ci.required_checks_passed` | feasible | merged changes in 30 days | for each, every required context (from protection or rules) concluded `success` on the merged head commit before `merged_at`; when none is required, at least one check ran and none failed | pass; fail with changes and contexts; error; insufficient (rate floor reached) | daily | change, commit, context, conclusion, completed at | SD-02 partial (as shipped) |
| `ci.production_deploys_controlled` | feasible | repositories marked as deploying production, their production environment (setting) | the environment exists and either has required reviewers (with `prevent_self_review`) or allows deployment only from protected branches or named branch and tag rules | pass; fail; fail `reason: plan` (private, required reviewers need Enterprise per current docs); error | daily | environment, rules | SD-13 partial (as shipped) |
| `ci.deployment_history_recorded` | feasible | deployments to the production environment in 30 days | each has commit, ref, creator and time, and a final status | pass; fail; insufficient when a repository marked as deploying has no deployment record (it may deploy from elsewhere: empty is not proof); error | daily | deployments | SD-13 partial, SD-14 partial (as shipped) |

### 5.2 New checks

| Check key (NEW) | Population | Predicate | pass / fail / error / insufficient | Frequency | Evidence kept | Controls (code, coverage, rationale) |
|---|---|---|---|---|---|---|
| `vcs.protection_bypass_limited` | default branch policy of each repository | classic protection includes administrators (`enforce_admins`), and every ruleset on the default branch has no bypass actors other than those the customer allows in settings (default none, or deploy automation only) | pass; fail with actors; error when a ruleset could not be read | daily | enforce admins, bypass actors and mode | SD-06 partial: "bypass limited" in SD-06.C. SD-04 partial: the emergency route is bounded to named people |
| `vcs.approval_resets_on_change` | same | approvals are dismissed on new commits, or the most recent push must be approved by someone else. Classic: `required_pull_request_reviews.dismiss_stale_reviews` or `require_last_push_approval` [G6]; ruleset `pull_request` rule: `dismiss_stale_reviews_on_push` or `require_last_push_approval` [G24] (names confirmed) | pass; fail; error | daily | the setting and its source | SD-06 partial: the approval covers what actually merges. SD-01 partial: the approved change is the released change |
| `vcs.push_protection_enabled` | repositories | secret scanning push protection is on | pass; fail; fail `reason: plan`; error | daily | `security_and_analysis.secret_scanning_push_protection.status` (`enabled` or `disabled`; field name confirmed [G15]) | SD-11 partial: secrets are blocked before they land, not only found after. NS-09 partial: supports "no secrets in source code" |
| `vcs.secret_alerts_closed_in_time` | secret scanning alerts open now or resolved in 30 days | no alert open longer than the setting (default 7 days); every push protection bypass in the window has an alert that was resolved | pass; fail with alerts; not_applicable when none and scanning is on; error; insufficient | daily | alerts without the secret value | SD-11 partial: exposed secrets were dealt with in time (SD-11.C); rotation proof and misuse review (SD-11.D) are people's. NS-09 partial (NS-09.D) |
| `vcs.dependency_alerts_within_sla` | Dependabot alerts open now or closed in 30 days | no open alert is older than the workspace's vulnerability timeframe for its severity (from the vulnerabilities module settings); each dismissal has a reason | pass; fail; not_applicable when none and alerts are on; error; insufficient | daily | alerts: severity, advisory, created, dismissed or fixed and reason | SD-03 partial: alerts are triaged and fixed in time (SD-03.D, SD-03.E). LM-11 partial: one finding source fixed within timeframes (LM-11.D). See D-GH-2 |
| `vcs.access_list_exported` | organization members with role, outside collaborators, admins of in scope repositories | the full list was read (population export) | pass when complete; insufficient otherwise; error | weekly | dated list with roles and two factor state where visible | IAM-02 partial: the account list for the code system (IAM-02.B). IAM-07 partial: owners and repository admins are the privileged accounts (IAM-07.B). IAM-12 partial: leavers still in the organization become visible (IAM-12.E) |
| `ci.production_deploys_approved` | production deployments in 30 days in repositories marked as deploying | each ran from the default branch or a tag, and, where the environment requires reviewers, carries an approval by someone other than the person who triggered the run (link from deployment to run: unverified; the workflow run object has no deployment field [G22], so the link must come from the deployment status URL or the run's pending deployments, to be tested on a fixture) | pass; fail with deployments; insufficient when approvals could not be linked; error | daily | deployment, ref, run, approver, time | SD-13 partial: each release was approved before it ran (SD-13.C) and came from a protected source (SD-13.B). SD-12 partial: nothing went straight to production outside the path (SD-12.D support) |

Definition fields for `checks.json`:

| Key | Name | Capabilities | Planned providers | Resource type | Remediation (product text) | Evidence kinds |
|---|---|---|---|---|---|---|
| `vcs.protection_bypass_limited` | Nobody bypasses branch protection | version_control | github, gitlab, bitbucket | repository | Include administrators in the rule and remove bypass permissions that are not needed. | Branch protection settings; Ruleset bypass list |
| `vcs.approval_resets_on_change` | New commits need a new approval | version_control | github, gitlab, bitbucket | repository | Dismiss approvals when new commits are pushed, or require approval of the latest push. | Required review settings |
| `vcs.push_protection_enabled` | Secret pushes are blocked | version_control | github, gitlab | repository | Turn on push protection in the repository's security settings. | Repository security settings |
| `vcs.secret_alerts_closed_in_time` | Exposed secrets are dealt with | version_control | github, gitlab | repository | Rotate the exposed secret, then resolve the alert as revoked. | Secret scanning alerts |
| `vcs.dependency_alerts_within_sla` | Dependency alerts are fixed in time | version_control | github, gitlab | repository | Update or patch the dependency, or dismiss the alert with a reason. | Dependency alerts |
| `vcs.access_list_exported` | Code access list is exported | version_control | github, gitlab, bitbucket | organization | Connect every organization so the list is complete. | Members, admins and outside collaborators |
| `ci.production_deploys_approved` | Production releases were approved | ci_cd | github, gitlab | deployment | Require reviewers on the production environment and deploy only from the default branch. | Deployment history; Deployment approvals |

## 6. Artifacts and objectives it fills

| Artifact key (artifacts.json) | Objective codes | Control | Change |
|---|---|---|---|
| `branch-protection-settings` | SD-02.B, SD-06.C, SD-13.B | SD-06 | already lists `vcs.default_branch_protected`, `vcs.review_required`; add `vcs.status_checks_required` (SD-02.B judges exactly that setting), `vcs.protection_bypass_limited`, `vcs.approval_resets_on_change` (full for in scope repositories) |
| `sample-of-reviewed-changes` | SD-01.B, SD-01.D, SD-06.B, SD-06.D, SD-14.C | SD-06 | already lists `vcs.merged_changes_reviewed` (full for the 30 day window when the population is complete) |
| `change-requests-with-approval-for-a` | SD-01.B to SD-01.E, SD-09.D | SD-01 | already lists `vcs.merged_changes_reviewed` with `tickets.changes_linked` |
| `unreviewed-merge-log` | SD-04.B, SD-06.E | SD-04 | already lists `vcs.unreviewed_merges_recorded`; GitHub becomes its first implementation |
| `emergency-changes-with-their-after-the` | SD-04.B, SD-04.C, SD-04.D | SD-04 | same check (partial: the reason recorded at the time, SD-04.C, is a person's) |
| `test-run-results-for-a-sample` | SD-02.C, SD-02.D, SD-03.C, SD-09.C | SD-02 | already lists `ci.required_checks_passed` (full for merged changes in the window) |
| `deployment-history-for-a-sample-of` | SD-12.D, SD-13.B, SD-13.C, SD-13.E | SD-13 | already lists `ci.deployment_history_recorded`; add `ci.production_deploys_approved` |
| `change-records-linking-request-review-and` | SD-14.B to SD-14.E | SD-14 | already lists `ci.deployment_history_recorded` |
| `open-alerts-triaged-within-the-timeframe` | SD-03.B, SD-03.D, SD-03.E | SD-03 | person -> person + `vcs.dependency_alerts_enabled`, `vcs.dependency_alerts_within_sla` (partial: container images not covered) |
| `records-of-exposed-secrets-that-were` | SD-11.B to SD-11.E, NS-09.D | SD-11 | person -> person + `vcs.secret_scanning_enabled`, `vcs.push_protection_enabled`, `vcs.secret_alerts_closed_in_time` (partial: rotation and misuse review are people's) |
| `evidence-validation-was-tested` | SD-05.B | SD-05 | person -> person + `vcs.code_scanning_enabled` (partial) |
| `second-factor-enforcement-and-enrolled-users` | IAM-03.B | IAM-03 | person -> person + `vcs.org_two_factor_required`. Today the check maps to IAM-03 but no artifact names it, so it changes no objective (reconciliation gap) |
| `account-list-export` | IAM-02.B, IAM-12.E | IAM-02 | add `vcs.access_list_exported` (full for the code system) |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, SD-13.D | IAM-07 | add `vcs.access_list_exported` (partial: the approval of each grant is a person's) |
| `asset-inventory` | SD-06.B, SD-11.B, SD-03.B | LM-01 | NEED asset_discovery: the in scope repository list with exclusions is the repository population these objectives test. GitHub is not an `asset_discovery` provider in `capabilities.json` (D-GH-4) |

Objectives no GitHub data can prove: every `.A` design objective, SD-04.E (management review of
emergency rates), SD-10 (secure development design reviews and training), SD-14.D (retention), and the
human halves named above.

## 7. Framework reach

Controls: SD-01 to SD-06, SD-11 to SD-14, LM-11, IAM-02, IAM-03, IAM-07, IAM-12, NS-09.

- **SOC 2:** CC5.2, CC6.1, CC6.2, CC6.3, CC6.8, CC7.1, CC8.1, PI1.2, PI1.3.
- **ISO 27001:2022 Annex A:** A.5.3, A.5.16, A.5.17, A.5.18, A.5.21, A.5.32, A.8.2, A.8.4, A.8.5, A.8.8,
  A.8.18, A.8.19, A.8.25, A.8.26, A.8.28, A.8.29, A.8.30, A.8.31, A.8.32.

## 8. Limits and false assurance traps

- **A pull request population does not show direct pushes.** See the review in 2.1. Until rule suites or
  commits are read, a clean `vcs.merged_changes_reviewed` says "every pull request was reviewed", not
  "every change was".
- **Rulesets with bypass.** A ruleset that admins bypass blocks nobody who matters. `vcs.protection_bypass_limited`.
- **Protection today, not throughout.** Daily reads give a history; a rule turned off and back on between
  two runs is invisible without the audit log (Enterprise Cloud only, 180 days).
- **Required checks named by the customer.** A required lint job passes `vcs.status_checks_required`. The
  contexts are printed; whether they test processing (SD-02.E) is a person's judgement.
- **Approvals on old commits** count under GitHub's rules; listed, and judged by `vcs.approval_resets_on_change`.
- **Environment gates and plans.** Required reviewers on private repositories are documented as Enterprise
  only. A Team customer with a "production" environment and branch rules passes
  `ci.production_deploys_controlled` through the branch rule, and the evidence says no person approved.
- **Deployments outside GitHub.** Argo, Spinnaker, a laptop or a cloud console leave no GitHub deployment.
  `ci.deployment_history_recorded` gives `insufficient_information` for repositories marked as deploying
  with no records, never a pass.
- **Secret values.** The secret scanning API returns the secret unless `hide_secret=true` [G11]. The
  collector always sets it and strips the field defensively.
- **Personal accounts.** Two factor cannot be required by a personal account: `not_applicable`, and IAM-03
  needs another source.

## 9. Product and UI

Connect: **Install the GitHub App** (default) or **Use a token** (fallback, shows the four permissions).
After install: repository picker with reasons (built), the "deploys production" flag per repository, the
production environment name (default `production`), allowed bypass actors, the emergency review window.
Health: installed; permission missing (after the customer declines a new permission on an app update);
suspended installation; repositories over the cap; rate limit floor reached. In product guide needed: yes
for the token fallback (which boxes to tick); a short one for the app (owner role needed, which
repositories to choose).

## 10. Implementation notes

- **Port, not rewrite.** The Python collector stays until the Go runtime runs one provider in production;
  then it is ported with a parity test on recorded fixtures (`01-evidence-model.md` 1.5). The App support
  can land in Python first: only the token source changes.
- **Auth.** App JWT (`exp` at most 10 minutes ahead, `iat` set 60 seconds back for clock drift, RS256
  [G25]) signed with the private key from the secret store; installation token per run, narrowed to the in scope repositories and the read
  permissions; refresh on expiry (one hour).
- **Paging and limits.** `per_page=100`, `Link` headers; respect the primary and secondary limits [G3];
  keep the built rate floor (100 remaining) that skips, never fails, the rest.
- **Error mapping.** As built: 404 on optional settings is absent, 403 with the plan message is `reason:
  plan`, other 403 is `error`. Secret scanning 404 means public repository, scanning off or not found
  [G11]; tell them apart with `security_and_analysis`.
- **Fixtures.** Recorded per endpoint and plan (Free private, Team, Enterprise Cloud), scrubbed of logins.
- **Scope drift.** An app update that adds a permission waits for the owner's approval in GitHub; until
  then the new checks are `error` with "approve the new permission".
- **Deletion.** A repository that disappears or is removed from the installation leaves
  `connection_resources` with `last_seen`; history stays.

## 11. How comparable platforms do it

| Platform | Auth model | What it tests |
|---|---|---|
| Vanta | GitHub App, read only by default (optional write for task sync); owner role needed to connect; all or selected repositories | Branch protection, pull request structure, time to close security issues; does not collect GitHub Actions or CI/CD data [C1] |
| Drata, Secureframe, Sprinto | Not researched (competitor pages are outside the provider documentation checked on 2026-11-23) | unverified |

Verity can go further than the one source read: CI results per merged change, deployment approvals and
bypass history.

## 12. Sources

- [G1] Deciding when to build a GitHub App: https://docs.github.com/en/apps/creating-github-apps/about-creating-github-apps/deciding-when-to-build-a-github-app
- [G2] Generating an installation access token: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-an-installation-access-token-for-a-github-app
- [G3] Rate limits for the REST API: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
- [G4] Permissions required for fine grained personal access tokens: https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens
- [G5] Permissions required for GitHub Apps: https://docs.github.com/en/rest/authentication/permissions-required-for-github-apps
- [G6] Branch protection REST (plan statement): https://docs.github.com/en/rest/branches/branch-protection
- [G7] GitHub Secret Protection and Code Security for Team: https://github.blog/changelog/2025-04-01-github-advanced-security-is-here-for-github-team-organizations/ and https://docs.github.com/en/get-started/learning-about-github/about-github-advanced-security
- [G8] Deployment environments REST: https://docs.github.com/en/rest/deployments/environments ; Deployments and environments: https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments ; plan FAQ: https://docs.github.com/en/get-started/learning-about-github/faq-about-changes-to-githubs-plans
- [G9] Organization audit log (Enterprise Cloud): https://docs.github.com/en/enterprise-cloud@latest/organizations/keeping-your-organization-secure/managing-security-settings-for-your-organization/reviewing-the-audit-log-for-your-organization
- [G10] Rule suites REST: https://docs.github.com/en/rest/repos/rule-suites
- [G11] Secret scanning REST: https://docs.github.com/en/rest/secret-scanning/secret-scanning
- [G12] Organization members REST: https://docs.github.com/en/rest/orgs/members
- [G13] go-github: https://github.com/google/go-github
- [G14] Libraries for the REST API (go-github listed as third party): https://docs.github.com/en/rest/using-the-rest-api/libraries-for-the-rest-api
- [G15] Repositories REST (`security_and_analysis` keys and who sees them): https://docs.github.com/en/rest/repos/repos
- [G16] Making a GitHub App public or private: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/making-a-github-app-public-or-private
- [G17] Installing a GitHub App from a third party: https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party
- [G18] Personal access token policy for an organization: https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/setting-a-personal-access-token-policy-for-your-organization
- [G19] Organization audit log REST (Organization Administration read): https://docs.github.com/en/enterprise-cloud@latest/rest/orgs/orgs
- [G20] Configuring Dependabot alerts: https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/secure-your-dependencies/configure-dependabot-alerts ; About Dependabot alerts: https://docs.github.com/en/code-security/dependabot/dependabot-alerts/about-dependabot-alerts
- [G21] Actions artifact and log retention: https://docs.github.com/en/organizations/managing-organization-settings/configuring-the-retention-period-for-github-actions-artifacts-and-logs-in-your-organization
- [G22] Workflow runs REST (review history fields): https://docs.github.com/en/rest/actions/workflow-runs
- [G23] CodeQL supported languages: https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql
- [G24] Repository rules REST (`pull_request` rule parameters, bypass actors): https://docs.github.com/en/rest/repos/rules
- [G25] Generating a JWT for a GitHub App: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-json-web-token-jwt-for-a-github-app
- [C1] Vanta GitHub integration guide: https://help.vanta.com/en/articles/14845240-github-integration-guide and quickstart https://help.vanta.com/en/articles/14844982-github-quickstart

## Decisions for the owner

- **D-GH-1.** Build the Verity GitHub App now (recommended: yes, it removes the leaver problem and the
  personal repository noise), and under which GitHub organization, given the November 2026 incident.
- **D-GH-2.** Dependabot and secret scanning alerts: judge them in GitHub checks
  (`vcs.dependency_alerts_within_sla`, as proposed), or import them into the Verity vulnerability register so
  `verity.vulns.within_sla` judges every source in one place (what LM-11.C asks for, but a module change,
  spec first). Recommended: the check now, the import later.
- **D-GH-3.** Direct push detection needs Contents read, which can read source code. Recommended: no;
  rely on rule suites (Administration read) and say on the result that pushes outside rulesets are not
  seen.
- **D-GH-4.** Count in scope repositories as assets (GitHub as an `asset_discovery` provider), so SD-06.B,
  SD-03.B and SD-11.B can test "every repository is in scope" against the register.
