import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ErrorState, SegmentedControl, Skeleton, StatusPill } from "@/components/ui";
import { describeError } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { objectivesApi, OUTCOME } from "./api";

/**
 * Assessment objectives across the workspace (AO-2 to AO-5): per framework, how many controls
 * show their design and their operation, the first audit view (SOC 2 Type 1 design, ISO Stage 1
 * design), the next objectives to meet, and a comparison with today's readiness that the owner
 * reads before readiness ever switches to objectives.
 */

type View = "next" | "compare";

export function ObjectivesPage() {
  const { principal } = useAuth();
  const [view, setView] = useState<View>("next");
  const overview = useQuery({
    queryKey: ["objectives", principal?.tenant_id],
    queryFn: objectivesApi.overview,
  });
  const comparison = useQuery({
    queryKey: ["objectives", principal?.tenant_id, "comparison"],
    queryFn: objectivesApi.comparison,
    enabled: view === "compare",
  });

  if (overview.isLoading) return <Skeleton className="h-96 w-full rounded-lg" />;
  if (overview.isError || !overview.data) {
    const failure = describeError(overview.error, "objectives");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void overview.refetch() : undefined}
      />
    );
  }
  const data = overview.data;

  return (
    <div className="space-y-4">
      <p className="text-body-sm text-text-secondary">
        {data.controls_with_objectives} of {data.controls_total} controls have objectives so far.
        {data.review_status !== "reviewed" ? " Drafted by Verity, not yet independently reviewed." : ""}
      </p>
      <div className="grid gap-3 md:grid-cols-2">
        {data.frameworks.map((f) => (
          <section key={f.code} className="rounded-lg border border-border bg-surface-primary px-5 py-4">
            <h2 className="font-display text-title-md text-text-primary">{f.name}</h2>
            <dl className="mt-3 grid grid-cols-3 gap-3 text-body-sm">
              <Figure label="Objectives met" value={`${f.objectives_satisfied} of ${f.objectives_total}`} />
              <Figure label="Design shown" value={`${f.design_ready} of ${f.controls}`} />
              <Figure label="Operation shown" value={`${f.operating_ready} of ${f.controls}`} />
            </dl>
            <div className="mt-3 rounded-md bg-surface-sunken px-3 py-2 text-body-sm">
              <span className="font-semibold text-text-primary">
                {f.first_audit_label}: {f.first_audit_ready} of {f.controls} controls ready
              </span>
              <ul className="mt-1 text-text-secondary">
                {f.first_audit_notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </div>
          </section>
        ))}
      </div>

      <SegmentedControl
        items={[
          { id: "next", label: "Next to meet" },
          { id: "compare", label: "Compare with today" },
        ]}
        value={view}
        onChange={(v) => setView(v as View)}
        label="Objectives view"
      />

      {view === "next" ? (
        <div className="rounded-lg border border-border bg-surface-primary">
          {data.next.map((n) => (
            <div key={n.objective.code} className="flex flex-wrap items-center gap-3 border-t border-border px-5 py-3 first:border-t-0">
              <span className="min-w-[64px] font-mono text-body-sm text-text-primary">{n.objective.code}</span>
              <span className="min-w-0 flex-1 text-body-sm text-text-primary">
                {n.objective.statement}
                <span className="block text-caption text-text-subtle">
                  {n.control_name}, {n.objective.assurance === "design" ? "design" : "operation"}
                </span>
              </span>
              <StatusPill status={OUTCOME[n.objective.outcome].family} label={OUTCOME[n.objective.outcome].label} />
              <Link to={`/controls/${n.control_id}?tab=objectives`} className="text-body-sm text-text-link">
                {n.objective.next_step?.label ?? "Open"}
              </Link>
            </div>
          ))}
        </div>
      ) : comparison.isLoading || !comparison.data ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : (
        <div className="space-y-2">
          <p className="text-body-sm text-text-secondary">
            {comparison.data.compared} controls compared. Readiness would change for{" "}
            {comparison.data.differ_rule_b} if a passing check may count, and for{" "}
            {comparison.data.differ_rule_a} if only people's evidence counts. Nothing changes until you choose.
          </p>
          <div className="overflow-x-auto rounded-lg border border-border bg-surface-primary">
            <table className="w-full min-w-[640px] text-left text-body-sm">
              <thead className="border-b border-border text-caption text-text-subtle">
                <tr>
                  <th className="px-4 py-2.5 font-normal">Control</th>
                  <th className="px-4 py-2.5 font-normal">Ready today</th>
                  <th className="px-4 py-2.5 font-normal">With objectives</th>
                  <th className="px-4 py-2.5 font-normal">Holding it back</th>
                </tr>
              </thead>
              <tbody>
                {comparison.data.rows.map((r) => (
                  <tr key={r.control_id} className="border-b border-border last:border-b-0">
                    <td className="px-4 py-2.5">
                      <Link to={`/controls/${r.control_id}?tab=objectives`} className="text-text-link">
                        {r.code}
                      </Link>{" "}
                      <span className="text-text-secondary">{r.name}</span>
                    </td>
                    <td className="px-4 py-2.5">{r.ready_today ? "Yes" : "No"}</td>
                    <td className="px-4 py-2.5">{r.ready_rule_b ? "Yes" : "No"}</td>
                    <td className="px-4 py-2.5 font-mono text-caption text-text-secondary">{r.blocking.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function Figure({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-caption text-text-subtle">{label}</dt>
      <dd className="font-semibold tabular text-text-primary">{value}</dd>
    </div>
  );
}
