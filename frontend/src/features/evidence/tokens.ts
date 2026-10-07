import type { IconName } from "@/components/ui";
import type { Evidence, EvidenceFreshness, ReviewStatus } from "@/lib/api/types";

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
  if (!iso) return "No date";
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
  if (!iso) return "No date";
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
  if (bytes === null) return "Size unknown";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

/** What kind of artefact an evidence type is, as a word and a mark. A type the
 *  list does not know falls back to the plain document. */
const TYPE_ICON: Record<string, IconName> = {
  screenshot: "camera",
  configuration_export: "sliders",
  log_export: "list",
  policy_document: "book",
  training_record: "checklist",
  vendor_report: "vendor",
  ticket_record: "clipboard",
  meeting_minutes: "users",
};

export function typeIcon(evidenceType: string): IconName {
  return TYPE_ICON[evidenceType] ?? "doc";
}

/** "configuration_export" as "Configuration export". */
export function typeLabel(evidenceType: string): string {
  const words = evidenceType.replace(/_/g, " ");
  return words.charAt(0).toUpperCase() + words.slice(1);
}

const CONNECTOR_SUFFIX = " connector";
/** The title the first connector files carried, before they recorded a `source`. */
const LEGACY_TITLE = ": automated test results";

/** Automated evidence is titled with the moment it was collected (`, 6 Oct 2026 14:05 UTC`). */
const COLLECTED_AT = /,\s\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2} UTC$/;

/**
 * What a run of automated evidence is one history of, or null for an item a person added.
 *
 * Every day's result for one check is a new item with the same name and a different
 * moment. They share this key, so a list can show the latest and keep the rest behind it.
 */
export function historyKey(item: Evidence): string | null {
  if (automatedBy(item) === null) return null;
  return `${item.source_label ?? ""}|${item.title.replace(COLLECTED_AT, "")}`;
}

/**
 * The system that collected an item, or null when a person added it.
 *
 * What a connector files names its provider in `source`. The first files recorded
 * none and said so only in their label ("GitHub connector") and title together; a
 * label alone proves nothing, since anyone who manages evidence can type one.
 */
export function automatedBy(item: Evidence): string | null {
  if (item.source) return item.source === "github" ? "GitHub" : item.source;
  const label = item.source_label;
  return label?.endsWith(CONNECTOR_SUFFIX) && item.title.includes(LEGACY_TITLE)
    ? label.slice(0, -CONNECTOR_SUFFIX.length)
    : null;
}
