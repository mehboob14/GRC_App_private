import type { Control } from "@/lib/api/types";

/** The five SOC 2 Trust Services Categories, in canonical order. */
export const TRUST_SERVICES = [
  "Security",
  "Availability",
  "Confidentiality",
  "Processing Integrity",
  "Privacy",
] as const;

export type TrustService = (typeof TRUST_SERVICES)[number];

/**
 * A SOC 2 criterion code maps to one category by its prefix. This is the
 * fallback: the authoritative answer is `Requirement.trust_services_category`
 * from the server, which the page prefers when it has loaded. Order matters —
 * CC before C, PI before P.
 */
export function trustServiceFor(criterion: string): TrustService | null {
  if (criterion.startsWith("CC")) return "Security";
  if (criterion.startsWith("PI")) return "Processing Integrity";
  if (criterion.startsWith("A")) return "Availability";
  if (criterion.startsWith("C")) return "Confidentiality";
  if (criterion.startsWith("P")) return "Privacy";
  return null;
}

/**
 * The distinct categories a control covers, in canonical order.
 *
 * Only SOC 2 keys are interpreted: Trust Services Categories are a SOC 2
 * concept, and the prefix rule would otherwise read an ISO key like
 * `ISO27001:A.5.1` as "Availability", inventing a category the framework does
 * not have.
 */
export function trustServicesFor(control: Control): TrustService[] {
  const found = new Set<TrustService>();
  for (const key of control.requirement_keys) {
    if (!key.startsWith("SOC2:")) continue;
    const tsc = trustServiceFor(key.slice("SOC2:".length));
    if (tsc) found.add(tsc);
  }
  return TRUST_SERVICES.filter((tsc) => found.has(tsc));
}

const FRAMEWORK_LABEL: Record<string, string> = {
  SOC2: "SOC 2",
  ISO27001: "ISO 27001",
  HIPAA: "HIPAA",
};

/**
 * The frameworks a control answers to, read off its criteria keys
 * (`"SOC2:CC6.1"` → `SOC 2`). A control mapped to nothing shows no framework,
 * which is the honest answer rather than a default badge.
 */
export function frameworksFor(control: Control): string[] {
  const found = new Set<string>();
  for (const key of control.requirement_keys) {
    const prefix = key.includes(":") ? key.slice(0, key.indexOf(":")) : "";
    if (prefix) found.add(FRAMEWORK_LABEL[prefix] ?? prefix);
  }
  return [...found].sort();
}
