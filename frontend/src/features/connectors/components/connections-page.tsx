import { Button, Icon, StatusPill, statusFamilyFor } from "@/components/ui";
import { VENDOR_MARKS, type VendorMark } from "@/lib/vendor-marks";

type DownConnection = {
  id: string;
  name: string;
  mark: VendorMark;
  detail: string;
  impact: string;
};

type HealthyConnection = {
  id: string;
  name: string;
  mark: VendorMark;
  synced: string;
  checks: number;
  controls: number;
  evidence: number;
};

const DOWN: DownConnection[] = [
  {
    id: "datadog",
    name: "Datadog",
    mark: VENDOR_MARKS.datadog,
    detail: "Offline 6h · sync failed",
    impact: "Breaking CC7.2, A1.2 · 14 evidence items stale",
  },
  {
    id: "gws",
    name: "Google Workspace",
    mark: VENDOR_MARKS.gws,
    detail: "Auth expired · token revoked",
    impact: "Breaking CC6.2 · 9 evidence items stale",
  },
];

const HEALTHY: HealthyConnection[] = [
  {
    id: "aws",
    name: "Amazon Web Services",
    mark: VENDOR_MARKS.aws,
    synced: "Synced 4m ago",
    checks: 18,
    controls: 42,
    evidence: 214,
  },
  {
    id: "okta",
    name: "Okta",
    mark: VENDOR_MARKS.okta,
    synced: "Synced 12m ago",
    checks: 9,
    controls: 21,
    evidence: 88,
  },
  {
    id: "github",
    name: "GitHub",
    mark: VENDOR_MARKS.github,
    synced: "Synced 8m ago",
    checks: 12,
    controls: 16,
    evidence: 64,
  },
  {
    id: "snowflake",
    name: "Snowflake",
    mark: VENDOR_MARKS.snowflake,
    synced: "Synced 21m ago",
    checks: 6,
    controls: 11,
    evidence: 37,
  },
  {
    id: "crowdstrike",
    name: "CrowdStrike",
    mark: VENDOR_MARKS.crowdstrike,
    synced: "Synced 15m ago",
    checks: 7,
    controls: 14,
    evidence: 52,
  },
  {
    id: "jira",
    name: "Jira",
    mark: VENDOR_MARKS.jira,
    synced: "Synced 9m ago",
    checks: 4,
    controls: 8,
    evidence: 29,
  },
  {
    id: "cloudflare",
    name: "Cloudflare",
    mark: VENDOR_MARKS.cloudflare,
    synced: "Synced 6m ago",
    checks: 5,
    controls: 9,
    evidence: 41,
  },
];

/** DS §6.4 source/vendor cell: brand tile + name. Brand hex is sanctioned. */
function VendorTile({
  mark,
  className,
}: {
  mark: VendorMark;
  className?: string;
}) {
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-md text-caption font-bold text-white ${className ?? "size-9"}`}
      style={{ backgroundColor: mark.color }}
      aria-hidden
    >
      {mark.label}
    </span>
  );
}

/** Figma A2 · Connections (121:5989) — Phase 1 shell with mock connector health. */
export function ConnectionsPage() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-heading-lg text-text-primary">
        Connection health &amp; impact
      </h1>
      <p className="mt-2 text-body-lg text-text-secondary">
        Every connector shows the controls, checks and evidence it feeds.
      </p>

      {/* Ongoing condition → page banner (§7.2), danger family. */}
      <div className="mt-5 flex items-center gap-2.5 rounded-md border border-status-danger-border bg-status-danger-bg px-3.5 py-3">
        <Icon
          name="alert"
          className="size-4 shrink-0 text-status-danger-base"
        />
        <p className="text-label-md text-status-danger-text">
          <span className="tabular">2</span> connections down · breaking{" "}
          <span className="tabular">3</span> controls ·{" "}
          <span className="tabular">23</span> evidence items now stale
        </p>
      </div>

      <div className="mt-4 space-y-2.5">
        {DOWN.map((row) => (
          <div
            key={row.id}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface-primary px-4 py-3"
          >
            <VendorTile mark={row.mark} />
            <div className="min-w-0 flex-1">
              <p className="flex items-center gap-2 text-body-lg font-semibold text-text-primary">
                {row.name}
                <StatusPill
                  status={statusFamilyFor("Failing") ?? "unknown"}
                  label="Failing"
                />
              </p>
              <p className="text-body-sm text-text-subtle">{row.detail}</p>
              <p className="mt-1 text-body-sm font-medium text-status-danger-text">
                {row.impact}
              </p>
            </div>
            {/* Repeated row action — secondary keeps one-primary-per-region. */}
            <Button variant="secondary" size="sm" className="shrink-0">
              Reconnect
            </Button>
          </div>
        ))}
      </div>

      <h2 className="mb-3 mt-8 font-display text-heading-sm text-text-primary">
        Healthy connections
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {HEALTHY.map((row) => (
          <div
            key={row.id}
            className="rounded-lg border border-border bg-surface-primary p-4"
          >
            <div className="flex items-center gap-2.5">
              <VendorTile mark={row.mark} className="size-8" />
              <div className="min-w-0">
                <p className="truncate text-body-md font-semibold text-text-primary">
                  {row.name}
                </p>
                <p className="flex items-center gap-1.5">
                  <StatusPill
                    kind="inline"
                    status={statusFamilyFor("Healthy") ?? "unknown"}
                    label="Healthy"
                  />
                  <span className="tabular text-caption text-text-subtle">
                    · {row.synced}
                  </span>
                </p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-3 gap-2 border-t border-border pt-3">
              <Metric label="checks" value={row.checks} />
              <Metric label="controls" value={row.controls} />
              <Metric label="evidence" value={row.evidence} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="tabular font-display text-numeral-sm text-text-primary">
        {value}
      </p>
      <p className="text-caption text-text-subtle">{label}</p>
    </div>
  );
}
