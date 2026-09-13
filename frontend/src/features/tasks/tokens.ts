/**
 * Presentation tokens for the Task & Issue module — the single source of truth
 * for how a status, priority, severity or SLA state looks.
 *
 * These live here, not inside a component, so the register, board, detail and
 * (Phase C) the cross-module embed kit all render the same word the same way.
 * The reference implementation forked its colour maps between screens because
 * they lived under one screen's folder; this avoids that from day one.
 */

import type { StatusFamily } from "@/components/ui";
import type { CapaStatus, CapaType, Priority, Severity, SlaState, TaskStatus } from "./types";

export const STATUS_META: Record<TaskStatus, { label: string; family: StatusFamily }> = {
  open: { label: "Open", family: "neutral" },
  in_progress: { label: "In progress", family: "progress" },
  blocked: { label: "Blocked", family: "warning" },
  under_review: { label: "Under review", family: "pending" },
  closed: { label: "Closed", family: "success" },
  cancelled: { label: "Cancelled", family: "neutral" },
};

/** Priority is not a lifecycle, so it renders as a labelled dot rather than a
 *  pill — kept visually distinct from status on purpose. */
export const PRIORITY_META: Record<Priority, { label: string; dot: string; text: string }> = {
  critical: { label: "Critical", dot: "bg-status-danger-base", text: "text-status-danger-text" },
  high: { label: "High", dot: "bg-status-warning-base", text: "text-status-warning-text" },
  medium: { label: "Medium", dot: "bg-action-accent", text: "text-text-secondary" },
  low: { label: "Low", dot: "bg-status-neutral-base", text: "text-text-subtle" },
};

export const SLA_META: Record<SlaState, { label: string; family: StatusFamily }> = {
  breached: { label: "Breached", family: "danger" },
  due_soon: { label: "Due soon", family: "warning" },
  paused: { label: "Paused", family: "neutral" },
  on_track: { label: "On track", family: "success" },
  none: { label: "No SLA", family: "neutral" },
};

/** SeverityChip in the UI kit knows critical/high/medium/low; `informational`
 *  folds to low for colour while keeping its own label. */
export const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  informational: "Info",
};

/** CAPA action lifecycle. `completed` is "done, awaiting verification" (pending);
 *  `verified` is the terminal success. */
export const CAPA_STATUS_META: Record<CapaStatus, { label: string; family: StatusFamily }> = {
  planned: { label: "Planned", family: "neutral" },
  in_progress: { label: "In progress", family: "progress" },
  blocked: { label: "Blocked", family: "warning" },
  completed: { label: "Completed", family: "pending" },
  verified: { label: "Verified", family: "success" },
  cancelled: { label: "Cancelled", family: "neutral" },
};

export const CAPA_TYPE_LABEL: Record<CapaType, string> = {
  corrective: "Corrective",
  preventive: "Preventive",
  containment: "Containment",
  verification: "Verification",
};

// -- formatters --------------------------------------------------------------

export function fmtDate(value: string | null): string {
  if (!value) return "No date";
  return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "2-digit" });
}

/** "in 6h", "3d ago", "No date". Signed, for SLA/due proximity. */
export function relativeTime(value: string | null): string {
  if (!value) return "No date";
  const delta = new Date(value).getTime() - Date.now();
  const ahead = delta >= 0;
  const abs = Math.abs(delta);
  const h = Math.round(abs / 3_600_000);
  const label = h < 24 ? `${h}h` : `${Math.round(h / 24)}d`;
  if (h < 1) return "now";
  return ahead ? `in ${label}` : `${label} ago`;
}
