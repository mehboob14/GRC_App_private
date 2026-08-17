import { cn } from "@/lib/cn";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";
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

/**
 * The framework's own mark, in the same contained treatment as the sign-up
 * marquee: a light disc with a hairline ring, so a logo of any colour stays
 * legible on a hovered or selected row.
 *
 * The logo is the whole cell content, so the name has to reach the reader some
 * other way — `FrameworkLogo` sets `alt`/`title`, and the visually-hidden span
 * keeps the column meaningful when the image is the only thing rendered.
 */
export function FrameworkChip({ label, size = 28 }: { label: string; size?: number }) {
  return (
    <span
      title={label}
      className="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface-primary ring-1 ring-border"
      style={{ width: size, height: size }}
    >
      {/* Eager: the whole table shares a handful of distinct logos, so this is
          one cached request, and lazy-loading would pop icons in mid-scroll. */}
      <FrameworkLogo name={label} size={Math.round(size * 0.68)} eager />
      <span className="sr-only">{label}</span>
    </span>
  );
}
