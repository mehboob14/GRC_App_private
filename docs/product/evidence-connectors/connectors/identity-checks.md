# Identity checks: shared definitions and feasibility

Shared by [entra-id.md](entra-id.md), [okta.md](okta.md), [google-workspace.md](google-workspace.md) and
[1password.md](1password.md). Checks are written per capability, so a check key means the same thing on
every provider. This file holds what does not change between providers: the full definitions of the new
checks, the feasibility matrix, the artifacts the checks fill, the framework reach and the content
corrections found while researching. Each connector document holds the provider specific API, population
and predicate. Setup across sign in and evidence: [identity-providers-unified-setup.md](identity-providers-unified-setup.md).

Researched 2026-11-23. Nothing here edits content JSON (AUTHORING rule 8): the definitions below are
proposals for the reconciliation step.

## 1. Feasibility matrix

S supported, P partial, N not possible, n/a the check is not about this provider. "Partial" says why in
the connector document.

| Check | Entra ID | Okta | Google Workspace | 1Password |
|---|---|---|---|---|
| `idp.mfa_enforced` | S (P1 or P2 for Conditional Access and the registration report; on Free, security defaults cover the policy half but the per user half reads error with reason licence, so the check is insufficient; corrected 2026-11-23) | S | S | n/a (member 2FA is not exposed, see 1password.md) |
| `idp.sso_enforced` | P | P | P | P (unlock with SSO events only) |
| `idp.password_policy` | P (length is fixed by Microsoft) | S | P (super admin only, no lockout settings) | N |
| `idp.session_timeout` | P (no tenant wide idle timeout) | S (Identity Engine: the global session policy may need more than Read-only Administrator, test) | P (maximum only, no idle) | n/a |
| `idp.admins_limited` | S | S (Okta lists viewing administrators for Super Administrator only; test Read-only or a custom role) | S | n/a |
| `idp.access_list_exported` | S | S | S | P (members only, no vault access) |
| `idp.groups_drive_access` | S (group assignment needs P1) | S | N | n/a |
| `idp.connected_apps_known` | S | P | P (audit events, 180 days) | n/a |
| `people.leavers_deprovisioned` | P (needs a leaver roster) | P (needs a leaver roster) | P (needs a leaver roster) | see `vault.leavers_removed` |
| `people.joiners_onboarded` | P (needs onboarding records) | P | P | n/a |
| `vault.everyone_enrolled` | n/a | n/a | n/a | S (needs a staff roster) |
| `tickets.access_requests_approved` (identity side) | P (grant events, 30 days) | P (grant events, 90 days) | P (grant events, 180 days) | n/a |
| NEW `idp.admin_mfa_phishing_resistant` | S | P | P | n/a |
| NEW `idp.no_inactive_accounts` | S (P1) | S | S | N (no last sign in field) |
| NEW `idp.machine_identities_owned` | S | P | N | n/a |
| NEW `idp.access_reviews_completed` | S (Entra ID Governance or P2) | S (Okta Identity Governance, and the Access Certifications Administrator role on the app) | N | n/a |
| NEW `people.accounts_match_roster` | S (needs a roster) | S (needs a roster) | S (needs a roster) | n/a |
| NEW `vault.leavers_removed` | n/a | n/a | n/a | S (needs a leaver roster) |

The roster dependency is the largest gap. `hr_system` providers are `not_planned` in `capabilities.json`,
and the continuous compliance plan (section 6 C) proposes a controlled workforce import. Until a roster
exists in Verity, every check that needs one reads **insufficient information**, never pass (rule 3).

## 2. New checks: full definitions

Shape follows `checks.json`. `implementations` stays empty until a collector ships. Each entry also states
population, predicate, period and the empty case (rule 4).

### 2.1 `idp.admin_mfa_phishing_resistant`

| Field | Value |
|---|---|
| name | Administrators use phishing resistant sign in |
| description | Every account that holds an administrator role must sign in with a phishing resistant factor, such as a security key or a passkey. |
| capabilities | `identity_provider` |
| resource_type | `user` |
| frequency | daily |
| remediation | Require a phishing resistant factor for administrator roles, and enrol a security key or passkey for each listed administrator. |
| controls | IAM-03 partial: "Shows identity provider administrators must use a phishing resistant factor. Cloud root accounts and other systems are checked separately." IAM-07 partial: "Shows privileged identity provider accounts carry stronger sign in protection. Approval and review of those accounts stay with people." |
| evidence_kinds | Administrator sign in requirement; Administrator factor enrolment |
| population | Enabled accounts holding any administrator role (active or eligible) at collection time |
| predicate | A policy that applies to the account requires a phishing resistant factor, and the account has one enrolled |
| period | Point in time, daily |
| empty population | `error`: an identity provider always has at least one administrator, so an empty list means the role read failed |

### 2.2 `idp.no_inactive_accounts`

| Field | Value |
|---|---|
| name | No unused account stays active |
| description | No enabled account, member or guest, has gone longer than the allowed period without a successful sign in. |
| capabilities | `identity_provider` |
| resource_type | `user` |
| frequency | daily |
| parameter | `inactive_days`, default 90, set from the customer's access policy; accounts created less recently than this are left out |
| remediation | Disable the listed accounts, or record why each one must stay active. |
| controls | IAM-12 partial: "Finds accounts nobody uses, which is how missed removals surface. Matching accounts to leavers needs the staff list." IAM-02 partial: "Points reviewers at unused access between reviews. The review and its sign off stay with people." HR-03 partial: "Finds guest and contractor accounts that outlived their use. The contractor register and end dates stay with people." |
| evidence_kinds | Account list with last successful sign in |
| population | Enabled accounts older than `inactive_days`, members and guests, excluding accounts recorded as exceptions in Verity |
| predicate | Last successful sign in is within `inactive_days`. An account that never signed in counts as inactive |
| period | Rolling window of `inactive_days` ending at collection |
| empty population | `pass` only when the provider returned a complete user list; otherwise `insufficient information` |

### 2.3 `idp.machine_identities_owned`

| Field | Value |
|---|---|
| name | App credentials have owners and expire |
| description | Every application or service app that holds a credential in the identity provider has a named owner, and no credential lives longer than the rotation limit. |
| capabilities | `identity_provider` |
| resource_type | `application` |
| frequency | daily |
| parameter | `max_credential_days`, default 365, from the customer's access policy |
| remediation | Add an owner to the listed applications, and replace credentials that outlive the rotation limit. |
| controls | IAM-10 partial: "Covers machine identities held in the identity provider. Cloud and build system credentials are checked by `cloud.machine_credentials_rotated`." |
| evidence_kinds | Application credential inventory; Application owners |
| population | Applications registered in the customer's own directory that hold at least one secret or certificate |
| predicate | At least one owner, and every credential's lifetime (end minus start, or age where no end exists) is at most `max_credential_days` |
| period | Point in time, daily |
| empty population | `pass` with a note when the list was complete (many small tenants have none) |

### 2.4 `idp.access_reviews_completed`

| Field | Value |
|---|---|
| name | Identity provider access reviews are finished |
| description | Every access review that closed in the period has a decision on every item by someone other than the person reviewed, and every removal decided was applied. |
| capabilities | `identity_provider` |
| resource_type | `access_review` |
| frequency | daily |
| remediation | Finish open reviews, reassign self reviews, and apply the removals that were decided. |
| controls | IAM-02 partial: "Shows reviews run inside the identity provider were completed and acted on. Systems outside it and the review procedure stay with people." IAM-07 partial: "Where privileged roles are reviewed in the identity provider, shows those reviews were completed." |
| evidence_kinds | Access review instances and decisions |
| population | Review instances that ended in the last 90 days |
| predicate | No item without a decision; no item decided by the person it is about; every deny decision applied |
| period | 90 days ending at collection |
| empty population | `not_applicable` when the customer runs reviews outside the identity provider (the manual review pack stays the evidence), never `pass` |

### 2.5 `people.accounts_match_roster`

| Field | Value |
|---|---|
| name | Every account belongs to a current person |
| description | Every enabled member account in the identity provider matches a person on the current staff and contractor roster, or is a recorded shared or service account with an owner. |
| capabilities | `hr_system`, `identity_provider` |
| resource_type | `user` |
| frequency | daily |
| remediation | Disable the listed accounts, link each to a person, or record it as a service account with an owner. |
| controls | IAM-12 partial: "Reconciles accounts with the people who should have them. Systems outside the identity provider need their own reconciliation." IAM-01 partial: "Shows each account maps to one named person. Approval of the access is checked separately." HR-03 partial: "Shows contractor accounts match the contractor roster. Agreements and training stay with people." |
| evidence_kinds | Account list; Staff and contractor roster; Match results |
| population | Enabled member accounts (guests are covered by `idp.no_inactive_accounts`) |
| predicate | Matched to an active roster person by immutable id, or by email when the roster has no id, or recorded in Verity as a shared or service account with an owner |
| period | Point in time, daily |
| empty population | `insufficient information` when no roster exists or it is older than its own review period |

### 2.6 `vault.leavers_removed`

| Field | Value |
|---|---|
| name | Leavers lose password manager access |
| description | No one who left still has an active company password manager account after the allowed time. |
| capabilities | `hr_system`, `password_manager` |
| resource_type | `person` |
| frequency | daily |
| parameter | `removal_hours`, default 24, the same value `people.leavers_deprovisioned` uses |
| remediation | Suspend the listed password manager accounts, and rotate the shared credentials they could read. |
| controls | IAM-05 partial: "Shows leavers lost vault access. Rotating the shared credentials they could read is recorded by people." IAM-12 partial: "Covers the password manager, one of the systems outside single sign on that removal must reach." |
| evidence_kinds | Password manager member status; Leavers from the HR source |
| population | Leavers on the roster whose end date is in the last 90 days |
| predicate | No active vault account for the leaver later than `removal_hours` after the end date |
| period | 90 days ending at collection |
| empty population | `pass` only when the roster is current and shows no leavers; otherwise `insufficient information` |

## 3. Artifacts and objectives the identity checks fill

Today versus planned (artifact keys from `artifacts.json`). Proposed source changes only; the content edit
is for the reconciliation step.

| Artifact key | Objectives | Control | Today | Planned |
|---|---|---|---|---|
| `second-factor-enforcement-and-enrolled-users` | IAM-03.B, C, D, E | IAM-03 | person | person + `idp.mfa_enforced` (B, D, E) + `idp.admin_mfa_phishing_resistant` (C) |
| `list-of-privileged-accounts-with-approval` | IAM-07.B, IAM-01.D, IAM-03.C, IAM-10.C | IAM-07 | check (`idp.admins_limited`, `cloud.least_privilege`, no collector) + person | unchanged sources; `idp.admins_limited` gains three collectors. Approval stays a person |
| `account-list-export` | IAM-02.B, IAM-12.E, IAM-10.B, HR-03.B | IAM-02 | check `idp.access_list_exported` + person | + `people.accounts_match_roster` (IAM-12.E, HR-03.B) + `idp.no_inactive_accounts` (IAM-12.E) |
| `group-and-role-membership-export` | IAM-08.B, C, IAM-09.B | IAM-08 | person | person + `idp.access_list_exported` + `idp.groups_drive_access` |
| `applications-inside-and-outside-single-sign-on` | IAM-04.B, C, D | IAM-04 | person | person + `idp.sso_enforced` (B). Exceptions (C) stay a person |
| `identity-provider-password-settings` | IAM-06.B, C, D | IAM-06 | person | person + `idp.password_policy` (B, C). D stays a person |
| `session-limit-settings-export` | IAM-11.B, C, D | IAM-11 | person | person + `idp.session_timeout` (B). C and D stay a person |
| `review-of-newly-discovered-applications` | BC-05.B, C, D | BC-05 | person | person + `idp.connected_apps_known` (B) |
| `removal-records-for-a-sample-of` | IAM-12.B, C, D, IAM-04.D, IAM-11.D, HR-03.D | IAM-12 | check `people.leavers_deprovisioned` + person | + `vault.leavers_removed` (IAM-12.D) |
| `roster-of-joiners-and-leavers-with` | HR-05.C, D, HR-06.B, IAM-05.B, IAM-12.B, E | HR-05 | check `people.leavers_deprovisioned` + person | unchanged: an identity provider cannot produce the roster, it is compared against it |
| `completed-checklists-for-a-sample-of` | HR-06.B to E, IAM-01.B | HR-06 | person | person + `people.joiners_onboarded` (HR-06.B) |
| `password-manager-members-against-staff-list` | IAM-05.B, C, D | IAM-05 | person | person + `vault.everyone_enrolled` (B) + `vault.leavers_removed` (B, D). C stays a person |
| `inventory-of-service-accounts-and-keys` | IAM-10.B, C, D | IAM-10 | check `cloud.machine_credentials_rotated` + person | + `idp.machine_identities_owned` |
| `records-of-rotation-or-review` | IAM-10.D, E | IAM-10 | check `cloud.machine_credentials_rotated` + person | + `idp.machine_identities_owned` (D) |
| `completed-access-reviews-with-reviewer-sign` | IAM-02.C, D, IAM-07.C, D, IAM-01.E, HR-03.E | IAM-02 | person | person + `idp.access_reviews_completed` (only where the customer reviews inside Entra or Okta) |
| `access-changes-made-as-a-result` | IAM-02.E, IAM-07.E | IAM-02 | person | person + `idp.access_reviews_completed` |
| `privileged-elevation-and-break-glass-log` | IAM-07.B | IAM-07 | person | person + `idp.admins_limited` evidence (Entra with PIM only: eligible versus active, activation events) |
| `approved-requests-for-a-sample-of` | IAM-01.B to E, HR-06.B, D, IAM-08.C, HR-03.C | IAM-01 | check `tickets.access_requests_approved` + person | unchanged; the identity provider supplies the grant population from its audit log |
| `evidence-logs-are-reviewed` | LM-02.B, D | LM-02 | person | unchanged. NEED observability: identity provider sign in and admin events reach the central log store |
| `contractor-register-with-start-and-end` | HR-03.B to E | HR-03 | person | unchanged; it is an input to `people.accounts_match_roster` |

What no identity connector proves: the approved policies and procedures (every `.A` objective), approvals
and sign offs, the judgement that an admin needs their role, rotation of shared secrets after a leaver, and
any system that does not sign in through the identity provider.

## 4. Framework reach

Through IAM-01 to IAM-12, HR-03, HR-05, HR-06 and BC-05 (mappings from
`seed/content/{soc2,iso27001}/template_requirements.json`). Every link is partial on its own.

| Framework | References reached |
|---|---|
| SOC 2 | CC6.1 (IAM-03, 04, 05, 06, 08, 10, 11), CC6.2 (IAM-01, 02, 12, HR-03, 05, 06), CC6.3 (IAM-01, 02, 07, 08, 09, 10, 12, HR-05), CC5.1 (IAM-09), CC5.2 (IAM-08), CC9.2 (BC-05, HR-03), CC1.4 (HR-06) |
| ISO 27001:2022 | A.5.3 (IAM-09), A.5.4 (HR-06), A.5.11 (HR-03, 05), A.5.15 (IAM-01, 08), A.5.16 (IAM-01, 10, 12), A.5.17 (IAM-05, 06), A.5.18 (IAM-01, 02, 12), A.5.23 (BC-05), A.6.5 (HR-05), A.8.2 (IAM-07), A.8.3 (IAM-08, 10), A.8.4 (IAM-02, 08), A.8.5 (IAM-03, 04, 06, 11), A.8.18 (IAM-07), A.8.30 (HR-03), A.8.34 (IAM-01) |

LM-02 (CC7.2, A.8.15) is not reached: identity providers keep sign in logs for 7 to 180 days, and the
central store with 12 months retention is an observability source.

## 5. Content corrections found (for the reconciliation step)

Rule 5 asks for honest coverage. These existing entries claim more than any identity provider can show:

| Entry | Today | Proposed | Why |
|---|---|---|---|
| `idp.sso_enforced` to IAM-04 | full | partial | An identity provider sees only apps connected to it. IAM-04.B needs the vendor register compared, and IAM-04.C needs approved exceptions |
| `idp.password_policy` to IAM-06 | full | partial | Settings cannot show passwords were changed after an exposure (IAM-06.D). On Entra the length rule is fixed by Microsoft |
| `idp.session_timeout` to IAM-11 | full | partial | Settings do not show re-authentication for high risk actions (IAM-11.C) or that sign out ends refresh tokens (IAM-11.D) |
| `people.leavers_deprovisioned` to IAM-12 | full | partial | Disabling the identity provider account does not prove access to systems outside single sign on was removed (IAM-12.D) |
| `vault.everyone_enrolled` capabilities | `password_manager` | `password_manager`, `hr_system` | "Every active employee" needs a staff list; the vault alone cannot say who is missing |
| `vault.everyone_enrolled` to IAM-05 | full | partial | Membership does not show shared credentials are kept in team vaults (IAM-05.C) |
| `idp.mfa_enforced` predicate | one sign in policy for every user | name the exclusions | Every real tenant excludes break glass accounts. The check should list exclusions and pass only when each has an approved exception (IAM-03.D) |
| Artifacts in section 3 marked person only | person | person + check | The checks already exist but the artifacts do not list them, so the engine would never count them |
