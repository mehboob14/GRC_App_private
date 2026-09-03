import { cn } from "@/lib/cn";

/**
 * An entity's short code (BC-03, POL-014, CVE-2021-44228) rendered identically
 * on every screen it appears, per design-system 6.4.
 *
 * Promoted out of compliance/control-detail-page, which held the only version
 * that matched the documented spec. Three other pages had hand-rolled a mono
 * grey variant (rounded-sm bg-surface-sunken font-mono text-text-subtle); those
 * were the divergence, not this.
 */
export function CodeChip({ code, className }: { code: string; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link",
        className,
      )}
    >
      {code}
    </span>
  );
}
