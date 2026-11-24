# 8. Owner decisions that gate the work

The decisions that must be taken before the first packages of
[04-phases-and-work-packages.md](04-phases-and-work-packages.md) start, in the order they are needed. Each
row names the numbers of the full list in [08-owner-decisions-raw.md](08-owner-decisions-raw.md) (127
decisions raised by the research), where the options and sources are. The rest are taken when their
package starts. Record each answer in the Answer column, with the date, and in `local-context/DECISIONS.md`.

## Before anything is built (P0)

| # | Decision | Recommendation | Raw | Answer |
|---|---|---|---|---|
| G1 | **Automation rule, refinement.** Rule B is decided (2026-11-23, `local-context/DECISIONS.md`): a passing check may satisfy its artifact once a person confirmed the population is complete. Refine it so that only a check that fills the artifact in full can satisfy it alone? | Yes: a full filling check satisfies under rule B; a partial one combines with a person's record or an approved document. By the end of Phase 2 only about 3% of artifact rows have a full filling check, so this keeps partial automation from reading as proof. | engine (01 section 1.2) | |
| G2 | **Coverage downgrades.** Move all 16 full check to control links and the 8 full requirement links to partial, each with a rationale. | Approve: no connector check proves a whole control. | 44, 50 | |
| G3 | **Control breakdown.** Send the 11 splits and 4 additions (148 controls in all) and the objective revisions to qualified review (an ISO 27001 lead auditor, a CPA with SOC 2 experience), and model "full when the sibling control is not applicable" before any split ships. | Approve for review; nothing ships before the reviewer signs. | 52, 79 to 107 | |
| G4 | **Scope extension.** Ask the client to add device management, endpoint protection and HR (not in the signed catalogue). | Ask, in the order Intune with Defender, Google devices, Jamf, Kandji, CrowdStrike, SentinelOne; HR from a roster CSV, then BambooHR, HiBob, Rippling. | 4, 5, 14 | |

## Before the foundations (P1)

| # | Decision | Recommendation | Raw | Answer |
|---|---|---|---|---|
| G5 | **Staff roster source.** Verity members are not the staff list; every leaver, joiner and acknowledgement check reads "insufficient information" until a roster exists. | A CSV roster import as the interim HR source, minimal fields, leavers kept 13 months. | 108, 110 | |
| G6 | **Incident register.** Until the Incidents module (signed Phase 3.1), record incidents as an incident kind on Tasks; sync Jira and PagerDuty incidents into it awaiting a person's triage. | Approve both. | 119, 120 | |
| G7 | **Devices without an MDM.** Build the reviewed device attestation flow; add a device type to Assets; do not build an endpoint agent now. | Approve; re-decide the agent (Go and osquery) when customers without an MDM or Google Workspace are a meaningful share. | 111, 112, 116 | |
| G8 | **Vulnerability module before scanners.** Fix asset matching, unmatched findings, first found time, severity maps and scanner closure before any scanner ships. | Approve. | 117 | |
| G9 | **Integrations as content.** Generate the catalogue and the connect dialog from provider content; setup guides as reviewed content. | Approve. | 126 | |
| G10 | **The GitHub gap already built.** Direct pushes are not seen. Fix with rule suites (Administration read) and say on the result that pushes outside rulesets are not seen; do not ask for Contents read. Build the GitHub App under a hardened Verity organisation. | Approve both; the organisation hardening comes first (the November incident). | 21, 22 | |

## Before the first connectors (P2)

| # | Decision | Recommendation | Raw | Answer |
|---|---|---|---|---|
| G11 | **Two credential rule.** Every identity provider uses two credentials (sign in held by Keycloak, evidence held by Verity) behind one setup and one card. | Approve. | 37 | |
| G12 | **First identity provider.** | The pilot customer's provider. | 9 | |
| G13 | **Entra evidence app.** Customer owned evidence app created in the wizard first (Verity generates the certificate), Verity's multi tenant app after the first pilot, only with a key that cannot be exported; Azure follows the same choice. | Approve; join the Microsoft partner program for publisher verification either way. | 18, 27, 28 | |
| G14 | **Okta admin role.** | Test a custom admin role with read scopes on a developer org; never ask for Super Administrator by default. | 29, 30, 31 | |
| G15 | **Google Workspace.** Domain wide delegation to Verity's service account, signing without a stored key; ask for a super admin as the delegated subject, or accept three checks that say "needs a super admin". | Delegation, keyless signing; the subject choice is yours. | 32, 33, 34 | |
| G16 | **Verity's own cloud identities.** How Verity (hosted on Contabo) signs in to AWS, Google Cloud and Azure on customers' behalf: a stored key rotated every 90 days now, or one OIDC token issuer Verity hosts and reuses for all three. | A key in the runtime secret store now for AWS, the token issuer as an ADR before Google Cloud and Azure. | 15, 20, 33 | |
| G17 | **AWS role policy.** | Verity's custom least privilege policy (SecurityAudit also exposes Lambda and ECS environment values, EC2 user data and CodeBuild variables). | 16, 17 | |
| G18 | **Jira auth.** | A scoped service account token first; Atlassian's OAuth apps share one hourly quota across all customers since 2 March 2026. | 39 | |
| G19 | **Write capable credentials.** Bitbucket branch rules, the Sentry audit log, 1Password SCIM tokens and several Phase 3 providers have no read only credential. | Do not read them in Phase 2; one ADR before Phase 3 decides each with mitigations. | 25, 35, 41, 42 | |
| G20 | **Default thresholds.** The drafted defaults (screen lock 15 minutes, device stale after 14 days, high urgency page acknowledged in 30 minutes, signal triage 24 hours, post incident review in 14 days, scan interval quarterly) are proposals each workspace's procedure overrides. | Accept as proposals; settle the scan interval (30 or 92 days) as one setting. | 54, 58, 63 | |

## Also asked

- The market research read "Intrata" as Drata and "like dot" as Laika (now Thoropass). If you meant
  other products (for example Scytale or Delve), name them and the research is extended (raw 127).
