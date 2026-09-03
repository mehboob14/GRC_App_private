import type { BadgeVariant, StatusFamily } from "@/components/ui";
import type { InstanceState } from "./types";

/** Shared data tokens for the vulnerabilities feature (no JSX — see severity-badge.tsx). */

export const STATE_META: Record<InstanceState, { label: string; variant: BadgeVariant }> = {
  new: { label: "New", variant: "countWarn" },
  active: { label: "Active", variant: "countWarn" },
  in_progress: { label: "In progress", variant: "statusReview" },
  pending_retest: { label: "Pending retest", variant: "statusReview" },
  fixed: { label: "Fixed", variant: "statusPass" },
  resurfaced: { label: "Resurfaced", variant: "statusFail" },
  accepted: { label: "Accepted", variant: "role" },
  false_positive: { label: "False positive", variant: "neutral" },
};

/** Chart color family per state — the six StatusPill families, not a new palette. */
export const STATE_FAMILY: Record<InstanceState, StatusFamily> = {
  new: "warning",
  active: "warning",
  in_progress: "progress",
  pending_retest: "progress",
  fixed: "success",
  resurfaced: "danger",
  accepted: "pending",
  false_positive: "neutral",
};

/** States where a finding is still open work (mirrors backend OPEN_STATES). */
export const OPEN_STATES: InstanceState[] = ["new", "active", "in_progress", "pending_retest"];

export const ALL_STATES: InstanceState[] = [
  "new",
  "active",
  "in_progress",
  "pending_retest",
  "fixed",
  "resurfaced",
  "accepted",
  "false_positive",
];

export const STATE_LABEL: Record<InstanceState, string> = Object.fromEntries(
  Object.entries(STATE_META).map(([k, v]) => [k, v.label]),
) as Record<InstanceState, string>;
