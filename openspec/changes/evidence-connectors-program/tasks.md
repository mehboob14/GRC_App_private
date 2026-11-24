# Tasks: evidence connectors program

One box per work package of `docs/product/evidence-connectors/04-phases-and-work-packages.md`. Tick a box
only when that document's definition of done holds (section 4.6 for connectors, 4.7 for control families),
with a line naming the commit and what was verified.

## P0 Decisions and review

- [ ] D1 Owner decisions answered (`08-owner-decisions.md`)
- [ ] D2 Qualified review of the control changes and mapping changes (`06-control-changes.md`)
- [x] D3a Automation rule: rule B chosen by the owner on 2026-11-23 (local-context/DECISIONS.md)
- [ ] D3b Rule B refinement: only a check that fills an artifact in full satisfies it alone (G1)

## P1 Foundations

- [ ] F1 Content truth: defects, downgrades, template gaps
- [ ] F2a Control breakdown: GOV, CS, HR
- [ ] F2b Control breakdown: IAM, EP, PE, NS, DM
- [ ] F2c Control breakdown: SD, LM, BC
- [ ] F3 Verity module evidence: proposed verity.* checks and module gaps (incident marker, scan targets,
      triage time, device asset type, subprocessor list, roster import, Verity identity, device attestation)
- [ ] F4 Integration platform: provider content, generated catalogue and connect dialog, probe, health,
      guides, integration card joining sign in and evidence
- [ ] F5 Go collector runtime, observation contracts, ingestion API
- [ ] F6 GitHub fixes: direct push gap, GitHub App decision, CI checks
- [ ] F7 Vulnerability module fixes before scanners
- [ ] F8 Vendor side identities and key service

## P2 Signed connectors

- [ ] C1 Entra ID and Microsoft 365
- [ ] C2 Google Workspace
- [ ] C3 Okta
- [ ] C4 1Password
- [ ] C5 AWS
- [ ] C6 GitHub expansion
- [ ] C7 GitLab
- [ ] C8 Bitbucket
- [ ] C9 Jira
- [ ] C10 PagerDuty
- [ ] C11 Datadog
- [ ] C12 Sentry
- [ ] C13 Cloudflare
- [ ] C14 Tailscale and Slack

## P2X Extension (client agreement first)

- [ ] X1 Intune and Defender for Endpoint
- [ ] X2 Google devices and Endpoint Verification
- [ ] X3 Jamf Pro
- [ ] X4 Kandji
- [ ] X5 CrowdStrike Falcon
- [ ] X6 SentinelOne
- [ ] X7 HR systems
- [ ] X8 Learning platform, e-signature, background screening

## P3 Later

- [ ] L1 Azure and GCP
- [ ] L2 Vulnerability scanners
- [ ] L3 Business applications and AI providers
- [ ] L4 Remaining Phase 3 catalogue
- [ ] L5 Verity multi tenant Entra evidence app
- [ ] L6 Endpoint agent re-decision
