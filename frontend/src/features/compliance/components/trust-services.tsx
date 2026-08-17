import { cn } from "@/lib/cn";
import type { TrustService } from "@/features/compliance/trust-services";

/**
 * Colour note (DS F12): a Trust Services Category says *what kind of control*
 * this is — a taxonomy, not a lifecycle state and not a severity. So the chips
 * are drawn from the `identity` ramp, which exists precisely for per-entity
 * categorical colour, rather than from `status-*` (where in the lifecycle) or
 * `severity-*` (how bad). Re-using either of those here would make a control
 * covering Privacy read as "worse" than one covering Security.
 *
 * Solid fill with inverse text, matching how the ramp is used everywhere else
 * (Avatar). The identity tokens are deliberately one definition with no `.dark`
 * override, so a tinted-background/coloured-text chip would be legible in light
 * mode and near-invisible in dark; white on the solid fill holds in both.
 *
 * The fill is applied through the token variable rather than a `bg-identity-1`
 * utility so it cannot depend on whether the JIT happened to scan this file.
 */
const TSC_TOKEN: Record<TrustService, string> = {
  Security: "--color-identity-1",
  Availability: "--color-identity-3",
  Confidentiality: "--color-identity-2",
  "Processing Integrity": "--color-identity-4",
  Privacy: "--color-identity-5",
};

/** Short forms — five full category names do not fit a table cell. */
const TSC_SHORT: Record<TrustService, string> = {
  Security: "Security",
  Availability: "Availability",
  Confidentiality: "Confidential.",
  "Processing Integrity": "Proc. Integrity",
  Privacy: "Privacy",
};

export function TrustServiceChip({
  tsc,
  className,
}: {
  tsc: TrustService;
  className?: string;
}) {
  const token = TSC_TOKEN[tsc];
  return (
    <span
      style={{ backgroundColor: `rgb(var(${token}))` }}
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-xs px-1.5 py-0.5 font-sans text-caption font-semibold text-text-inverse",
        className,
      )}
    >
      {/* The short form is what fits; the full name is the accessible name, so
          it is read out rather than hidden behind a hover-only title. */}
      <span className="sr-only">{tsc}</span>
      <span aria-hidden>{TSC_SHORT[tsc]}</span>
    </span>
  );
}

/** Neutral outline chip — a framework is a label, never a state. */
export function FrameworkChip({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-xs border border-border bg-surface-sunken px-1.5 py-0.5 font-sans text-caption font-medium text-text-secondary">
      {label}
    </span>
  );
}
