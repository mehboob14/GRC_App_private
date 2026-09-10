import type { StatusFamily } from "./status-pill";

// Kept out of `status-pill.tsx` so that module exports only its component;
// a file that mixes components with plain values loses fast refresh. The
// import above is type-only, so nothing links back at runtime.

/**
 * Canonical lifecycle → family map (DS §6.1). The same word must render the
 * same way on every screen; look words up here instead of hardcoding a
 * family per call site.
 */
export const STATUS_WORD_FAMILY: Readonly<Record<string, StatusFamily>> = {
  // success
  passing: "success",
  complete: "success",
  healthy: "success",
  published: "success",
  active: "success",
  granted: "success",
  fixed: "success",
  retained: "success",
  "on track": "success",
  compliant: "success",
  // danger
  failing: "danger",
  overdue: "danger",
  expired: "danger",
  revoked: "danger",
  behind: "danger",
  breached: "danger",
  // warning
  "needs review": "warning",
  aging: "warning",
  "due soon": "warning",
  "at risk": "warning",
  degraded: "warning",
  "sync error": "warning",
  // progress
  "in progress": "progress",
  monitoring: "progress",
  mitigating: "progress",
  syncing: "progress",
  running: "progress",
  // pending
  pending: "pending",
  "in review": "pending",
  queued: "pending",
  "awaiting approval": "pending",
  "not started": "pending",
  // neutral
  draft: "neutral",
  inactive: "neutral",
  archived: "neutral",
  "not applicable": "neutral",
  "not configured": "neutral",
  // Week 1 IAM words, mapped once here so every screen renders them alike:
  // membership lifecycle (invited → active → disabled) and MFA enrollment.
  invited: "pending",
  disabled: "neutral",
  // Connector catalogue: a provider with no credential configured. Sits beside
  // the map's own "not configured" in the neutral family — it is a fact, not a
  // failure, and it must never render as danger or warning.
  "not connected": "neutral",
  enrolled: "success",
  "not enrolled": "warning",
  enforced: "success",
  // Week 5 third-party risk. The vendor lifecycle, the assessment states and
  // the gate decisions, mapped once here so "Approved" is the same green
  // whether it labels a vendor, an intake request or a gate decision.
  requested: "pending",
  "under review": "progress",
  approved: "success",
  "approved with conditions": "warning",
  flagged: "danger",
  "on hold": "warning",
  offboarding: "warning",
  terminated: "neutral",
  submitted: "progress",
  scored: "success",
  skipped: "neutral",
  deferred: "pending",
  rejected: "danger",
  declined: "danger",
  "in remediation": "progress",
  accepted: "pending",
  met: "success",
  waived: "neutral",
  received: "progress",
  reviewed: "success",
  "not screened": "pending",
  screened: "success",
  "not tiered": "neutral",
  "not scored": "neutral",
};

/** Family for a canonical status word, or undefined for unmapped words. */
export function statusFamilyFor(word: string): StatusFamily | undefined {
  return STATUS_WORD_FAMILY[word.trim().toLowerCase()];
}
