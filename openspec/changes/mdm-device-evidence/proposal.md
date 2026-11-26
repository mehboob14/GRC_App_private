# Proposal: MDM and device evidence

## Why

Seven endpoint controls (EP-01 to EP-08) and parts of DM-19, HR-03, HR-05 and LM-01 are today satisfied only
by people. Device management systems hold most of that evidence, but what they can prove depends on the
platform and enrolment channel, several "read only" credentials can reach secrets, and an MDM cannot see a
device that never enrolled. Round 2 research (`docs/product/evidence-connectors/mdm/`) settles these questions
for 16 device sources and turns them into checks, content changes, processes and work packages.

## What

- **Content:** split the device inventory artifact, add three artifacts and objective EP-03.F (personal
  devices), a mobile screen lock limit, 28 device and endpoint checks with partial mappings to EP-01 to EP-08,
  DM-19, HR-03, HR-05 and LM-01, and the providers in `capabilities.json`.
- **Contracts:** device observation types v2 (`device`, `device.policy`, `device.purchase`, `device.action`,
  `device.app_protection`, `device.directory`), with privacy rules enforced in the Go normaliser.
- **Core:** one merged device record per device, company device and staff populations, daily device history,
  per resource exception waiver (decision), Assets device type (decision).
- **Providers, wave 1:** Intune (with Autopilot, Entra devices, MAM), Google devices, Jamf Pro, Iru, JumpCloud,
  and Apple Business as the purchase source. Wave 2 on demand.
- **Product:** devices register, matching review, leaver and lost device tasks, disposal links, auditor
  exports, setup guides, privacy pack, attestation for customers without an MDM.

Plan: `docs/product/evidence-connectors/mdm/06-build-plan.md`. Decisions: `mdm/07-decisions.md`.

## Not in this change

A Verity endpoint agent (D-MDM-20 keeps round 1's "not now"). Sending any device command. Endpoint protection
connectors beyond what round 1 planned. Hexnode and Mosyle until they offer a scoped token.

## Gates

D-DEV-1 (scope extension with the client) before any provider package; the connection platform and Go runtime
(`openspec/changes/connector-runtime/`); D2 review before content ships.
