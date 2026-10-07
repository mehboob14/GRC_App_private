# Connectors

Checks are content (`seed/content/automation/`): each names the capabilities it needs
and the providers that implement it, and maps to control templates. A connection is a
workspace's read only link to one provider account. A run collects once, evaluates every
implemented check, appends one `check_results` row per check and resource, files the
snapshot as evidence on the mapped controls, and updates the connection's health.

## GitHub

What a customer grants. Use a **fine grained personal access token**, read only, scoped
to the organisation (or the user) and the repositories Verity should check:

| Permission | Level | Needed for |
|---|---|---|
| Repository: Metadata | Read | Listing repositories (always granted) |
| Repository: Administration | Read | Branch protection, Dependabot alerts setting, secret scanning setting |
| Repository: Pull requests | Read | Merged changes and their reviews |
| Organization: Administration | Read | Whether the organisation requires two factor |

A missing permission turns only the checks that need it into `error` ("could not
check"), never `fail`. A classic token also works but cannot be read only; prefer fine
grained.

What Verity reads, per repository **in scope**: the default branch, classic branch
protection, rulesets that apply to the default branch, the Dependabot alerts setting, the
secret scanning setting, and pull requests merged into the default branch in the last 30
days with every review of each (who decided what, when, and on which commit), up to 100 per
repository per run, reading as many as 500 closed pull requests to find them. Nothing is
written to GitHub.

### Scope

A token reaches every repository its owner can read, which for a personal account is every
fork and every piece of coursework. A SOC 2 engagement covers named systems, so each run
lists everything the token can see into `connection_resources` and checks only what is in
scope (AU-9).

- Archived repositories and forks are out by default, with a system reason that is
  re-derived on every run. Archived stays out whatever anyone decides.
- A person's decision (Connections, **Choose repositories**) is kept until a person changes
  it. A run never overwrites it.
- Leaving a repository out needs a reason. It is stored on the repository (and refused by a
  database CHECK without one), written to the audit log, and printed on the evidence's
  `verity.scope.excluded`, so an auditor reading a clean result knows what it was clean over.

### Outcomes

| Outcome | Means |
|---|---|
| `pass` / `fail` | The setting was read and does / does not meet the check |
| `error` | Verity could not tell (token, permission, rate limit, outage). Never a failure (rule 7) |
| `not_applicable` | Nothing to check: a repository with no commits, a personal account and two factor. Counts neither as a pass nor a fail |

| `stale` | Not a result but a reading of one: the last run is older than two days (one missed run is tolerated, two are not). Shown instead of pass or fail, and blocks readiness |

A plan that does not offer a setting is a `fail` with its own remedy, not an `error`: with
admin on the repository, the setting being absent means the plan, not the token. The
result's `detail.reason` is `plan` and its summary names the feature and the ways out
("GitHub does not offer secret scanning for this private repository on its current plan.
Upgrade the plan, make the repository public, or exclude it with a reason."). The control
page says it once per account instead of per repository, withholds the how-to-fix hint that
cannot apply, and offers **Leave these out**, which opens the repository picker with those
repositories unticked. A control whose every result is not applicable reads "Nothing to
verify", never "Passing".

| Check | Passes when |
|---|---|
| `vcs.default_branch_protected` | Direct pushes are blocked (a pull request is required, pushes are restricted or the branch is locked, by a classic rule or a ruleset) and force pushes are blocked. Protection that only stops deletion does not count |
| `vcs.review_required` | At least one approving review is required to merge |
| `vcs.status_checks_required` | Required status checks must pass before merge |
| `vcs.merged_changes_reviewed` | Every change merged in the last 30 days had an approving review before it merged, from someone other than its author |
| `vcs.secret_scanning_enabled` | Secret scanning is on |
| `vcs.dependency_alerts_enabled` | Dependabot alerts are on |
| `vcs.org_two_factor_required` | The organisation requires two factor (not applicable to a personal account) |

### Checks, controls, criteria and evidence

Each check supports controls (full or partial), and each control answers SOC 2 criteria.
Generated from the shipped content, not written by hand:

| Check | Controls it supports | SOC 2 criteria | What the evidence file holds |
|---|---|---|---|
| `vcs.default_branch_protected` | SD-06 (partial), SD-01 (partial) | CC8.1 | per repository: `protection` (including whether administrators can bypass it), `rules` |
| `vcs.review_required` | SD-06 (partial), SD-01 (partial) | CC8.1 | `protection.required_pull_request_reviews`, ruleset `pull_request` |
| `vcs.merged_changes_reviewed` | SD-01 (partial), SD-06 (partial) | CC8.1 | `merged_changes`: PR, author, head commit, every review with reviewer, decision, time and commit, last 30 days, up to 100 per repository |
| `vcs.status_checks_required` | SD-02 (partial) | CC8.1, PI1.3 | `protection.required_status_checks`, ruleset `required_status_checks` |
| `vcs.secret_scanning_enabled` | SD-11 (partial) | CC6.1, CC7.1 | `security_and_analysis.secret_scanning` |
| `vcs.dependency_alerts_enabled` | SD-03 (partial), LM-11 (partial) | CC6.8, CC7.1 | `vulnerability_alerts` |
| `vcs.org_two_factor_required` | IAM-03 (partial) | CC6.1 | `account.two_factor_required` |

**One evidence file per check.** A run files each check's results as its own evidence item,
linked only to the controls that check supports (SD-11 holds the secret scanning file and
nothing about branch protection). A check that found nothing an auditor can use, only errors or
not applicable results, files nothing. The file carries `verity.check` (key, name,
description), `verity.scope` (what was checked and every exclusion with its reason), that
check's results (`check`, `name`, `resource`, `outcome`, `summary`, `reason`) and the part of the
snapshot it read (`evidence_snapshot` in `github.py`: protection and rules for the three
branch checks, `merged_changes`, `security_and_analysis`, `vulnerability_alerts`, or the account
alone for two factor).

It is named for what it evidences, where and when: `Secret scanning is on: GitHub devuser,
6 Oct 2026 14:05 UTC`, because a check whose results changed files again within the day. It
is filed with `source` (the provider), `external_id` (`connection:check:digest:run`) and
`synced_at` (rule 9); the digest is how the next run tells a repeat from a new result, so a
check files again only when its results changed or its last file is more than 20 hours old.
`check_runs.evidence_id` is no longer set: a run has no single file.

The evidence page reads it as a report (what was checked, what was left out and why, what the
check found) with the raw file behind a toggle, and the original JSON downloads from the header.
A file that is not in this shape opens as plain text. Files filed before this held every
check of the run and were linked to every control any of them touched; the evidence page still
reads them, and `python -m scripts.retire_legacy_connector_evidence --apply` unlinks them from
the controls (nothing is deleted, each unlink is audited) once a run on the new code has filed
the per-check evidence.

**What GitHub can and cannot prove.** It speaks for part of five criteria, not all of them:

| Criterion | Controls mapped | GitHub tests | Still needs other evidence |
|---|---|---|---|
| CC8.1 changes | 8 | SD-01, SD-02, SD-06 (partial) | SD-04 emergency change, SD-10 secure SDLC policy, SD-12 separate environments, SD-13 controlled deployments and SD-14 change traceability (pipeline and ticket checks, planned) |
| CC7.1 detection | 7 | SD-03, SD-11, LM-11 (partial) | scanning of infrastructure, configuration drift, penetration test |
| CC6.1 logical access | 16 | IAM-03, SD-11 (partial) | SSO, password policy, encryption, network controls, and the rest |
| CC6.8 malicious software | 5 | SD-03 (partial) | endpoint protection, threat detection |
| PI1.3 processing | 2 | SD-02 (partial) | reconciliation |

A requirement is met only when every control that applies to it is ready (CF-4), so no
criterion can read "met" from GitHub alone. That is the intended behaviour, not a gap in the
connector: a source control system cannot show that laptops are encrypted.

Runs: daily from the worker (`run_connector_checks`, due after 20 hours), and on demand
from the control page or the Connections page. Evidence: one file per check, at most one a
day unless anything that check found changes (a reviewer, a setting, a population, not only a
pass or a fail), valid for 7 days (it reads aging only in its last two, because
evidence reads aging in the last third of its life, up to 30 days). Every result names the rules that judged it
(`rule`, currently `github.2026-10`), so a later rewording of a check never reinterprets an
old result.

### What a review proves

A review is a person's decision at a moment, so the moment and the commit are part of what it
proves. For each merged change only each reviewer's **last decision before the merge**
counts. An approval given after the merge reviewed nothing that was merged, an approval
withdrawn by a later "changes requested" no longer stands, a dismissed approval is gone,
comments are not approval, and the author cannot approve their own change. An approval of an
earlier commit than the one that merged still counts (GitHub does not require otherwise
unless the repository turns on "require approval of the most recent push"), but the evidence
lists those changes and the summary says so.

### What could not be read, and what was not read

- **Policy.** A branch can be protected by classic protection, by a ruleset, or both. When
  either source cannot be read, a repository that looks unprotected from the other may be
  protected by the one nobody could see, so the result is `error`, not `fail`. A setting
  that was read and found absent is still a `fail`. Protection that was read is never undone
  by a ruleset that was not.
- **Administrators.** Classic protection says whether administrators can bypass the rule;
  the result carries it and the summary says so. A ruleset's bypass list is not read yet.
- **Population.** More than 100 merged changes in a repository, more closed pull requests
  than 500 to page through, or the provider's request allowance running low part way through
  (the remaining changes are skipped, never failed) is stated: "None of the 100 merged changes read lacked an
  approving review. More were merged than could be read." An unreviewed change found is
  always a `fail`. More than 300 in-scope repositories is an `error` on every per
  repository check until the scope is narrowed, never a clean result over the part that
  was read.

### How a control is evidenced

The control page's **Checks** tab shows, for each control, every check that evidences it,
which software runs each one (and whether it is connected, ready to connect, or still
planned), what each collects, and the evidence people or Verity modules provide.
`composition.py` holds the rules and is covered by `tests/unit/test_composition.py`; the
design is in `openspec/changes/common-control-framework/design.md` section 4.5.

`GET /control-composition` feeds the controls register: for every control its mode, counts,
the control's `code` and `name`, and `runs_on`, the keys of the systems that have a collector
for any of its checks, connected or not (Verity's own modules appear as `verity`). That one
response drives the register's **Evidenced by** and **System** filters and the list of
controls on each connection card, with no request per system.

GitHub Enterprise Server: set `CONNECTORS_GITHUB_API_URL` to its API base.
