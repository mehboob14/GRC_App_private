# Evidence connectors: research and plan

How every Verity control gets its evidence, from connected systems, from Verity's own modules and from
people; how each connector is connected, collected, checked and shown; and the order to build it. A plan,
researched and fact checked on 2026-11-23. Nothing in it is built yet. OpenSpec change:
`openspec/changes/evidence-connectors-program/`.

## Start here

| Read | For |
|---|---|
| [AUTHORING.md](AUTHORING.md) | The rules for anyone adding to this plan (accuracy, least privilege, own words, check naming, file formats) |
| [01-evidence-model.md](01-evidence-model.md) | Control, objectives, artifacts and the three source kinds; observation types; the Go collector architecture |
| [02-integration-model.md](02-integration-model.md) | One integration per provider; two credentials behind one setup for identity providers; credential patterns; connect screens; setup guides as content |
| [03-market-research.md](03-market-research.md) | How Vanta, Drata, Secureframe, Sprinto, Thoropass, Scrut, Hyperproof and ServiceNow do it, and where Verity can be better |
| [04-phases-and-work-packages.md](04-phases-and-work-packages.md) | **The build plan**: phases, packages, definition of done |
| [05-check-registry.md](05-check-registry.md), [checks-proposed.json](checks-proposed.json) | Every existing and proposed check, per capability, with providers and controls |
| [06-control-changes.md](06-control-changes.md) | Proposed control splits and additions, objective revisions, mapping changes, content defects |
| [07-control-matrix.md](07-control-matrix.md), [.csv](07-control-matrix.csv) | Control by control: where each artifact's evidence comes from, by phase |
| [08-owner-decisions.md](08-owner-decisions.md) | The 20 decisions that gate the first packages ([raw list of 127](08-owner-decisions-raw.md)) |
| [mdm-and-endpoint-strategy.md](mdm-and-endpoint-strategy.md) | Devices, endpoint protection and HR: what they serve, and customers without an MDM |
| [connectors/](connectors/) | One document per provider: permissions, setup guide draft, collection, checks, controls, Go notes |
| [coverage/](coverage/) | Artifact by artifact source mappings and control decisions, per family |
| [verification/](verification/) | Fact checking logs: 768 claims checked against official documentation |
| [tools/](tools/) | The generators: `merge.py` (registry and needs), `gen_docs.py` (05 to 08), `validate.py` |

## What the research found

- **The model already in the platform is right** (the architecture diagram): control, objectives,
  artifacts, sources, outcome. Connectors plug in as checks that fill artifacts; Verity's modules plug in
  the same way through `verity.*` checks; people stay a source for every artifact.
- **The library grows from 133 to 148 controls** if the review accepts it: 11 splits where SOC 2 and ISO
  27001 need separate ownership, cadence or applicability (for example ISO management review and the
  top management policy statement apart from their SOC 2 counterparts, scan coverage apart from
  remediation, server patching apart from laptop patching), and 4 additions (product sign in
  protections, processing error handling, output delivery, direct changes to production data).
- **127 new checks** after removing duplicates (138 proposed), and 80 existing checks gain providers.
- **Automation is mostly partial, and that is honest.** By the end of Phase 2, 93% of artifact rows have
  at least one automated source (a connector or a Verity module check), but only 3% have one that fills
  the artifact in full. Connectors find deviations, collect populations and save work; most objectives
  still need a reviewed record or an approved document. No competitor publishes coverage per mapping;
  Verity can.
- **Sign in and evidence in one setup**, with two credentials underneath, is ahead of every competitor
  reviewed (all keep them apart; Drata comes closest for Okta). Keycloak, run by Infowise, never holds a
  credential that can read a customer's directory.
- **Fix before building:** a shipped device artifact lets an enrolment check satisfy encryption and wipe
  objectives; all 16 full check to control links overstate; the GitHub connector cannot see direct
  pushes; the vulnerability module would make a connected scanner look cleaner than the estate.
- **Scope:** device management, endpoint protection and HR are not in the signed catalogue; the plan asks
  the client for an extension and offers a reviewed device attestation flow and a roster import meanwhile.

## Keeping it current

Every session that builds or changes anything here follows [AUTHORING.md](AUTHORING.md), reruns
`tools/merge.py`, `tools/gen_docs.py` and `tools/validate.py` after editing coverage or checks, ticks the
package in the OpenSpec tasks, updates `local-context/STATE.md` and `CHANGELOG.md`, and pushes the GitHub
branch `handoff/verity-dev`.
