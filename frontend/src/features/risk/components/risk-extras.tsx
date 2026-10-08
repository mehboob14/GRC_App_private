import { StatusPill } from "@/components/ui";
import { useCustomFields } from "@/features/custom-fields/hooks";
import { customFieldText } from "@/features/custom-fields/format";
import { APPETITE_META } from "../scoring";

/** Where a risk sits against the category's appetite and tolerance. Nothing when none is set. */
export function AppetitePill({ status }: { status: string | null | undefined }) {
  const meta = status ? APPETITE_META[status] : undefined;
  if (!meta) return null;
  return <StatusPill status={meta.family} label={meta.label} kind="inline" />;
}

/** The workspace's own fields on one risk, read only. */
export function CustomValues({ values }: { values: Record<string, string | number | boolean> }) {
  const fields = (useCustomFields("risks", true).data ?? []).filter((f) => !f.archived || f.key in values);
  if (fields.length === 0) return null;
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <h3 className="mb-3 font-display text-title-sm text-text-primary">More details</h3>
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {fields.map((f) => (
          <div key={f.id}>
            <dt className="text-label-sm text-text-subtle">{f.label}</dt>
            <dd className="whitespace-pre-line text-body-md text-text-primary">{customFieldText(f, values[f.key])}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
