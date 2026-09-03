import { Badge, SeverityChip, type Severity as ChipSeverity } from "@/components/ui";
import type { Severity } from "../types";

/** A severity chip that also handles "info" (which the base SeverityChip omits). */
export function SeverityBadge({ severity }: { severity: Severity }) {
  if (severity === "info") return <Badge variant="neutral">Info</Badge>;
  const label = severity.charAt(0).toUpperCase() + severity.slice(1);
  return <SeverityChip severity={severity as ChipSeverity} label={label} />;
}
