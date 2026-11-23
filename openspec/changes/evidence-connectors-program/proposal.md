# Proposal: evidence connectors program

## Why

Verity proves 133 controls (plus the proposed successors) through 591 assessment objectives and 338
artifact types. Today 268 of those artifacts can only be filled by a person, and only GitHub and
Verity's own built in checks collect anything automatically. The signed delivery plan promises fifteen
Phase 2 connectors and a longer Phase 3 list. The owner wants each provider connected once by the
customer, serving both sign in (through Keycloak) and evidence, with every piece of evidence traceable
from the system to the objective, the control and the SOC 2 and ISO 27001 requirements. Collectors may be
written in Go.

## What

The research and plan in `docs/product/evidence-connectors/`:

- `01-evidence-model.md`: how connector checks, Verity module checks and people fill artifacts and
  objectives; observation types; the Go collector architecture.
- `02-integration-model.md`: one integration per provider, credential patterns, connect screens, setup
  guides as content, two credentials behind one setup for identity providers.
- `03-market-research.md`: how Vanta, Drata, Secureframe, Sprinto, Thoropass, Scrut, Hyperproof and
  ServiceNow do it.
- `04-phases-and-work-packages.md`: the build order and the definition of done.
- `05-check-registry.md` and `checks-proposed.json`: every existing and proposed check, deduplicated.
- `06-control-changes.md`: proposed splits, new controls, objective revisions and content defects.
- `07-control-matrix.md`: control by control, where each artifact's evidence comes from, by phase.
- `08-owner-decisions.md`: what the owner must decide before each package starts.
- `connectors/`: one document per provider; `coverage/`: artifact by artifact mappings;
  `verification/`: the fact checking logs.

## Not in this change

Any code or content change. Each work package in `tasks.md` is its own change when built. Control splits
and mapping changes are proposals for qualified review (an ISO 27001 lead auditor and a CPA with SOC 2
experience), never applied by this plan. Device management, endpoint protection and HR connectors are
outside the signed catalogue and need the client's agreement.
