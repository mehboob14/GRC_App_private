/**
 * Data layer for the Asset module — wired to the real backend.
 *
 * Criticality scoring stays client-side (`previewCriticality`) so the form can
 * show a live tier before anything is saved; those pure helpers still live in
 * mock.ts next to the (no longer used) seed data.
 */

import { ApiError, apiFetch } from "@/lib/api/client";
import { computeCriticality, effectiveTier, isHighImpact } from "./mock";
import type {
  Asset,
  AssetDetail,
  AssetFilters,
  AssetPage,
  AssetStatus,
  AssetSummary,
  AssetType,
  CiaRating,
  CriticalityTier,
  DataClassification,
  DecommissionRecord,
  Environment,
  LinkTarget,
  Member,
  RelationshipType,
} from "./types";

/** The backend does not model asset links or relationships yet, so a detail
 *  response is completed with empty collections rather than leaving those tabs
 *  reading `undefined.length`. */
const NO_LINKS: Record<LinkTarget, number> = {
  control: 0,
  evidence: 0,
  risk: 0,
  document: 0,
  vendor: 0,
  vulnerability: 0,
};

type AssetDetailResponse = Omit<AssetDetail, "links" | "relationships" | "linked_summary">;

function withEmptyLinks(a: AssetDetailResponse): AssetDetail {
  return { ...a, links: [], relationships: [], linked_summary: NO_LINKS };
}

// -- reads -------------------------------------------------------------------

export async function listAssets(
  filters: Partial<AssetFilters>,
  page = 1,
  pageSize = 25,
): Promise<AssetPage> {
  const q = new URLSearchParams();
  if (filters.search) q.set("search", filters.search);
  if (filters.asset_type && filters.asset_type !== "all") q.set("asset_type", filters.asset_type);
  // Array facets go over the wire as repeated keys (?tiers=critical&tiers=high).
  for (const t of filters.tiers ?? []) q.append("tiers", t);
  for (const s of filters.statuses ?? []) q.append("statuses", s);
  for (const e of filters.environments ?? []) q.append("environments", e);
  for (const c of filters.classifications ?? []) q.append("classifications", c);
  if (filters.exposure) q.set("exposure", filters.exposure);
  if (filters.owner) q.set("owner", filters.owner);
  q.set("page", String(page));
  q.set("page_size", String(pageSize));
  return apiFetch<AssetPage>(`/assets?${q.toString()}`);
}

export async function getAsset(id: string): Promise<AssetDetail | null> {
  try {
    return withEmptyLinks(await apiFetch<AssetDetailResponse>(`/assets/${id}`));
  } catch (e) {
    // A missing asset is an empty state, not an error the page should throw on.
    if (e instanceof ApiError && e.status === 404) return null;
    throw e;
  }
}

/** Facet counts for the register filter bar, over the whole (unfiltered) estate. */
export async function getFacets(): Promise<{
  asset_type: Record<AssetType, number>;
  tier: Record<CriticalityTier | "unassessed", number>;
  status: Record<AssetStatus, number>;
  environment: Record<Environment, number>;
  needs_attention: number;
}> {
  return apiFetch("/assets/facets");
}

export async function getSummary(): Promise<AssetSummary> {
  return apiFetch<AssetSummary>("/assets/summary");
}

/** Tenant members for the owner pickers. Served by IAM rather than the assets
 *  module, so this needs `members:read` — an assets-only role sees it empty. */
type RawMember = { membership_id: string; full_name: string };
export async function listMembers(): Promise<Member[]> {
  const rows = await apiFetch<RawMember[]>("/members");
  return rows.map((m) => ({ membership_id: m.membership_id, name: m.full_name }));
}


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

/** The API names the owner fields `*_membership_id` and rejects unknown keys
 *  (`extra="forbid"`), so the form's `*_id` shape is translated here.
 *
 *  `owning_team` is deliberately not sent: the API takes an `owning_team_group_id`
 *  (a group UUID) and the form collects a free-text team name, so there is
 *  nothing honest to map it to until the form picks a real group. */
function writeBody(input: AssetInput) {
  const {
    primary_owner_id,
    secondary_owner_id,
    business_owner_id,
    custodian_id,
    escalation_contact_id,
    owning_team,
    ...rest
  } = input;
  void owning_team;
  return {
    ...rest,
    primary_owner_membership_id: primary_owner_id,
    secondary_owner_membership_id: secondary_owner_id,
    business_owner_membership_id: business_owner_id,
    custodian_membership_id: custodian_id,
    escalation_contact_membership_id: escalation_contact_id,
  };
}

export async function createAsset(input: AssetInput): Promise<AssetDetail> {
  return withEmptyLinks(
    await apiFetch<AssetDetailResponse>("/assets", {
      method: "POST",
      body: JSON.stringify(writeBody(input)),
    }),
  );
}

/** PATCH on the wire, a full replace in behaviour — the API assigns every field,
 *  so an omitted optional is cleared. The form always sends the whole record. */
export async function updateAsset(id: string, input: AssetInput): Promise<AssetDetail> {
  return withEmptyLinks(
    await apiFetch<AssetDetailResponse>(`/assets/${id}`, {
      method: "PATCH",
      body: JSON.stringify(writeBody(input)),
    }),
  );
}

export async function transitionAsset(
  id: string,
  to: AssetStatus,
  note?: string,
): Promise<AssetDetail> {
  return withEmptyLinks(
    await apiFetch<AssetDetailResponse>(`/assets/${id}/transition`, {
      method: "POST",
      body: JSON.stringify({ to_status: to, note: note ?? null }),
    }),
  );
}

// -- relationships & review --------------------------------------------------

export type RelationshipInput = {
  type: RelationshipType;
  direction: "outbound" | "inbound";
  other_asset_id: string;
};

/** Asset-to-asset relationships have no backend yet — no table, no endpoint — so
 *  declaring one fails loudly rather than writing to a store nothing else can
 *  see. `AssetDetail.relationships` stays empty until that ships. */
export async function addRelationship(
  assetId: string,
  input: RelationshipInput,
): Promise<AssetDetail> {
  void assetId;
  void input;
  throw new Error("Asset relationships aren't available yet.");
}

export async function deleteRelationship(assetId: string, relId: string): Promise<AssetDetail> {
  void assetId;
  void relId;
  throw new Error("Asset relationships aren't available yet.");
}

/** Inventory attestation: the owner signs off that the record was reviewed, which
 *  clears the stale flag and lands on the activity trail (ISO 27001 A.5.9). */
export async function recordReview(assetId: string): Promise<AssetDetail> {
  return withEmptyLinks(
    await apiFetch<AssetDetailResponse>(`/assets/${assetId}/review`, { method: "POST" }),
  );
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

function csvEscape(v: string): string {
  return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

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
  return `${ASSET_TEMPLATE_COLUMNS.join(",")}\n${example.map(csvEscape).join(",")}\n`;
}

/** Trigger a browser download for a CSV string — the same blob+anchor idiom
 *  every export/template button in the app uses. */
export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob([content], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

const EXPORT_COLUMNS = [
  "name",
  "asset_type",
  "owner",
  "criticality",
  "confidentiality",
  "integrity",
  "availability",
  "lifecycle",
  "value_usd",
  "internet_facing",
] as const;

/** The rows currently on screen, as a CSV — there is no backend export for
 *  assets yet, so this exports exactly what the register is showing. */
export function assetsExportCsv(rows: Asset[]): string {
  const lines = rows.map((a) =>
    [
      a.name,
      a.asset_type,
      a.ownership.primary_owner?.name ?? "",
      effectiveTier(a.criticality) ?? "",
      a.criticality.confidentiality != null ? String(a.criticality.confidentiality) : "",
      a.criticality.integrity != null ? String(a.criticality.integrity) : "",
      a.criticality.availability != null ? String(a.criticality.availability) : "",
      a.status,
      a.valuation != null ? String(a.valuation) : "",
      a.internet_facing ? "true" : "false",
    ]
      .map(csvEscape)
      .join(","),
  );
  return `${EXPORT_COLUMNS.join(",")}\n${lines.join("\n")}\n`;
}

/** The first worksheet of an Excel file as text rows, header first. The import
 *  page reads CSV itself; Excel is opened by the server. */
export function readAssetSheet(file: File): Promise<{ rows: string[][] }> {
  const form = new FormData();
  form.append("file", file);
  return apiFetch<{ rows: string[][] }>("/assets/import/sheet", { method: "POST", body: form });
}

export async function importAssets(inputs: AssetInput[]): Promise<{ created: number }> {
  return apiFetch<{ created: number }>("/assets/import", {
    method: "POST",
    body: JSON.stringify({ rows: inputs.map(writeBody) }),
  });
}


/** Decommission is a guarded transition: it records the disposal and cascades
 *  to close the asset's open vulnerabilities. */
export async function decommissionAsset(
  id: string,
  detail: Omit<DecommissionRecord, "decommissioned_by" | "decommissioned_at">,
): Promise<AssetDetail> {
  return withEmptyLinks(
    await apiFetch<AssetDetailResponse>(`/assets/${id}/decommission`, {
      method: "POST",
      body: JSON.stringify(detail),
    }),
  );
}
