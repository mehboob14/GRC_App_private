/**
 * Data layer for the Asset module.
 *
 * Phase A: every function reads/writes the in-memory mock (mock.ts) so the
 * screens work before the backend exists. Phase C: the bodies swap to
 * `apiFetch(...)` and mock.ts is deleted. The exported signatures — the contract
 * the components depend on — do not change across that swap.
 */

import {
  CURRENT_MEMBER,
  LIFECYCLE_TRANSITIONS,
  MEMBERS,
  STORE,
  all,
  computeCriticality,
  computeHygiene,
  effectiveTier,
  findMember,
  isHighImpact,
  nextId,
} from "./mock";
import type {
  Asset,
  AssetDetail,
  AssetFilters,
  AssetPage,
  AssetStatus,
  AssetSummary,
  AssetType,
  CiaRating,
  Criticality,
  CriticalityTier,
  DataClassification,
  DecommissionRecord,
  Environment,
  Member,
  Ownership,
  RelationshipType,
  SavedView,
} from "./types";
import { ASSET_STATUSES } from "./types";

/** Small latency so loading and empty states are exercised during the build. */
const wait = (ms = 140) => new Promise((r) => setTimeout(r, ms));

const TIER_RANK: Record<CriticalityTier, number> = { critical: 0, high: 1, medium: 2, low: 3 };

function needsAttention(a: AssetDetail): boolean {
  return a.hygiene.missing.length > 0 || a.hygiene.is_stale;
}

function toRow(a: AssetDetail): Asset {
  return {
    id: a.id,
    name: a.name,
    asset_type: a.asset_type,
    description: a.description,
    hostname: a.hostname,
    ip_address: a.ip_address,
    fqdn: a.fqdn,
    os_normalized: a.os_normalized,
    environment: a.environment,
    location: a.location,
    vendor_ref: a.vendor_ref,
    data_classification: a.data_classification,
    regulated_data_type: a.regulated_data_type,
    compliance_scope: a.compliance_scope,
    internet_facing: a.internet_facing,
    customer_facing: a.customer_facing,
    network_segment: a.network_segment,
    business_function: a.business_function,
    criticality: a.criticality,
    ownership: a.ownership,
    status: a.status,
    replaced_by_asset_id: a.replaced_by_asset_id,
    valuation: a.valuation,
    first_seen_at: a.first_seen_at,
    last_seen_at: a.last_seen_at,
    last_reviewed_at: a.last_reviewed_at,
    created_at: a.created_at,
    updated_at: a.updated_at,
    source: a.source,
    hygiene: a.hygiene,
    vuln_count: a.vuln_count,
    link_count: a.link_count,
    relationship_count: a.relationship_count,
  };
}

function matches(a: AssetDetail, f: Partial<AssetFilters>): boolean {
  if (f.asset_type && f.asset_type !== "all" && a.asset_type !== f.asset_type) return false;
  if (f.statuses?.length && !f.statuses.includes(a.status)) return false;
  if (f.tiers?.length) {
    const tier = effectiveTier(a.criticality);
    if (!tier || !f.tiers.includes(tier)) return false;
  }
  if (f.environments?.length && (!a.environment || !f.environments.includes(a.environment)))
    return false;
  if (f.classifications?.length && (!a.data_classification || !f.classifications.includes(a.data_classification)))
    return false;
  if (f.exposure === "internet_facing" && !a.internet_facing) return false;
  if (f.exposure === "customer_facing" && !a.customer_facing) return false;
  if (f.needs_attention && !needsAttention(a)) return false;
  if (f.owner) {
    const owner = a.ownership.primary_owner;
    if (f.owner === "unassigned" && owner) return false;
    if (f.owner === "me" && owner?.membership_id !== CURRENT_MEMBER.membership_id) return false;
    if (f.owner !== "me" && f.owner !== "unassigned" && owner?.membership_id !== f.owner) return false;
  }
  if (f.search) {
    const q = f.search.toLowerCase();
    const hay = [a.name, a.hostname, a.ip_address, a.fqdn].filter(Boolean).join(" ").toLowerCase();
    if (!hay.includes(q)) return false;
  }
  return true;
}

/** Criticality desc (unassessed last), then attention, then name. */
function compare(a: Asset, b: Asset): number {
  const at = effectiveTier(a.criticality);
  const bt = effectiveTier(b.criticality);
  const ar = at ? TIER_RANK[at] : 9;
  const br = bt ? TIER_RANK[bt] : 9;
  if (ar !== br) return ar - br;
  const aAtt = a.hygiene.missing.length > 0 || a.hygiene.is_stale ? 0 : 1;
  const bAtt = b.hygiene.missing.length > 0 || b.hygiene.is_stale ? 0 : 1;
  if (aAtt !== bAtt) return aAtt - bAtt;
  return a.name.localeCompare(b.name);
}

// -- reads -------------------------------------------------------------------

export async function listAssets(
  filters: Partial<AssetFilters>,
  page = 1,
  pageSize = 25,
): Promise<AssetPage> {
  await wait();
  const rows = all().filter((a) => matches(a, filters)).map(toRow).sort(compare);
  const start = (page - 1) * pageSize;
  return { items: rows.slice(start, start + pageSize), total: rows.length };
}

export async function getAsset(id: string): Promise<AssetDetail | null> {
  await wait();
  const a = all().find((x) => x.id === id) ?? null;
  if (!a) return null;
  a.allowed_transitions = LIFECYCLE_TRANSITIONS[a.status];
  // Return a fresh clone: the mock mutates STORE objects in place, so handing
  // React Query the same reference on every refetch would leave the view stale
  // (structural sharing sees no change). A new object graph forces the re-render.
  return structuredClone(a);
}

/** Facet counts for the register filter bar, over the whole (unfiltered) estate. */
export async function getFacets(): Promise<{
  asset_type: Record<AssetType, number>;
  tier: Record<CriticalityTier | "unassessed", number>;
  status: Record<AssetStatus, number>;
  environment: Record<Environment, number>;
  needs_attention: number;
}> {
  await wait(60);
  const assets = all();
  const asset_type = {} as Record<AssetType, number>;
  const status = {} as Record<AssetStatus, number>;
  const environment = {} as Record<Environment, number>;
  const tier = { critical: 0, high: 0, medium: 0, low: 0, unassessed: 0 } as Record<
    CriticalityTier | "unassessed",
    number
  >;
  let needs_attention = 0;
  for (const a of assets) {
    asset_type[a.asset_type] = (asset_type[a.asset_type] ?? 0) + 1;
    status[a.status] = (status[a.status] ?? 0) + 1;
    if (a.environment) environment[a.environment] = (environment[a.environment] ?? 0) + 1;
    const t = effectiveTier(a.criticality);
    tier[t ?? "unassessed"] += 1;
    if (needsAttention(a)) needs_attention += 1;
  }
  return { asset_type, tier, status, environment, needs_attention };
}

export async function getSummary(): Promise<AssetSummary> {
  await wait();
  const assets = all();
  const by_tier = { critical: 0, high: 0, medium: 0, low: 0, unassessed: 0 } as AssetSummary["by_tier"];
  const by_status = Object.fromEntries(ASSET_STATUSES.map((s) => [s, 0])) as Record<AssetStatus, number>;
  const typeMap = new Map<AssetType, number>();
  let needs_cia = 0;
  let regulated = 0;
  let stale = 0;
  let hygieneTotal = 0;
  for (const a of assets) {
    const t = effectiveTier(a.criticality);
    by_tier[t ?? "unassessed"] += 1;
    by_status[a.status] += 1;
    typeMap.set(a.asset_type, (typeMap.get(a.asset_type) ?? 0) + 1);
    if (a.hygiene.missing.includes("no_cia")) needs_cia += 1;
    if (a.regulated_data_type || a.compliance_scope.includes("PCI")) regulated += 1;
    if (a.hygiene.is_stale) stale += 1;
    hygieneTotal += a.hygiene.score;
  }
  return {
    total: assets.length,
    by_tier,
    by_type: [...typeMap.entries()].map(([type, count]) => ({ type, count })).sort((x, y) => y.count - x.count),
    by_status,
    needs_cia,
    regulated,
    stale,
    hygiene_avg: assets.length ? Math.round(hygieneTotal / assets.length) : 0,
  };
}

export async function listMembers(): Promise<Member[]> {
  await wait(60);
  return MEMBERS;
}

export async function listSavedViews(): Promise<SavedView[]> {
  await wait(60);
  return SAVED_VIEWS;
}

const SAVED_VIEWS: SavedView[] = [
  { id: "v-mine", name: "My assets", filters: { owner: "me" }, is_shared: false, position: 0 },
  { id: "v-critical", name: "Critical", filters: { tiers: ["critical"] }, is_shared: true, position: 1 },
  { id: "v-attention", name: "Needs attention", filters: { needs_attention: true }, is_shared: true, position: 2 },
  { id: "v-internet", name: "Internet-facing", filters: { exposure: "internet_facing" }, is_shared: true, position: 3 },
];

// -- writes ------------------------------------------------------------------

/** Everything the create/edit form can set. Criticality is derived, so the form
 *  supplies the CIA inputs and the override, never the score/tier. */
export type AssetInput = {
  name: string;
  asset_type: AssetType;
  description: string;
  hostname: string | null;
  ip_address: string | null;
  environment: Environment | null;
  location: string | null;
  vendor_ref: string | null;
  data_classification: DataClassification | null;
  regulated_data_type: string | null;
  compliance_scope: string[];
  internet_facing: boolean;
  customer_facing: boolean;
  network_segment: string | null;
  business_function: string | null;
  confidentiality: CiaRating | null;
  integrity: CiaRating | null;
  availability: CiaRating | null;
  tier_override: CriticalityTier | null;
  tier_override_reason: string | null;
  primary_owner_id: string | null;
  secondary_owner_id: string | null;
  business_owner_id: string | null;
  custodian_id: string | null;
  escalation_contact_id: string | null;
  owning_team: string | null;
  valuation: number | null;
  business_impact_notes: string | null;
  operational_dependency_rating: string | null;
};

function criticalityFrom(input: {
  confidentiality: CiaRating | null;
  integrity: CiaRating | null;
  availability: CiaRating | null;
  internet_facing: boolean;
  data_classification: DataClassification | null;
  business_function: string | null;
  tier_override: CriticalityTier | null;
  tier_override_reason: string | null;
}): Criticality {
  const computed = computeCriticality(
    { c: input.confidentiality, i: input.integrity, a: input.availability },
    {
      internet_facing: input.internet_facing,
      data_classification: input.data_classification,
      business_function_high_impact: isHighImpact(input.business_function),
    },
  );
  return {
    confidentiality: input.confidentiality,
    integrity: input.integrity,
    availability: input.availability,
    score: computed?.score ?? null,
    tier: computed?.tier ?? null,
    tier_override: input.tier_override,
    tier_override_reason: input.tier_override_reason,
  };
}

function ownershipFrom(input: AssetInput): Ownership {
  return {
    primary_owner: findMember(input.primary_owner_id),
    secondary_owner: findMember(input.secondary_owner_id),
    business_owner: findMember(input.business_owner_id),
    custodian: findMember(input.custodian_id),
    escalation_contact: findMember(input.escalation_contact_id),
    owning_team: input.owning_team,
  };
}

/** Live criticality preview for the form — computes without persisting. */
export function previewCriticality(input: {
  confidentiality: CiaRating | null;
  integrity: CiaRating | null;
  availability: CiaRating | null;
  internet_facing: boolean;
  data_classification: DataClassification | null;
  business_function: string | null;
}): { score: number; tier: CriticalityTier } | null {
  return computeCriticality(
    { c: input.confidentiality, i: input.integrity, a: input.availability },
    {
      internet_facing: input.internet_facing,
      data_classification: input.data_classification,
      business_function_high_impact: isHighImpact(input.business_function),
    },
  );
}

export async function createAsset(input: AssetInput): Promise<AssetDetail> {
  await wait();
  const now = new Date().toISOString();
  const id = nextId();
  const criticality = criticalityFrom({ ...input });
  const ownership = ownershipFrom(input);
  const created: AssetDetail = {
    id,
    name: input.name.trim(),
    asset_type: input.asset_type,
    description: input.description.trim(),
    hostname: input.hostname,
    ip_address: input.ip_address,
    fqdn: null,
    os_normalized: null,
    environment: input.environment,
    location: input.location,
    vendor_ref: input.vendor_ref,
    data_classification: input.data_classification,
    regulated_data_type: input.regulated_data_type,
    compliance_scope: input.compliance_scope,
    internet_facing: input.internet_facing,
    customer_facing: input.customer_facing,
    network_segment: input.network_segment,
    business_function: input.business_function,
    criticality,
    ownership,
    status: "planned",
    replaced_by_asset_id: null,
    valuation: input.valuation,
    first_seen_at: now,
    last_seen_at: null,
    last_reviewed_at: now,
    created_at: now,
    updated_at: now,
    source: "manual",
    hygiene: { score: 0, missing: [], is_stale: false },
    vuln_count: 0,
    link_count: 0,
    relationship_count: 0,
    serial_number: null,
    primary_mac: null,
    cloud_resource_id: null,
    business_impact_notes: input.business_impact_notes,
    operational_dependency_rating: input.operational_dependency_rating,
    decommission: null,
    transitions: [
      { id: `${id}-t0`, actor: CURRENT_MEMBER.name, field_changed: "created", old_value: null, new_value: input.name.trim(), note: null, occurred_at: now },
    ],
    links: [],
    relationships: [],
    linked_summary: { control: 0, evidence: 0, risk: 0, document: 0, vendor: 0, vulnerability: 0 },
    watchers: [],
    allowed_transitions: LIFECYCLE_TRANSITIONS.planned,
  };
  created.hygiene = computeHygiene(created);
  STORE.unshift(created);
  return created;
}

export async function updateAsset(id: string, input: AssetInput): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === id);
  if (!a) throw new Error("asset not found");
  const before = effectiveTier(a.criticality);
  Object.assign(a, {
    name: input.name.trim(),
    asset_type: input.asset_type,
    description: input.description.trim(),
    hostname: input.hostname,
    ip_address: input.ip_address,
    environment: input.environment,
    location: input.location,
    vendor_ref: input.vendor_ref,
    data_classification: input.data_classification,
    regulated_data_type: input.regulated_data_type,
    compliance_scope: input.compliance_scope,
    internet_facing: input.internet_facing,
    customer_facing: input.customer_facing,
    network_segment: input.network_segment,
    business_function: input.business_function,
    criticality: criticalityFrom({ ...input }),
    ownership: ownershipFrom(input),
    valuation: input.valuation,
    business_impact_notes: input.business_impact_notes,
    operational_dependency_rating: input.operational_dependency_rating,
    last_reviewed_at: new Date().toISOString(),
  });
  const after = effectiveTier(a.criticality);
  if (before !== after) record(a, "criticality", before ?? "—", after ?? "—", null);
  a.hygiene = computeHygiene(a);
  return a;
}

function record(a: AssetDetail, field: string, oldV: string | null, newV: string | null, note: string | null): void {
  const now = new Date().toISOString();
  a.transitions.unshift({
    id: `${a.id}-t${a.transitions.length}`,
    actor: CURRENT_MEMBER.name,
    field_changed: field,
    old_value: oldV,
    new_value: newV,
    note,
    occurred_at: now,
  });
  a.updated_at = now;
}

export async function transitionAsset(id: string, to: AssetStatus, note?: string): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === id);
  if (!a) throw new Error("asset not found");
  if (!LIFECYCLE_TRANSITIONS[a.status].includes(to)) {
    throw new Error(`illegal transition ${a.status} → ${to}`);
  }
  record(a, "status", a.status, to, note ?? null);
  a.status = to;
  a.allowed_transitions = LIFECYCLE_TRANSITIONS[to];
  return a;
}

// -- relationships & review (A8) ---------------------------------------------

let relCounter = 0;

export type RelationshipInput = {
  type: RelationshipType;
  direction: "outbound" | "inbound";
  other_asset_id: string;
};

/** Declaring an edge writes it on both assets (the inverse on the other side), so
 *  the dependency graph reads correctly from either end. */
export async function addRelationship(assetId: string, input: RelationshipInput): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === assetId);
  if (!a) throw new Error("asset not found");
  const other = STORE.find((x) => x.id === input.other_asset_id);
  relCounter += 1;
  const id = `rel-${relCounter}`;
  a.relationships.unshift({
    id,
    direction: input.direction,
    type: input.type,
    other_asset_id: input.other_asset_id,
    other_asset_name: other?.name ?? "Unknown",
    provenance: "declared",
  });
  a.relationship_count = a.relationships.length;
  if (other) {
    other.relationships.unshift({
      id: `${id}-inv`,
      direction: input.direction === "outbound" ? "inbound" : "outbound",
      type: input.type,
      other_asset_id: a.id,
      other_asset_name: a.name,
      provenance: "declared",
    });
    other.relationship_count = other.relationships.length;
  }
  record(a, "relationship", null, `${input.direction === "outbound" ? "" : "is "}${input.type.replace(/_/g, " ")} ${other?.name ?? ""}`, null);
  return a;
}

export async function deleteRelationship(assetId: string, relId: string): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === assetId);
  if (!a) throw new Error("asset not found");
  a.relationships = a.relationships.filter((r) => r.id !== relId);
  a.relationship_count = a.relationships.length;
  // drop the inverse from the other side too
  for (const other of STORE) {
    const before = other.relationships.length;
    other.relationships = other.relationships.filter((r) => r.id !== `${relId}-inv`);
    if (other.relationships.length !== before) other.relationship_count = other.relationships.length;
  }
  return a;
}

/** Inventory attestation: the owner signs off that the record was reviewed, which
 *  clears the stale flag and lands on the activity trail (ISO 27001 A.5.9). */
export async function recordReview(assetId: string): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === assetId);
  if (!a) throw new Error("asset not found");
  a.last_reviewed_at = new Date().toISOString();
  record(a, "reviewed", null, "inventory reviewed", null);
  a.hygiene = computeHygiene(a);
  return a;
}

// -- CSV import --------------------------------------------------------------

/** The downloadable template columns, in order. `name` + `asset_type` are the
 *  only hard-required fields; `criticality` doubles as the audited override
 *  (blank = auto-calc). Matches the reference template. */
export const ASSET_TEMPLATE_COLUMNS = [
  "name",
  "description",
  "asset_type",
  "host_name",
  "ip_address",
  "vendor",
  "location",
  "operating_system",
  "confidentiality_rating",
  "integrity_rating",
  "availability_rating",
  "data_classification",
  "internet_facing",
  "business_function",
  "network_segment",
  "compliance_scope",
  "owner_name",
  "owning_team",
  "valuation",
  "criticality",
  "criticality_override_reason",
] as const;

/** A two-row CSV: the header, then one worked example, so a person editing it in
 *  a spreadsheet sees exactly what each column expects. */
export function assetImportTemplateCsv(): string {
  const example = [
    "Customer billing platform",
    "Customer-facing billing service",
    "business_service",
    "",
    "",
    "",
    "",
    "",
    "5",
    "5",
    "4",
    "restricted",
    "true",
    "Payment processing",
    "",
    "SOC2;PCI",
    "Omar Reyes",
    "Payments Engineering",
    "4200000",
    "",
    "",
  ];
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  return `${ASSET_TEMPLATE_COLUMNS.join(",")}\n${example.map(esc).join(",")}\n`;
}

export async function importAssets(inputs: AssetInput[]): Promise<{ created: number }> {
  await wait(220);
  for (const input of inputs) await bulkCreate(input);
  return { created: inputs.length };
}

/** Like createAsset but without the per-row latency, for the import batch. */
async function bulkCreate(input: AssetInput): Promise<void> {
  const now = new Date().toISOString();
  const id = nextId();
  const criticality = criticalityFrom({ ...input });
  const created: AssetDetail = {
    id,
    name: input.name.trim(),
    asset_type: input.asset_type,
    description: input.description.trim(),
    hostname: input.hostname,
    ip_address: input.ip_address,
    fqdn: null,
    os_normalized: null,
    environment: input.environment,
    location: input.location,
    vendor_ref: input.vendor_ref,
    data_classification: input.data_classification,
    regulated_data_type: input.regulated_data_type,
    compliance_scope: input.compliance_scope,
    internet_facing: input.internet_facing,
    customer_facing: input.customer_facing,
    network_segment: input.network_segment,
    business_function: input.business_function,
    criticality,
    ownership: ownershipFrom(input),
    status: "active",
    replaced_by_asset_id: null,
    valuation: input.valuation,
    first_seen_at: now,
    last_seen_at: now,
    last_reviewed_at: now,
    created_at: now,
    updated_at: now,
    source: "import",
    hygiene: { score: 0, missing: [], is_stale: false },
    vuln_count: 0,
    link_count: 0,
    relationship_count: 0,
    serial_number: null,
    primary_mac: null,
    cloud_resource_id: null,
    business_impact_notes: input.business_impact_notes,
    operational_dependency_rating: input.operational_dependency_rating,
    decommission: null,
    transitions: [
      { id: `${id}-t0`, actor: CURRENT_MEMBER.name, field_changed: "created", old_value: null, new_value: input.name.trim(), note: "imported", occurred_at: now },
    ],
    links: [],
    relationships: [],
    linked_summary: { control: 0, evidence: 0, risk: 0, document: 0, vendor: 0, vulnerability: 0 },
    watchers: [],
    allowed_transitions: LIFECYCLE_TRANSITIONS.active,
  };
  created.hygiene = computeHygiene(created);
  STORE.unshift(created);
}

/** Decommission is a guarded transition: it records the disposal and (on the real
 *  backend) cascades to close the asset's open vulns. */
export async function decommissionAsset(
  id: string,
  detail: Omit<DecommissionRecord, "decommissioned_by" | "decommissioned_at">,
): Promise<AssetDetail> {
  await wait();
  const a = STORE.find((x) => x.id === id);
  if (!a) throw new Error("asset not found");
  const now = new Date().toISOString();
  a.decommission = { ...detail, decommissioned_by: CURRENT_MEMBER.name, decommissioned_at: now };
  a.replaced_by_asset_id = detail.replacement_asset_id;
  record(a, "status", a.status, "decommissioned", detail.reason);
  a.status = "decommissioned";
  a.allowed_transitions = LIFECYCLE_TRANSITIONS.decommissioned;
  return a;
}
