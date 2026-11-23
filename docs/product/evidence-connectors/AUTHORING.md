# Authoring rules for the evidence connectors plan

Read this before writing anything in `docs/product/evidence-connectors/`. It is the brief for every
person or agent who researches a connector or maps controls to evidence, now or later.

## 1. What this plan is

Verity proves controls with evidence. The model (diagram: `docs/Compliance Control Architecture
Flowchart.png`; design: `docs/product/guided-onboarding/05-control-library-and-objectives.md`):

```
framework requirement (SOC 2 CC6.1, ISO 27001:2022 A.5.15)
  -> common control (IAM-02)                     seed/content/{soc2,iso27001}/control_templates.json
       mapping with coverage full|partial         seed/content/{soc2,iso27001}/template_requirements.json
  -> assessment objectives (IAM-02.A .. E)        seed/content/objectives/objectives.json
       assurance design|operating, methods examine|interview|observe|test, each method names artifacts
  -> artifact types (account list export, ...)    seed/content/objectives/artifacts.json
       each artifact lists sources:
         {"kind": "check", "checks": [...]}       automated: a connector check or a Verity module check
         {"kind": "document", "template": "..."}  the Documents module (a policy or procedure)
         {"kind": "person"}                       uploads, interviews, attestations, observations
  -> observations -> test -> objective outcome -> control readiness -> framework status
```

Checks are content (`seed/content/automation/checks.json`). A check is written against a
**capability** (`identity_provider`, `device_management`, ...; `capabilities.json`) and lists the
**providers that implement it** (`implementations`). One connected provider per capability is enough.
Each check maps to controls with `coverage` (full or partial) and a `rationale`. Verity's own modules
are the provider `verity` (checks `verity.*`). Today only GitHub (7 checks) and Verity (30 checks) run.
93 checks exist; 133 controls; 591 objectives; 338 artifact types, of which 268 can only be filled by a
person today. This plan says, for every connector and every control, how that changes.

Existing references to read, not repeat:
`docs/architecture/check-catalogue.md` (generated), `docs/architecture/integrations.md`,
`docs/product/control-framework-requirements.md`, `docs/product/continuous-compliance-plan.md`
(section 7 and its connector acceptance contract), `docs/product/control-evidence-sufficiency.md`,
`backend/src/verity/modules/connectors/README.md` (the GitHub connector as built: scope, runs, results),
`docs/runbooks/sso-providers.md` and `keycloak-production.md` (sign in through Keycloak).

## 2. Rules

1. **Accuracy first.** Every claim about a provider's API, permission, scope, endpoint, plan or
   edition requirement, or setup step cites the provider's official documentation (URL in the
   Sources section). Use current documentation (search the web and read the page). When you cannot
   confirm a fact, write "unverified" next to it. Never invent an endpoint, field, scope or setting.
2. **Read only, least privilege.** Verity never writes to a customer's system. Name the narrowest
   permission that collects each item, and say which checks need which permission.
3. **A missing permission or an unreachable API is `error` ("could not check"), never `fail`.** A
   check that cannot see the whole population is `insufficient information`, never `pass`.
4. **Every check states its population, predicate and period:** which resources, what must be true of
   each, over which time window, and what happens on an empty population (an empty list proves
   nothing unless the source can show the population really was empty).
5. **Coverage is honest.** A connector check almost never satisfies a whole control. Say `partial`
   with a rationale naming what remains (usually a document or a person's review).
6. **Own words.** No sentences from AICPA, ISO, NIST, PCI or vendor documentation. Identifiers (CC6.1,
   A.8.5) are fine.
7. **Plain English, short sentences, tables.** No em dashes. Write for the developer who builds it
   next and for the customer who reads the setup guide.
8. **Do not edit** content JSON, code or anything outside `docs/product/evidence-connectors/`.
9. **Collectors may be written in Go.** Name the official Go SDK when one exists (and its import
   path), otherwise the REST or GraphQL API. Keep collection separate from evaluation: a collector
   fetches and normalises observations; checks evaluate them (see `01-evidence-model.md`).

## 3. Names of new checks

A new check key is `<prefix>.<what_must_be_true>` in snake case, written against the capability, not
a vendor. Prefixes and who may add to them in the first research round:

| Prefix | Capability | Owner in round 1 |
|---|---|---|
| `idp.`, `vault.`, `people.` | identity provider, password manager, joiner and leaver | identity research |
| `devices.`, `endpoint.`, `hr.` | device management, endpoint protection, HR system | devices research |
| `cloud.`, `assets.`, `vcs.`, `ci.` | cloud, asset discovery, version control, CI and CD | cloud and code research |
| `tickets.`, `alerts.`, `observability.`, `edge.` | ticketing, on call, observability, network edge | operations research |
| `scanner.`, `apps.`, `ai.` | vulnerability scanner, business applications, AI providers | phase 3 research |
| `verity.` | Verity's own modules | control mapping research, per family |

Reuse an existing key whenever its meaning fits. Control mapping research does not invent connector
keys: it writes a need as `NEED <capability>: <plain predicate>`, and the reconciliation step matches
needs to keys.

## 4. Connector document template

File: `connectors/<provider>.md`, one per provider (`entra-id.md`, `google-workspace.md`, ...).

```
# <Provider>

| | |
|---|---|
| Capabilities | identity_provider, device_management, ... |
| Delivery phase | Phase 2 (signed catalogue) / Phase 3 / not in the signed catalogue |
| Auth model | e.g. OAuth 2.0 client credentials with admin consent |
| Shares setup with | e.g. single sign on (docs/runbooks/sso-providers.md) |
| Go library | e.g. github.com/microsoftgraph/msgraph-sdk-go |

## 1. What it proves
## 2. Connecting: method, credentials and permissions
   table: permission or scope | read only | needed for (check keys) | admin role that can grant it
   plan or licence requirements; vendor side prerequisites (app registration, marketplace listing,
   publisher verification, review lead times)
## 3. Customer setup guide (draft in product text, numbered steps, plain words)
## 4. What Verity collects
   table: resource | API (endpoint or SDK call) | fields kept | paging and rate limits | provider retention
## 5. Checks
   table: check key (existing or NEW) | population | predicate | pass, fail, error, insufficient |
   frequency | evidence kept | controls (code, coverage, rationale)
## 6. Artifacts and objectives it fills
   table: artifact key (artifacts.json) | objective codes | control | change (person -> person + check)
## 7. Framework reach
   SOC 2 criteria and ISO 27001:2022 Annex A references reached through the controls above
## 8. Limits and false assurance traps
## 9. Product and UI
   connect form fields, scope selection, health states, in product guide needed (yes/no and why)
## 10. Implementation notes
   Go collector: auth flow, token refresh, paging, rate limits, recorded fixtures, test accounts,
   error mapping, scope drift, deletion semantics
## 11. How comparable platforms do it
   Vanta, Drata, Secureframe, Sprinto, others: auth model and what they test, with sources
## 12. Sources
```

## 5. Control mapping files

File: `coverage/<families>.md` plus `coverage/<families>.json`.

The JSON is a list, one entry per artifact of the families covered:

```json
{
  "artifact": "account-list-export",
  "control": "IAM-02",
  "objectives": ["IAM-02.B"],
  "today": ["person"],
  "planned": [
    {"kind": "check", "check": "idp.access_list_exported", "provider_capability": "identity_provider", "fills": "full|partial", "note": "..."},
    {"kind": "need", "capability": "identity_provider", "predicate": "...", "fills": "partial"},
    {"kind": "module", "module": "assets", "report": "...", "check": "verity.assets.reviewed"},
    {"kind": "document", "template": "access-control-policy"},
    {"kind": "person", "what": "upload of the signed review"}
  ],
  "phase": "P1|P2|P3|people-only",
  "notes": "..."
}
```

The markdown explains, control by control, why each source fits, what stays with people, and which
objectives no system can ever prove (interviews, judgements, signatures).

## 6. Control breakdown and objective revisions (owner's request, 2026-11-23)

The 133 controls may need to be broken down further, because SOC 2 and ISO 27001 differ in nature:
SOC 2 criteria are principles a service auditor tests over a period, ISO 27001 Annex A controls are
selected through risk treatment and recorded in the Statement of Applicability, and ISO clauses 4 to
10 are management system duties. A control that bundles activities with different owners, cadences,
applicability, evidence or remediation cannot be assessed honestly as one. Review every control of
your families against all the requirements it maps to in both frameworks and decide:

| Decision | Use when |
|---|---|
| keep | One coherent activity; objectives and artifacts are enough |
| revise objectives | The control is right but its objectives miss a requirement it claims (for example an ISO qualifier or a SOC 2 point the mapping relies on), or an objective is untestable or bundles two things |
| split | Different activities need independent ownership, cadence, applicability (one part could be not applicable while the other applies) or remediation conclusions; or the control maps `full` to requirements of different nature |
| add | A requirement has no suitable control after gap review |
| merge or deprecate | Two controls duplicate one activity (never merge from names alone) |

Follow `docs/product/continuous-compliance-plan.md` section 4. Rules: existing codes never change
meaning or get reused; a split keeps the original code for the part that stays and gives successors
new codes (next free number in the family, marked "proposed"); objectives move with the activity they
test and keep their letter codes where possible; every mapping change states requirement, control,
coverage and rationale; note what existing workspaces need (data migration, adoption proposal, no
copying of a green result or a risk acceptance to a successor). Objective statements are in Verity's
own words. A split is a proposal for qualified review, never applied by this plan.

Output, per coverage file pair, a third file `coverage/<families>.controls.json`, a list with one
entry per control:

```json
{
  "control": "LM-11",
  "decision": "keep | revise_objectives | split | add | merge",
  "reason": "plain words, naming the requirements (SOC2:CC7.1, ISO27001:A.8.8) that drive it",
  "successors": [
    {"code": "LM-13", "status": "proposed", "name": "...", "takes_objectives": ["LM-11.B"],
     "requirements": [{"key": "ISO27001:A.8.8", "coverage": "partial", "rationale": "..."}]}
  ],
  "objective_changes": [
    {"code": "LM-11.F", "change": "add | reword | move | remove", "statement": "...",
     "assurance": "design | operating", "methods": [{"method": "test", "artifacts": ["..."]}],
     "why": "..."}
  ],
  "tenant_impact": "none | adoption proposal | data migration: ..."
}
```

and a section "Proposed control changes" at the top of the coverage markdown. The coverage JSON (the
artifact mapping) then uses the proposed structure: artifacts of a successor control are listed under
the successor's code with `"control_status": "proposed"`.
