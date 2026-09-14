import type { IconName, StatusFamily } from "@/components/ui";
import type { Attention, Band, BandKey, RegisterType, RiskStatus, Treatment } from "./types";

export const STATUS_META: Record<RiskStatus, { label: string; family: StatusFamily }> = {
  open: { label: "Open", family: "danger" },
  in_treatment: { label: "In treatment", family: "progress" },
  mitigated: { label: "Mitigated", family: "success" },
  accepted: { label: "Accepted", family: "warning" },
  closed: { label: "Closed", family: "neutral" },
};

export const TREATMENT_META: Record<Treatment, { label: string; icon: IconName; hint: string }> = {
  mitigate: { label: "Mitigate", icon: "shield", hint: "Reduce with controls" },
  accept: { label: "Accept", icon: "check", hint: "Formally approved" },
  avoid: { label: "Avoid", icon: "x", hint: "Stop the activity" },
  transfer: { label: "Transfer", icon: "export", hint: "Insure or outsource" },
};

export const REGISTER_TYPE_LABEL: Record<RegisterType, string> = {
  enterprise: "Enterprise",
  rcsa: "RCSA",
  iso_27001: "ISO 27001",
  soc_2: "SOC 2",
  pci_dss: "PCI DSS",
  sox: "SOX",
  gdpr: "GDPR",
  nist_csf: "NIST CSF",
  sama_csf: "SAMA CSF",
  internal: "Internal",
  project: "Project",
  third_party: "Third party",
  other: "Other",
};

export const ATTENTION_META: Record<Attention, { label: string; icon: IconName; family: StatusFamily }> = {
  no_controls: { label: "No linked control", icon: "controls", family: "danger" },
  review_overdue: { label: "Review overdue", icon: "clock", family: "danger" },
  treatment_overdue: { label: "Treatment overdue", icon: "alert", family: "warning" },
  unscored: { label: "Not scored", icon: "gauge", family: "warning" },
  unowned: { label: "No owner", icon: "user", family: "warning" },
  acceptance_pending: { label: "Awaiting approval", icon: "flag", family: "progress" },
  acceptance_expiring: { label: "Acceptance expiring", icon: "calendar", family: "warning" },
};

export const ORIGIN_LABEL: Record<string, string> = {
  manual: "Added by hand",
  library: "Starter library",
  import: "Imported",
  vendor_finding: "Vendor finding",
  assessment: "Assessment",
};

/** Solid fill for populated cells and chips; a pale tint of the same hue marks the zone. */
export const BAND_TONE: Record<BandKey, { solid: string; tint: string; text: string; dot: string; stroke: string }> = {
  low: {
    solid: "bg-severity-low text-white",
    tint: "bg-severity-low/15",
    text: "text-severity-low",
    dot: "bg-severity-low",
    stroke: "stroke-severity-low",
  },
  medium: {
    solid: "bg-severity-medium text-white",
    tint: "bg-severity-medium/15",
    text: "text-severity-medium",
    dot: "bg-severity-medium",
    stroke: "stroke-severity-medium",
  },
  high: {
    solid: "bg-severity-high text-white",
    tint: "bg-severity-high/15",
    text: "text-severity-high",
    dot: "bg-severity-high",
    stroke: "stroke-severity-high",
  },
  critical: {
    solid: "bg-severity-critical text-white",
    tint: "bg-severity-critical/15",
    text: "text-severity-critical",
    dot: "bg-severity-critical",
    stroke: "stroke-severity-critical",
  },
};

export function bandFor(bands: Band[], score: number | null | undefined): Band | null {
  if (score === null || score === undefined) return null;
  let hit: Band | null = null;
  for (const band of bands) if (band.min_score <= score) hit = band;
  return hit;
}

export function bandLabel(bands: Band[], key: BandKey | null): string {
  return bands.find((b) => b.key === key)?.label ?? "Not scored";
}

/** The event line a person reads in the history tab. */
export const EVENT_LABEL: Record<string, string> = {
  created: "Created",
  updated: "Edited",
  scored: "Rescored",
  status: "Status changed",
  treatment: "Treatment decided",
  owner: "Owner changed",
  control_linked: "Control linked",
  control_unlinked: "Control unlinked",
  linked: "Record linked",
  unlinked: "Record unlinked",
  action_added: "Action added",
  acceptance_requested: "Acceptance requested",
  acceptance_approved: "Acceptance approved",
  acceptance_rejected: "Acceptance rejected",
  acceptance_withdrawn: "Acceptance withdrawn",
  acceptance_revoked: "Acceptance revoked",
  acceptance_expired: "Acceptance expired",
  reviewed: "Reviewed",
  imported: "Imported",
  adopted: "Added from library",
  promoted: "Promoted from vendor finding",
};

export const EVENT_ICON: Record<string, IconName> = {
  created: "plus",
  updated: "edit",
  scored: "gauge",
  status: "activity",
  treatment: "shield",
  owner: "user",
  control_linked: "controls",
  control_unlinked: "controls",
  linked: "link",
  unlinked: "link",
  action_added: "checklist",
  acceptance_requested: "flag",
  acceptance_approved: "check",
  acceptance_rejected: "x",
  acceptance_withdrawn: "arrowl",
  acceptance_revoked: "x",
  acceptance_expired: "clock",
  reviewed: "eye",
  imported: "upload",
  adopted: "book",
  promoted: "vendor",
};

export function humanise(value: string | null | undefined): string {
  if (!value) return "";
  return STATUS_META[value as RiskStatus]?.label ?? value.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

export function fmtDate(value: string | null | undefined): string {
  if (!value) return "Not set";
  const d = new Date(value.length === 10 ? `${value}T00:00:00` : value);
  if (Number.isNaN(d.getTime())) return "Not set";
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

export function daysUntil(value: string | null | undefined): number | null {
  if (!value) return null;
  const target = new Date(`${value.slice(0, 10)}T00:00:00`);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return Math.round((target.getTime() - today.getTime()) / 86_400_000);
}

export function isoDate(offsetDays: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** Link record types, in the order the Links tab lists them. */
export const LINK_META: Record<string, { label: string; plural: string; icon: IconName; href: (id: string) => string }> = {
  asset: { label: "Asset", plural: "Assets", icon: "server", href: (id) => `/assets/${id}` },
  vulnerability: { label: "Vulnerability", plural: "Vulnerabilities", icon: "bug", href: (id) => `/vulnerabilities/${id}` },
  evidence: { label: "Evidence", plural: "Evidence", icon: "doc", href: (id) => `/evidence/${id}` },
  task: { label: "Task or issue", plural: "Tasks and issues", icon: "checklist", href: (id) => `/tasks/${id}` },
  vendor: { label: "Vendor", plural: "Vendors", icon: "vendor", href: (id) => `/vendors/${id}` },
  document: { label: "Document", plural: "Policies and documents", icon: "book", href: (id) => `/documents/${id}` },
};
