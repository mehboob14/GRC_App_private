import type { EvidenceFreshness, ReviewStatus } from "@/lib/api/types";

/** Presentation constants for the evidence module. Lifted out of the pages so
 *  the register, the detail page and the viewer all label a state the same way. */

export const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
};

export const REVIEW_META: Record<
  ReviewStatus,
  { label: string; family: "success" | "danger" | "pending" }
> = {
  pending: { label: "Pending review", family: "pending" },
  approved: { label: "Approved", family: "success" },
  rejected: { label: "Rejected", family: "danger" },
};

/** A date-only ISO string (YYYY-MM-DD) in the reader's locale. */
export function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
      new Date(`${iso.slice(0, 10)}T00:00:00`),
    );
  } catch {
    return iso;
  }
}

/** A full timestamp, for the audit trail and review decisions where the time
 *  of day is part of the record. */
export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
