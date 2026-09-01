import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import { getSummary } from "../api";
import { ASSET_STATUSES, ASSET_TYPES, CRITICALITY_TIERS, type CriticalityTier } from "../types";
import { ASSET_TYPE_META, STATUS_META, TIER_META } from "../tokens";

const TIER_BAR: Record<CriticalityTier | "unassessed", string> = {
  critical: "bg-status-danger-base",
  high: "bg-status-warning-base",
  medium: "bg-action-accent",
  low: "bg-status-neutral-base",
  unassessed: "bg-surface-sunken",
};

export function AssetsOverviewPage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });
  const s = query.data;

  if (!s) {
    return <p className="text-body-md text-text-subtle">Loading…</p>;
  }

  const typeMax = Math.max(1, ...s.by_type.map((t) => t.count));

  return (
    <div className="space-y-5">
      {/* Stat tiles */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Total assets" value={s.total} />
        <Stat
          label="Inventory hygiene"
          value={`${s.hygiene_avg}%`}
          tone={s.hygiene_avg >= 80 ? "success" : s.hygiene_avg >= 40 ? "warning" : "danger"}
        />
        <Stat label="Critical" value={s.by_tier.critical} tone="danger" onClick={() => navigate("/assets?tier=critical")} />
        <Stat label="Stale > 90d" value={s.stale} tone="warning" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Criticality distribution */}
        <Panel title="Criticality">
          <div className="space-y-2.5">
            {([...CRITICALITY_TIERS, "unassessed"] as const).map((tier) => {
              const count = s.by_tier[tier];
              const pct = s.total ? Math.round((count / s.total) * 100) : 0;
              return (
                <div key={tier} className="flex items-center gap-3">
                  <span className="w-24 shrink-0 text-body-sm text-text-secondary">
                    {tier === "unassessed" ? "Not assessed" : TIER_META[tier].label}
                  </span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <div className={cn("h-full rounded-full", TIER_BAR[tier])} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-8 shrink-0 text-right tabular text-body-sm text-text-primary">{count}</span>
                </div>
              );
            })}
          </div>
        </Panel>

        {/* By type */}
        <Panel title="By type">
          <div className="space-y-2.5">
            {ASSET_TYPES.map((t) => {
              const count = s.by_type.find((x) => x.type === t)?.count ?? 0;
              return (
                <div key={t} className="flex items-center gap-3">
                  <span className="w-32 shrink-0 text-body-sm text-text-secondary">{ASSET_TYPE_META[t].label}</span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <div className="h-full rounded-full bg-action-accent" style={{ width: `${(count / typeMax) * 100}%` }} />
                  </div>
                  <span className="w-8 shrink-0 text-right tabular text-body-sm text-text-primary">{count}</span>
                </div>
              );
            })}
          </div>
        </Panel>

        {/* Lifecycle */}
        <Panel title="Lifecycle">
          <div className="flex flex-wrap gap-2">
            {ASSET_STATUSES.map((st) => (
              <div key={st} className="flex items-center gap-2 rounded-md border border-border px-3 py-2">
                <span className="text-body-sm text-text-secondary">{STATUS_META[st].label}</span>
                <span className="tabular text-body-md font-semibold text-text-primary">{s.by_status[st]}</span>
              </div>
            ))}
          </div>
        </Panel>

        {/* Attention */}
        <Panel title="Needs attention">
          <ul className="space-y-2">
            <AttentionRow icon="alert" label="Missing a CIA rating" count={s.needs_cia} onClick={() => navigate("/assets?attention=1")} />
            <AttentionRow icon="clock" label="Stale (not reviewed in 90 days)" count={s.stale} onClick={() => navigate("/assets?attention=1")} />
            <AttentionRow icon="shield" label="Regulated data in scope" count={s.regulated} />
          </ul>
        </Panel>
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
  onClick,
}: {
  label: string;
  value: number | string;
  tone?: "success" | "warning" | "danger";
  onClick?: () => void;
}) {
  const toneClass =
    tone === "success" ? "text-status-success-text" : tone === "warning" ? "text-status-warning-text" : tone === "danger" ? "text-status-danger-text" : "text-text-primary";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={!onClick}
      className={cn(
        "rounded-lg border border-border bg-surface-primary px-4 py-3.5 text-left",
        onClick ? "transition-colors hover:border-border-strong" : "cursor-default",
      )}
    >
      <p className="text-caption text-text-subtle">{label}</p>
      <p className={cn("mt-1 font-display text-heading-md tabular", toneClass)}>{value}</p>
    </button>
  );
}

function AttentionRow({ icon, label, count, onClick }: { icon: "alert" | "clock" | "shield"; label: string; count: number; onClick?: () => void }) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        disabled={!onClick}
        className={cn(
          "flex w-full items-center gap-2.5 rounded-sm px-1 py-1.5 text-left",
          onClick ? "hover:bg-surface-hover" : "cursor-default",
        )}
      >
        <Icon name={icon} className="size-4 text-text-subtle" />
        <span className="flex-1 text-body-sm text-text-secondary">{label}</span>
        <span className="tabular text-body-md font-semibold text-text-primary">{count}</span>
      </button>
    </li>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="mb-4 font-display text-title-sm text-text-primary">{title}</h2>
      {children}
    </div>
  );
}
