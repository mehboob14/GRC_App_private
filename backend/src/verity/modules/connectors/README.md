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

What Verity reads, per active (non archived) repository: the default branch, classic
branch protection, rulesets that apply to the default branch, the Dependabot alerts
setting, the secret scanning setting, and pull requests merged into the default branch in
the last 30 days with their reviews (up to 20 per repository per run). Nothing is
written to GitHub.

| Check | Passes when |
|---|---|
| `vcs.default_branch_protected` | The default branch is protected (or a ruleset requires pull requests) and force pushes are blocked |
| `vcs.review_required` | At least one approving review is required to merge |
| `vcs.status_checks_required` | Required status checks must pass before merge |
| `vcs.merged_changes_reviewed` | Every change merged in the last 30 days was approved by someone other than its author |
| `vcs.secret_scanning_enabled` | Secret scanning is on |
| `vcs.dependency_alerts_enabled` | Dependabot alerts are on |
| `vcs.org_two_factor_required` | The organisation requires two factor (not applicable to a personal account) |

Runs: daily from the worker (`run_connector_checks`, due after 20 hours), and on demand
from the control page or the Connections page. Evidence: one JSON snapshot per day per
connection, or sooner when results change, valid for 7 days.

GitHub Enterprise Server: set `CONNECTORS_GITHUB_API_URL` to its API base.
