import { Badge, Icon } from "@/components/ui";

/**
 * A preview of cross-framework mapping suggestions, deliberately half-visible.
 *
 * Everything below is ILLUSTRATIVE — a shape, not a result. Nothing in the
 * platform computes these today, so the panel is faded, non-interactive and
 * labelled, and the rows use frameworks Verity does not yet ship content for.
 * A reader must not be able to mistake this for a mapping their tenant has.
 */
const SAMPLE = [
  {
    framework: "ISO/IEC 27001:2022",
    code: "A.5.15",
    name: "Access control",
    coverage: "Full",
  },
  {
    framework: "SOC 2 (2017 TSC)",
    code: "CC6.2",
    name: "Registration and authorisation of users",
    coverage: "Full",
  },
  {
    framework: "GDPR",
    code: "Art. 32(1)(b)",
    name: "Confidentiality and integrity of processing",
    coverage: "Partial",
  },
] as const;

export function SuggestedMappingsTeaser() {
  return (
    <section
      aria-labelledby="suggested-mappings-heading"
      className="relative overflow-hidden rounded-lg border border-border bg-surface-primary"
    >
      <div className="flex flex-wrap items-start justify-between gap-3 p-5 pb-3">
        <div className="min-w-0">
          <h2
            id="suggested-mappings-heading"
            className="flex items-center gap-2 font-display text-title-md text-text-primary"
          >
            <Icon name="shield" className="size-4 text-action-accent" aria-hidden />
            Suggested control mappings
          </h2>
          <p className="mt-1 text-body-sm text-text-secondary">
            Controls this evidence may also satisfy, across every framework you
            carry. Review each row, then link the ones that fit — suggested
            automatically, never linked without a person saying so.
          </p>
        </div>
        <Badge variant="role">Coming soon</Badge>
      </div>

      {/* aria-hidden: illustrative rows are decoration, not content a screen
          reader should announce as this control's real mappings. */}
      <div aria-hidden className="px-5 pb-5">
        <table className="w-full table-fixed">
          <thead>
            <tr className="border-b border-border">
              {["Framework", "Control", "Coverage", ""].map((heading) => (
                <th key={heading} className="pb-2 text-left type-overline">
                  {heading}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {SAMPLE.map((row) => (
              <tr key={row.framework} className="border-b border-border last:border-0">
                <td className="py-3 pr-3 align-top text-body-sm text-text-primary">
                  {row.framework}
                </td>
                <td className="py-3 pr-3 align-top">
                  <span className="block font-display text-caption font-bold text-text-link">
                    {row.code}
                  </span>
                  <span className="block truncate text-caption text-text-subtle">
                    {row.name}
                  </span>
                </td>
                <td className="py-3 pr-3 align-top">
                  <Badge
                    variant={row.coverage === "Full" ? "count" : "countWarn"}
                  >
                    {row.coverage}
                  </Badge>
                </td>
                <td className="py-3 text-right align-top">
                  <span className="inline-flex items-center gap-1 rounded-sm bg-action-accent-tint px-2.5 py-1 text-label-sm text-action-accent opacity-60">
                    <Icon name="plus" className="size-3.5" aria-hidden />
                    Link
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* The fade is the honesty device: the panel is visibly a preview that
          runs out, not a list that happens to be short. */}
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-32 bg-gradient-to-t from-surface-primary via-surface-primary/85 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-center pb-4">
        <span className="rounded-full border border-border bg-surface-primary px-3 py-1.5 text-caption font-semibold text-text-secondary shadow-1">
          Example only — cross-framework suggestions arrive with the AI mapping
          engine
        </span>
      </div>
    </section>
  );
}
