import type { Severity } from "./severity";

/**
 * Label colour for text placed beside the chip (DS §2.6).
 *
 * Kept out of `severity.tsx` so that module exports only its components; a file
 * that mixes the two loses fast refresh. The import above is type-only, so
 * nothing links back at runtime.
 */
export const severityTextClass: Record<Severity, string> = {
  critical: "text-severity-critical",
  high: "text-severity-high",
  medium: "text-severity-medium",
  low: "text-status-neutral-text",
};
