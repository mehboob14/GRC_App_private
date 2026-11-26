# Tasks: MDM and device evidence

One box per work package of `docs/product/evidence-connectors/mdm/06-build-plan.md`. Tick a box only when that
package's "done when" holds, with a line naming the commit and what was verified.

## Gates

- [ ] G0 D-DEV-1: device evidence agreed with the client as an extension
- [ ] G1 Connection platform (F4) and Go runtime (F5) available (`openspec/changes/connector-runtime/`)

## Decisions and content

- [ ] MDM-0 Owner decisions D-MDM-1 to D-MDM-20 answered; D2 review of CC1 to CC7 and the 28 check mappings
- [ ] MDM-1 Content: artifact split and three new artifacts, EP-03.F, mobile lock parameter, 28 checks, capability
      providers; resealed; comparison report accepted
- [ ] MDM-2 Contracts: six device observation schemas, generated Go and Python, CI staleness check

## Core and runtime

- [ ] MDM-3 Device record, populations, daily history, manual links and exclusions; Assets device type (if
      D-MDM-5 yes)
- [ ] MDM-4 Check evaluators for 28 checks per platform; evidence files with query, filters and counts;
      exception waiver (if D-MDM-6 yes)
- [ ] MDM-5 Go device package: normaliser, privacy drop, endpoint and field allowlists, secrets self check

## Providers

- [ ] MDM-6 Intune (with Autopilot, Entra devices, MAM, Data Warehouse backfill)
- [ ] MDM-7 Google devices (endpoint management, Endpoint Verification, ChromeOS, Chrome policy, Knox)
- [ ] MDM-8 Jamf Pro (version ladder, DDM status, profiles, command history)
- [ ] MDM-9 Iru (Kandji)
- [ ] MDM-10 JumpCloud
- [ ] MDM-11 Apple Business (purchase source)
- [ ] MDM-12 Wave 2, one line per provider when demanded: Workspace ONE, ManageEngine, Rippling devices, Addigy,
      SimpleMDM, Fleet, NinjaOne, Device Trust

## Product

- [ ] MDM-13 Devices register, device detail, matching review, exceptions, leaver and lost device tasks,
      disposal links, auditor exports, before you connect pages, setup guides, privacy pack
- [ ] MDM-14 Device attestation flow for customers without an MDM
