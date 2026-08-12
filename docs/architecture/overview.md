# Architecture overview

## What the system does

Maps SOC 2 Trust Services Criteria to a managed control set, holds the evidence proving each
control, and connects tasks, documents, risks, vendors, assets, and vulnerabilities into one graph
so impact can be traced in any direction. From Phase 2 it connects to the organisation's systems,
collects evidence automatically, and monitors on a schedule.

## Shape

```
Browser  -->  React SPA
                 |
                 v
           FastAPI (modular monolith)
             |        |        |
             v        v        v
       PostgreSQL   Redis   Object storage
         (RLS)        |      (evidence files)
                      v
             Celery workers + scheduler
                      |
                      v
              Connectors (read-only, per provider)

  Native auth now / external OIDC IdP later  -->  authentication for both planes
```

One deployable backend, one database, workers from the same codebase. See
[ADR-0008](../adr/0008-modular-monolith.md) for why not microservices.

## Controls are the hub

Requirements justify controls. Evidence proves controls. Every other module traces back to them.

- **Frameworks, requirements, control templates, checks, and question banks are global shipped
  content** with no `tenant_id`. Adding ISO 27001, HIPAA, or GDPR is inserting content, never
  changing schema.
- **Tenant creation instantiates the library**: each control template becomes a tenant control
  carrying `template_id`, and requirement mappings are copied into the tenant's map.
- **Evidence anchors to controls, not requirements** ([ADR-0004](../adr/0004-evidence-anchors-to-controls.md)),
  which is what makes collect-once-satisfy-many work.

## Modules

| Module | Owns |
|---|---|
| `tenancy` | Provider plane: tenants, branding, provisioning |
| `iam` | Users, groups, roles, permissions, identities |
| `compliance` | Frameworks, requirements, controls, engagements, readiness |
| `evidence` | Evidence items, types, validity, staleness |
| `tasks` | Tasks, transitions, SLA definitions |
| `documents` | Templates, versions, variables, acknowledgement campaigns |
| `risk` | Risk register, matrix settings, acceptances, ERM (Phase 3) |
| `vendors` | Full TPRM lifecycle: intake, tiering, assessments, findings, offboarding |
| `assets` | Inventory, merge, relationships, software, policies, violations |
| `vulnerabilities` | Definitions, instances, scoring, SLA, exceptions, remediation |
| `connectors` | Connector framework, connections, checks, results, findings |
| `approvals` | The single sign-off record for the whole platform |
| `audit` | Append-only audit log |
| `ai` | Drafting and proposal generation — never publishes, never decides |
| `notifications` | Alerts, digests, reminders |

## Cross-cutting mechanisms

**Approvals.** One `approvals` table serves evidence review, control sign-off, document approval,
risk acceptance, and TPRM gate exits. One mechanism, one pending queue, one audit surface. TPRM
keeps a richer `vendor_approvals` record because its decision set (approve with conditions, defer)
goes beyond approve/reject.

**Links.** The 360-degree model rides a hybrid: explicit join tables for hot pairs, one polymorphic
`links` table for the long tail, direct FKs for one-way promotions
([ADR-0003](../adr/0003-hybrid-linkage-model.md)).

**Audit log.** Append-only, before/after snapshots, no updates and no deletes ever.

**Integration fields.** `source`, `external_id`, `synced_at` on every ingestible table from day one,
so every future connector is an idempotent upsert against tables that already exist.

## The demonstration that proves the model

Trace a vulnerability to its asset, the asset to a risk, the risk to a control, the control to a
policy and its evidence. Four hops, all indexed, every step in the audit trail. This is a Phase 1
exit criterion — treat it as an integration test, not a demo script.
