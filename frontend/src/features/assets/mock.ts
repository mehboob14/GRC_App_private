/**
 * In-memory mock for the Asset module (Phase A).
 *
 * Stands in for the backend so the screens are real and reviewable before the
 * API exists. api.ts reads and writes through here; at Phase C its internals
 * swap to `apiFetch` and this file is deleted.
 *
 * The rules that must match the real service are kept as pure functions so the
 * behaviour is identical on both sides: the lifecycle allow-list, the ISO 27005
 * criticality scorer, and the hygiene computation.
 */

import type {
  AssetDetail,
  AssetLink,
  AssetRelationship,
  AssetStatus,
  AssetType,
  CiaRating,
  Criticality,
  CriticalityTier,
  DataClassification,
  DecommissionRecord,
  Environment,
  Hygiene,
  HygieneFlag,
  LinkTarget,
  Member,
  Ownership,
} from "./types";
import { LINK_TARGETS } from "./types";

// -- shared rules (mirror the future service) --------------------------------

/** The only legal lifecycle moves out of each state. Served to the client as
 *  `allowed_transitions`, never hardcoded in a component. `retired` is terminal. */
export const LIFECYCLE_TRANSITIONS: Record<AssetStatus, AssetStatus[]> = {
  planned: ["active", "retired"],
  active: ["in_maintenance", "decommissioned"],
  in_maintenance: ["active", "decommissioned"],
  decommissioned: ["retired", "active"], // retire, or reinstate
  retired: [],
};

const DAY = 86_400_000;
const STALE_DAYS = 90;
const HARM: Record<CiaRating, number> = { 1: 2, 2: 4, 3: 6, 4: 8, 5: 10 };

/** Business functions that carry the +1.5 criticality boost. In the real backend
 *  this is the `high_impact` flag on the business-function catalogue; the mock
 *  keeps the same small set so create/update can recompute from the stored name. */
export const HIGH_IMPACT_FUNCTIONS = new Set([
  "Payment processing",
  "Authentication / IAM",
  "Regulated data (PHI)",
  "Customer data",
  "Financial reporting",
]);
export function isHighImpact(fn: string | null): boolean {
  return fn != null && HIGH_IMPACT_FUNCTIONS.has(fn);
}

/** The reference's ISO 27005 scorer: base = MAX of the rated CIA values (highest
 *  harm wins, not a sum), then exposure and data-sensitivity boosts, clamped to
 *  [0,10]. Returns null when NOTHING is rated — no phantom default. */
export function computeCriticality(
  cia: { c: CiaRating | null; i: CiaRating | null; a: CiaRating | null },
  ctx: {
    internet_facing: boolean;
    data_classification: DataClassification | null;
    business_function_high_impact: boolean;
  },
): { score: number; tier: CriticalityTier } | null {
  const rated = [cia.c, cia.i, cia.a].filter((r): r is CiaRating => r != null);
  if (rated.length === 0) return null;
  let score = Math.max(...rated.map((r) => HARM[r]));
  if (ctx.internet_facing) score += 2.5;
  if (ctx.data_classification === "restricted") score += 1.5;
  else if (ctx.data_classification === "confidential") score += 1.0;
  if (ctx.business_function_high_impact) score += 1.5;
  score = Math.min(10, Math.round(score * 10) / 10);
  const tier: CriticalityTier =
    score >= 8.5 ? "critical" : score >= 6.5 ? "high" : score >= 4.0 ? "medium" : "low";
  return { score, tier };
}

/** The tier actually shown/inherited: a human override wins, else the computed
 *  tier, else null (not assessed). */
export function effectiveTier(c: Criticality): CriticalityTier | null {
  return c.tier_override ?? c.tier;
}

export function isStale(last: string | null): boolean {
  if (!last) return false;
  return Date.now() - new Date(last).getTime() > STALE_DAYS * DAY;
}

/** Five checks; NULL means unmet, so an unassessed record scores low honestly. */
export function computeHygiene(a: {
  asset_type: AssetType | null;
  data_classification: DataClassification | null;
  criticality: Criticality;
  ownership: Ownership;
  last_reviewed_at: string | null;
  last_seen_at: string | null;
}): Hygiene {
  const missing: HygieneFlag[] = [];
  if (!a.ownership.primary_owner) missing.push("no_owner");
  if (!a.asset_type) missing.push("no_type");
  if (effectiveTier(a.criticality) == null) missing.push("no_criticality");
  if (!a.data_classification) missing.push("no_classification");
  if (
    a.criticality.confidentiality == null ||
    a.criticality.integrity == null ||
    a.criticality.availability == null
  ) {
    missing.push("no_cia");
  }
  return {
    score: Math.round(((5 - missing.length) / 5) * 100),
    missing,
    is_stale: isStale(a.last_reviewed_at ?? a.last_seen_at),
  };
}

function iso(offsetMs: number): string {
  return new Date(Date.now() + offsetMs).toISOString();
}

// -- seed: people ------------------------------------------------------------

const M = {
  sana: { membership_id: "m-sana", name: "Sana Malik" },
  omar: { membership_id: "m-omar", name: "Omar Reyes" },
  lena: { membership_id: "m-lena", name: "Lena Fischer" },
  priya: { membership_id: "m-priya", name: "Priya Nair" },
  tom: { membership_id: "m-tom", name: "Tom Becker" },
} satisfies Record<string, Member>;

export const MEMBERS: Member[] = Object.values(M);
export const CURRENT_MEMBER = M.sana;

// -- seed: assets ------------------------------------------------------------

type Seed = {
  id: string;
  name: string;
  asset_type: AssetType;
  status: AssetStatus;
  description?: string;
  hostname?: string;
  ip_address?: string;
  fqdn?: string;
  os_normalized?: string;
  environment?: Environment;
  location?: string;
  vendor_ref?: string;
  data_classification?: DataClassification;
  regulated_data_type?: string;
  compliance_scope?: string[];
  internet_facing?: boolean;
  customer_facing?: boolean;
  network_segment?: string;
  business_function?: string;
  business_function_high_impact?: boolean;
  cia?: [CiaRating | null, CiaRating | null, CiaRating | null];
  tier_override?: CriticalityTier;
  tier_override_reason?: string;
  ownership?: Partial<Ownership>;
  valuation?: number;
  serial_number?: string;
  primary_mac?: string;
  cloud_resource_id?: string;
  business_impact_notes?: string;
  operational_dependency_rating?: string;
  replaced_by_asset_id?: string;
  decommission?: DecommissionRecord;
  links?: AssetLink[];
  relationships?: AssetRelationship[];
  watchers?: Member[];
  vuln_count?: number;
  first_seen_at?: string;
  last_seen_at?: string;
  last_reviewed_at?: string;
  created_at?: string;
};

function ownership(partial?: Partial<Ownership>): Ownership {
  return {
    primary_owner: partial?.primary_owner ?? null,
    secondary_owner: partial?.secondary_owner ?? null,
    business_owner: partial?.business_owner ?? null,
    custodian: partial?.custodian ?? null,
    escalation_contact: partial?.escalation_contact ?? null,
    owning_team: partial?.owning_team ?? null,
  };
}

function linkedSummary(links: AssetLink[]): Record<LinkTarget, number> {
  const out = Object.fromEntries(LINK_TARGETS.map((t) => [t, 0])) as Record<LinkTarget, number>;
  for (const l of links) out[l.to_type] += 1;
  return out;
}

function build(seed: Seed): AssetDetail {
  const created = seed.created_at ?? iso(-40 * DAY);
  const [c, i, a] = seed.cia ?? [null, null, null];
  const computed = computeCriticality(
    { c, i, a },
    {
      internet_facing: seed.internet_facing ?? false,
      data_classification: seed.data_classification ?? null,
      business_function_high_impact:
        seed.business_function_high_impact ?? isHighImpact(seed.business_function ?? null),
    },
  );
  const criticality: Criticality = {
    confidentiality: c,
    integrity: i,
    availability: a,
    score: computed?.score ?? null,
    tier: computed?.tier ?? null,
    tier_override: seed.tier_override ?? null,
    tier_override_reason: seed.tier_override_reason ?? null,
  };
  const own = ownership(seed.ownership);
  const links = seed.links ?? [];
  const relationships = seed.relationships ?? [];
  const last_reviewed_at = seed.last_reviewed_at ?? null;
  const last_seen_at = seed.last_seen_at ?? null;
  const hygiene = computeHygiene({
    asset_type: seed.asset_type,
    data_classification: seed.data_classification ?? null,
    criticality,
    ownership: own,
    last_reviewed_at,
    last_seen_at,
  });

  return {
    id: seed.id,
    name: seed.name,
    asset_type: seed.asset_type,
    description: seed.description ?? "",
    hostname: seed.hostname ?? null,
    ip_address: seed.ip_address ?? null,
    fqdn: seed.fqdn ?? null,
    os_normalized: seed.os_normalized ?? null,
    environment: seed.environment ?? null,
    location: seed.location ?? null,
    vendor_ref: seed.vendor_ref ?? null,
    data_classification: seed.data_classification ?? null,
    regulated_data_type: seed.regulated_data_type ?? null,
    compliance_scope: seed.compliance_scope ?? [],
    internet_facing: seed.internet_facing ?? false,
    customer_facing: seed.customer_facing ?? false,
    network_segment: seed.network_segment ?? null,
    business_function: seed.business_function ?? null,
    criticality,
    ownership: own,
    status: seed.status,
    replaced_by_asset_id: seed.replaced_by_asset_id ?? null,
    valuation: seed.valuation ?? null,
    first_seen_at: seed.first_seen_at ?? created,
    last_seen_at,
    last_reviewed_at,
    created_at: created,
    updated_at: seed.last_seen_at ?? created,
    source: "manual",
    hygiene,
    vuln_count: seed.vuln_count ?? 0,
    link_count: links.length,
    relationship_count: relationships.length,
    // detail-only
    serial_number: seed.serial_number ?? null,
    primary_mac: seed.primary_mac ?? null,
    cloud_resource_id: seed.cloud_resource_id ?? null,
    business_impact_notes: seed.business_impact_notes ?? null,
    operational_dependency_rating: seed.operational_dependency_rating ?? null,
    decommission: seed.decommission ?? null,
    transitions: [
      {
        id: `${seed.id}-t0`,
        actor: CURRENT_MEMBER.name,
        field_changed: "created",
        old_value: null,
        new_value: seed.name,
        note: null,
        occurred_at: created,
      },
    ],
    links,
    relationships,
    linked_summary: linkedSummary(links),
    watchers: seed.watchers ?? [],
    allowed_transitions: LIFECYCLE_TRANSITIONS[seed.status],
  };
}

const SEEDS: Seed[] = [
  {
    id: "ast-billing",
    name: "Customer billing platform",
    asset_type: "business_service",
    status: "active",
    description: "Customer-facing billing and subscription service. Processes cardholder data.",
    environment: "prod",
    internet_facing: true,
    customer_facing: true,
    data_classification: "restricted",
    regulated_data_type: "cardholder_data",
    compliance_scope: ["SOC2", "PCI"],
    business_function: "Payment processing",
    business_function_high_impact: true,
    cia: [5, 5, 4],
    ownership: {
      primary_owner: M.omar,
      secondary_owner: M.tom,
      business_owner: M.lena,
      owning_team: "Payments Engineering",
    },
    valuation: 4_200_000,
    business_impact_notes: "Revenue-critical; outage stops all customer billing.",
    operational_dependency_rating: "very_high",
    vuln_count: 3,
    last_reviewed_at: iso(-20 * DAY),
    last_seen_at: iso(-2 * DAY),
    links: [
      { id: "l1", to_type: "control", to_id: "c-cc61", to_label: "CC6.1 · Logical access controls", relation: "relates_to", note: null },
      { id: "l2", to_type: "risk", to_id: "r-pci", to_label: "Cardholder data exposure", relation: "relates_to", note: null },
      { id: "l3", to_type: "document", to_id: "d-datamap", to_label: "Data flow map", relation: "relates_to", note: null },
    ],
    relationships: [
      { id: "rel1", direction: "outbound", type: "depends_on", other_asset_id: "ast-db", other_asset_name: "prod-db-01 (billing)", provenance: "declared" },
    ],
    watchers: [M.sana],
  },
  {
    id: "ast-db",
    name: "prod-db-01 (billing)",
    asset_type: "infrastructure",
    status: "active",
    description: "Primary PostgreSQL for the billing platform.",
    hostname: "prod-db-01",
    ip_address: "10.4.1.20",
    fqdn: "prod-db-01.internal.acme.io",
    os_normalized: "ubuntu-22.04",
    environment: "prod",
    network_segment: "data-tier",
    data_classification: "confidential",
    business_function: "Payment processing",
    cia: [5, 4, 4],
    ownership: { primary_owner: M.tom, owning_team: "Platform" },
    serial_number: "SN-DB01-9931",
    primary_mac: "02:42:ac:11:00:14",
    valuation: 180_000,
    vuln_count: 5,
    last_reviewed_at: iso(-25 * DAY),
    last_seen_at: iso(-1 * DAY),
    relationships: [
      { id: "rel2", direction: "inbound", type: "depends_on", other_asset_id: "ast-billing", other_asset_name: "Customer billing platform", provenance: "declared" },
    ],
    links: [{ id: "l4", to_type: "control", to_id: "c-cc63", to_label: "CC6.3 · Data at rest encryption", relation: "relates_to", note: null }],
  },
  {
    id: "ast-auth",
    name: "Identity service (Keycloak)",
    asset_type: "application",
    status: "active",
    description: "Central authentication and SSO for all workspaces.",
    hostname: "auth-01",
    fqdn: "auth.acme.io",
    os_normalized: "ubuntu-22.04",
    environment: "prod",
    internet_facing: true,
    data_classification: "confidential",
    business_function: "Authentication / IAM",
    business_function_high_impact: true,
    cia: [4, 5, 5],
    ownership: { primary_owner: M.omar, escalation_contact: M.sana, owning_team: "Security" },
    valuation: 90_000,
    vuln_count: 1,
    last_reviewed_at: iso(-10 * DAY),
    last_seen_at: iso(-1 * DAY),
  },
  {
    id: "ast-evidence",
    name: "Evidence object store",
    asset_type: "cloud",
    status: "active",
    description: "S3 bucket holding compliance evidence artifacts.",
    cloud_resource_id: "arn:aws:s3:::acme-verity-evidence",
    environment: "prod",
    internet_facing: false,
    data_classification: "confidential",
    compliance_scope: ["SOC2"],
    cia: [4, 3, 3],
    ownership: { primary_owner: M.sana, custodian: M.tom, owning_team: "Security" },
    last_reviewed_at: iso(-15 * DAY),
    last_seen_at: iso(-1 * DAY),
    links: [{ id: "l5", to_type: "evidence", to_id: "e-store", to_label: "Evidence retention export", relation: "relates_to", note: null }],
  },
  {
    id: "ast-analytics",
    name: "Analytics read replica",
    asset_type: "data",
    status: "in_maintenance",
    description: "Reporting replica of the product database. CIA not yet assessed.",
    hostname: "analytics-replica-01",
    environment: "staging",
    network_segment: "data-tier",
    // deliberately unassessed: no CIA, no classification, no owner -> hygiene low, tier "— assess"
    ownership: {},
    last_seen_at: iso(-3 * DAY),
  },
  {
    id: "ast-payments-api",
    name: "Northwind Payments API",
    asset_type: "third_party",
    status: "active",
    description: "External payment processor integration.",
    vendor_ref: "Northwind Payments",
    internet_facing: true,
    customer_facing: true,
    data_classification: "restricted",
    regulated_data_type: "cardholder_data",
    compliance_scope: ["PCI"],
    business_function: "Payment processing",
    business_function_high_impact: true,
    cia: [4, 4, 3],
    ownership: { primary_owner: M.priya, business_owner: M.lena },
    last_reviewed_at: iso(-30 * DAY),
    last_seen_at: iso(-5 * DAY),
    links: [{ id: "l6", to_type: "vendor", to_id: "v-northwind", to_label: "Northwind Payments", relation: "relates_to", note: null }],
  },
  {
    id: "ast-fileserver",
    name: "legacy-fileserver-02",
    asset_type: "infrastructure",
    status: "decommissioned",
    description: "Retired on-prem file server; replaced by cloud storage.",
    hostname: "legacy-fileserver-02",
    os_normalized: "windows-server-2016",
    environment: "prod",
    data_classification: "internal",
    cia: [2, 2, 2],
    ownership: { primary_owner: M.tom, owning_team: "IT" },
    serial_number: "SN-FS02-1187",
    replaced_by_asset_id: "ast-evidence",
    decommission: {
      disposal_method: "wiped_and_recycled",
      media_sanitised: true,
      replacement_asset_id: "ast-evidence",
      evidence_ref: "disposal-cert-2026-03",
      reason: "End of life; workloads migrated to cloud storage.",
      decommissioned_by: M.tom.name,
      decommissioned_at: iso(-120 * DAY),
    },
    last_reviewed_at: iso(-200 * DAY),
    last_seen_at: iso(-130 * DAY),
  },
  {
    id: "ast-marketing",
    name: "Marketing website",
    asset_type: "application",
    status: "active",
    description: "Public marketing site. No customer data.",
    fqdn: "www.acme.io",
    environment: "prod",
    internet_facing: true,
    data_classification: "public",
    business_function: "Marketing",
    cia: [1, 2, 2],
    ownership: { primary_owner: M.lena, owning_team: "Marketing" },
    last_reviewed_at: iso(-45 * DAY),
    last_seen_at: iso(-1 * DAY),
  },
  {
    id: "ast-datalake",
    name: "Analytics data lake (planned)",
    asset_type: "cloud",
    status: "planned",
    description: "Planned data lake for product analytics. Not yet assessed or built.",
    environment: "dev",
    ownership: { primary_owner: M.priya },
  },
];

// -- mutable store -----------------------------------------------------------

/** Module-level array, mutated in place — a session-lived store, so a create or
 *  transition is visible on the next query, same as a real API. */
export const STORE: AssetDetail[] = SEEDS.map(build);

/** Every read recomputes hygiene through the clock so nothing shows a stale
 *  freshness badge. */
export function all(): AssetDetail[] {
  for (const asset of STORE) {
    asset.hygiene = computeHygiene(asset);
  }
  return STORE;
}

let counter = SEEDS.length;
export function nextId(): string {
  counter += 1;
  return `ast-${counter}`;
}

export function findMember(id: string | null): Member | null {
  if (!id) return null;
  return MEMBERS.find((m) => m.membership_id === id) ?? null;
}
