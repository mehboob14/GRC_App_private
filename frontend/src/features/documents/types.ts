/**
 * Documents & Policies — typed contracts for the UI/UX build.
 *
 * Stage 1-2 run against an in-memory mock (see mock.ts / api.ts) so the screens
 * can be validated before the backend exists. The shapes here are the contract
 * the real API will fill later, so swapping mock → real is a one-file change.
 */

export const DOC_TYPES = [
  "policy",
  "standard",
  "procedure",
  "guideline",
  "charter",
] as const;
export type DocType = (typeof DOC_TYPES)[number];

export const CLASSIFICATIONS = [
  "public",
  "internal",
  "confidential",
  "restricted",
] as const;
export type Classification = (typeof CLASSIFICATIONS)[number];

/** Lifecycle a document moves through. `draft → needs_approval → approved →
 *  published`, with `expired` (renewal lapsed) and `archived` off to the side. */
export const LIFECYCLES = [
  "draft",
  "needs_approval",
  "approved",
  "published",
  "expired",
  "archived",
] as const;
export type Lifecycle = (typeof LIFECYCLES)[number];

/** How the current version's content is held: authored rich text, or an
 *  uploaded file kept in object storage and shown in a viewer. */
export type ContentFormat = "html" | "pdf" | "docx";

export type DocumentOwner = {
  membership_id: string;
  name: string;
};

export type Document = {
  id: string;
  code: string; // POL-01 / STD-01 / PRC-01 / GDL-01 / CHT-01
  title: string;
  description: string;
  doc_type: DocType;
  classification: Classification;
  lifecycle: Lifecycle;
  version: string; // "1.0", "1.12"
  content_format: ContentFormat;
  filename: string | null; // for uploaded docs
  owner: DocumentOwner | null;
  frameworks: string[];
  controls: string[];
  /** Percent of assigned personnel who have acknowledged, or null if no campaign. */
  attestation_pct: number | null;
  assigned_to: string | null; // "All personnel", a group name, or null
  created_on: string | null;
  approved_on: string | null;
  published_on: string | null;
  renewal_date: string | null;
  updated_at: string | null;
};

export type ChangeType = "major" | "minor" | "patch";

export type DocumentVersion = {
  version: string;
  change_type: ChangeType;
  created_on: string;
  created_by: string;
  summary: string;
  status: "current" | "superseded";
};

export type ApprovalTier = {
  tier: number;
  name: string;
  status: "pending" | "approved" | "rejected" | "not_started";
  approver: string | null;
  decided_on: string | null;
};

/** The extra detail a single document carries beyond the register row. */
export type DocumentDetail = Document & {
  content_html: string | null;
  versions: DocumentVersion[];
  approvals: ApprovalTier[];
  acknowledged: number;
  assigned_count: number;
  acknowledged_by_me: boolean;
};

export type DocumentKpis = {
  renewal_soon: number;
  renewal_past_due: number;
  needs_approval: number;
  ready_to_publish: number;
};

