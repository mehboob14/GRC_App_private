/**
 * Asset management — typed contracts for the UI/UX build (Phase A).
 *
 * Built against an in-memory mock (mock.ts, read through api.ts) so the module
 * is clickable before the backend exists; these shapes are the contract the real
 * API fills at Phase C, so mock -> real stays a one-file change in api.ts — the
 * same path documents and tasks took.
 *
 * Decisions encoded here (see docs/product/assets-module-plan.md):
 *   No phantom defaults — criticality, CIA and score are nullable; NULL means
 *     "not assessed" and renders "— / assess", never a laundered "medium".
 *   Criticality is the reference's ISO 27005 scorer: CIA 1-5, base = MAX (highest
 *     harm wins), + exposure/classification boosts; tier_override kept separately.
 *   Correlation keys (fqdn, mac, serial, cloud id, os_normalized) ride the record
 *     now so Phase-2 connector dedup needs no schema change.
 *   360 linkage is the polymorphic `links` primitive, not a table per pair.
 */

// -- enumerations ------------------------------------------------------------

export const ASSET_TYPES = [
  "application",
  "infrastructure",
  "data",
  "cloud",
  "third_party",
  "business_service",
] as const;
export type AssetType = (typeof ASSET_TYPES)[number];

/** Enforced lifecycle. `decommissioned` cascades to close linked vulns and
 *  records a disposal record; `retired` is terminal. */
export const ASSET_STATUSES = [
  "planned",
  "active",
  "in_maintenance",
  "decommissioned",
  "retired",
] as const;
export type AssetStatus = (typeof ASSET_STATUSES)[number];

export const DATA_CLASSIFICATIONS = ["public", "internal", "confidential", "restricted"] as const;
export type DataClassification = (typeof DATA_CLASSIFICATIONS)[number];

/** Derived from `criticality_score`; null until CIA is assessed (no default). */
export const CRITICALITY_TIERS = ["critical", "high", "medium", "low"] as const;
export type CriticalityTier = (typeof CRITICALITY_TIERS)[number];

/** CIA is rated 1-5; null = not rated. */
export type CiaRating = 1 | 2 | 3 | 4 | 5;

export const ENVIRONMENTS = ["prod", "staging", "dev", "test", "dr"] as const;
export type Environment = (typeof ENVIRONMENTS)[number];

/** Which hygiene checks a record fails. */
export const HYGIENE_FLAGS = [
  "no_owner",
  "no_type",
  "no_criticality",
  "no_classification",
  "no_cia",
] as const;
export type HygieneFlag = (typeof HYGIENE_FLAGS)[number];

/** Manually-declared dependency edges (A8); provenance distinguishes people
 *  from Phase-2 connector discovery. */
export const RELATIONSHIP_TYPES = [
  "depends_on",
  "runs_on",
  "contains",
  "connects_to",
  "processes_data_for",
] as const;
export type RelationshipType = (typeof RELATIONSHIP_TYPES)[number];

/** The objects an asset links to through the polymorphic `links` table. */
export const LINK_TARGETS = [
  "control",
  "evidence",
  "risk",
  "document",
  "vendor",
  "vulnerability",
] as const;
export type LinkTarget = (typeof LINK_TARGETS)[number];

/** Where a record came from (rule 9). */
export type AssetSource = LinkTarget | "manual" | "import";

// -- people ------------------------------------------------------------------

/** Always a tenant membership, never a global user (rule 3). */
export type Member = {
  membership_id: string;
  name: string;
};

// -- value objects -----------------------------------------------------------

/** Nested on the asset. `score`/`tier` null = not assessed; `tier_override` wins
 *  for display when set, but the computed values are always kept alongside. */
export type Criticality = {
  confidentiality: CiaRating | null;
  integrity: CiaRating | null;
  availability: CiaRating | null;
  score: number | null; // 0-10, computed
  tier: CriticalityTier | null; // derived from score
  tier_override: CriticalityTier | null;
  tier_override_reason: string | null;
};

/** The full ownership chain — every person a membership (rule 3); the owning
 *  team is a group, carried as its name for display. */
export type Ownership = {
  primary_owner: Member | null;
  secondary_owner: Member | null;
  business_owner: Member | null;
  custodian: Member | null;
  escalation_contact: Member | null;
  owning_team: string | null;
};

/** Computed, never stored: which checks fail and whether the record is stale. */
export type Hygiene = {
  /** 0-100, the share of the five checks that pass. */
  score: number;
  missing: HygieneFlag[];
  is_stale: boolean;
};

// -- the asset ---------------------------------------------------------------

/** The register row: everything a list cell needs. Detail extends this. */
export type Asset = {
  id: string;
  name: string;
  asset_type: AssetType;
  description: string;

  // identity + correlation keys (populated by connectors in Phase 2)
  hostname: string | null;
  ip_address: string | null;
  fqdn: string | null;
  os_normalized: string | null;
  environment: Environment | null;
  location: string | null;
  vendor_ref: string | null; // free text until the vendors module lands

  // classification & exposure
  data_classification: DataClassification | null;
  regulated_data_type: string | null;
  compliance_scope: string[];
  internet_facing: boolean;
  customer_facing: boolean;
  network_segment: string | null;
  business_function: string | null;

  criticality: Criticality;
  ownership: Ownership;

  // lifecycle
  status: AssetStatus;
  replaced_by_asset_id: string | null;

  // business context shown on the row
  valuation: number | null;

  // freshness
  first_seen_at: string | null;
  last_seen_at: string | null;
  last_reviewed_at: string | null;

  created_at: string;
  updated_at: string;
  source: AssetSource;

  // derived / badges (so a row needs no extra fetch)
  hygiene: Hygiene;
  vuln_count: number;
  link_count: number;
  relationship_count: number;
};

/** One immutable lifecycle-history row — columnar, so "who changed criticality"
 *  is a filter, not a JSON parse. Separate from the platform audit log. */
export type AssetTransition = {
  id: string;
  actor: string;
  field_changed: string; // "status", "criticality", "owner", "created", …
  old_value: string | null;
  new_value: string | null;
  note: string | null;
  occurred_at: string;
};

export type AssetLink = {
  id: string;
  to_type: LinkTarget;
  to_id: string;
  to_label: string; // e.g. "CC6.1 · Logical access controls"
  relation: string; // "relates_to", "remediates", "processes_data_for"
  note: string | null;
};

/** A directed dependency edge relative to the current asset (A8). */
export type AssetRelationship = {
  id: string;
  direction: "outbound" | "inbound";
  type: RelationshipType;
  other_asset_id: string;
  other_asset_name: string;
  provenance: "declared" | "discovered";
};

/** Written when an asset is decommissioned — auditors test retirement followed
 *  policy, so disposal method and sanitisation are recorded. */
export type DecommissionRecord = {
  disposal_method: string;
  media_sanitised: boolean;
  replacement_asset_id: string | null;
  evidence_ref: string | null;
  reason: string;
  decommissioned_by: string;
  decommissioned_at: string;
};

/** The extra detail one asset carries beyond the register row. */
export type AssetDetail = Asset & {
  // remaining identity / correlation
  serial_number: string | null;
  primary_mac: string | null;
  cloud_resource_id: string | null;

  // business context
  business_impact_notes: string | null;
  operational_dependency_rating: string | null;

  decommission: DecommissionRecord | null;

  transitions: AssetTransition[];
  links: AssetLink[];
  relationships: AssetRelationship[];
  /** Counts per link target for the "Linked" tab headers. */
  linked_summary: Record<LinkTarget, number>;
  watchers: Member[];

  /** Served by the API — the lifecycle moves allowed from the current state. */
  allowed_transitions: AssetStatus[];
};

// -- filtering & views -------------------------------------------------------

export type AssetFilters = {
  search: string;
  asset_type: AssetType | "all";
  tiers: CriticalityTier[];
  statuses: AssetStatus[];
  environments: Environment[];
  classifications: DataClassification[];
  /** Exposure facet — internet- or customer-facing, or either. */
  exposure: "internet_facing" | "customer_facing" | null;
  owner: string | null; // membership_id, "me", or "unassigned"
  /** Hygiene issues or stale — the "needs attention" facet. */
  needs_attention: boolean;
};

export type SavedView = {
  id: string;
  name: string;
  filters: Partial<AssetFilters>;
  is_shared: boolean;
  position: number;
};

// -- dashboard ---------------------------------------------------------------

export type AssetSummary = {
  total: number;
  /** Tier distribution, plus the count of records with no tier yet. */
  by_tier: Record<CriticalityTier, number> & { unassessed: number };
  by_type: { type: AssetType; count: number }[];
  by_status: Record<AssetStatus, number>;
  needs_cia: number;
  regulated: number;
  stale: number;
  /** Mean hygiene across the estate, 0-100. */
  hygiene_avg: number;
};

// -- list envelope -----------------------------------------------------------

export type AssetPage = {
  items: Asset[];
  total: number;
};
