/**
 * Presentation tokens for the Asset module — the single source of truth for how
 * a type, criticality tier, lifecycle status or classification looks, so the
 * register, detail and dashboard all render the same word the same way.
 *
 * The "no phantom defaults" rule lives here too: an unassessed tier or CIA
 * renders NEEDS_ASSESSMENT ("— assess"), never an invented value.
 */

import type { IconName } from "@/components/ui/icon";
import type { StatusFamily } from "@/components/ui";
import type {
  AssetStatus,
  AssetType,
  Criticality,
  CriticalityTier,
  DataClassification,
  Environment,
} from "./types";

/** The tier actually shown/inherited: a human override wins, else the computed
 *  tier, else null (not assessed). The one place the UI reads criticality from. */
export function displayTier(c: Criticality): CriticalityTier | null {
  return c.tier_override ?? c.tier;
}

export const ASSET_TYPE_META: Record<AssetType, { label: string; icon: IconName }> = {
  application: { label: "Application", icon: "appWindow" },
  infrastructure: { label: "Infrastructure", icon: "server" },
  data: { label: "Data store", icon: "database" },
  cloud: { label: "Cloud resource", icon: "cloud" },
  third_party: { label: "Third party", icon: "briefcase" },
  business_service: { label: "Business service", icon: "layers" },
};

/** Criticality reads as a heat scale, hottest first. */
export const TIER_META: Record<CriticalityTier, { label: string; family: StatusFamily }> = {
  critical: { label: "Critical", family: "danger" },
  high: { label: "High", family: "warning" },
  medium: { label: "Medium", family: "pending" },
  low: { label: "Low", family: "neutral" },
};

/** Shown wherever a tier or CIA rating has not been set — never a default. */
export const NEEDS_ASSESSMENT = { label: "Not rated", family: "neutral" as StatusFamily };

export const STATUS_META: Record<AssetStatus, { label: string; family: StatusFamily }> = {
  planned: { label: "Planned", family: "pending" },
  active: { label: "Active", family: "success" },
  in_maintenance: { label: "In maintenance", family: "warning" },
  decommissioned: { label: "Decommissioned", family: "neutral" },
  retired: { label: "Retired", family: "neutral" },
};

export const CLASSIFICATION_META: Record<
  DataClassification,
  { label: string; family: StatusFamily }
> = {
  public: { label: "Public", family: "neutral" },
  internal: { label: "Internal", family: "neutral" },
  confidential: { label: "Confidential", family: "warning" },
  restricted: { label: "Restricted", family: "danger" },
};

export const ENVIRONMENT_LABEL: Record<Environment, string> = {
  prod: "Production",
  staging: "Staging",
  dev: "Development",
  test: "Test",
  dr: "DR",
};

// -- formatters --------------------------------------------------------------

export function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}

/** "in 6h", "3d ago", "—". Signed, for freshness/last-seen proximity. */
export function relativeTime(value: string | null): string {
  if (!value) return "—";
  const delta = new Date(value).getTime() - Date.now();
  const ahead = delta >= 0;
  const hours = Math.round(Math.abs(delta) / 3_600_000);
  if (hours < 1) return "now";
  const label = hours < 24 ? `${hours}h` : `${Math.round(hours / 24)}d`;
  return ahead ? `in ${label}` : `${label} ago`;
}

/** Valuation, compact — "$1.2M", "$40k", or "—" when there is no real figure
 *  (no phantom zero). */
export function fmtMoney(value: number | null): string {
  if (value == null) return "—";
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${Math.round(value / 1_000)}k`;
  return `$${value}`;
}
