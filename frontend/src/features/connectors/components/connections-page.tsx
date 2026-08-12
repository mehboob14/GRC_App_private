import { Button } from "@/components/ui";

type DownConnection = {
  id: string;
  name: string;
  mark: string;
  markColor: string;
  status: string;
  impact: string;
};

type HealthyConnection = {
  id: string;
  name: string;
  mark: string;
  markColor: string;
  synced: string;
  checks: number;
  controls: number;
  evidence: number;
};

const DOWN: DownConnection[] = [
  {
    id: "datadog",
    name: "Datadog",
    mark: "DD",
    markColor: "bg-[#632ca6]",
    status: "Offline 6h · sync failed",
    impact: "Breaking CC7.2, A1.2 · 14 evidence items stale",
  },
  {
    id: "gws",
    name: "Google Workspace",
    mark: "GW",
    markColor: "bg-[#0a6dd8]",
    status: "Auth expired · token revoked",
    impact: "Breaking CC6.2 · 9 evidence items stale",
  },
];

const HEALTHY: HealthyConnection[] = [
  {
    id: "aws",
    name: "Amazon Web Services",
    mark: "AWS",
    markColor: "bg-[#f90]",
    synced: "Synced 4m ago",
    checks: 18,
    controls: 42,
    evidence: 214,
  },
  {
    id: "okta",
    name: "Okta",
    mark: "OK",
    markColor: "bg-[#0a6dd8]",
    synced: "Synced 12m ago",
    checks: 9,
    controls: 21,
    evidence: 88,
  },
  {
    id: "github",
    name: "GitHub",
    mark: "GH",
    markColor: "bg-[#1b1f24]",
    synced: "Synced 8m ago",
    checks: 12,
    controls: 16,
    evidence: 64,
  },
  {
    id: "snowflake",
    name: "Snowflake",
    mark: "SF",
    markColor: "bg-[#29b5e8]",
    synced: "Synced 21m ago",
    checks: 6,
    controls: 11,
    evidence: 37,
  },
  {
    id: "crowdstrike",
    name: "CrowdStrike",
    mark: "CS",
    markColor: "bg-[#ec0000]",
    synced: "Synced 15m ago",
    checks: 7,
    controls: 14,
    evidence: 52,
  },
  {
    id: "jira",
    name: "Jira",
    mark: "JI",
    markColor: "bg-[#0052cc]",
    synced: "Synced 9m ago",
    checks: 4,
    controls: 8,
    evidence: 29,
  },
  {
    id: "cloudflare",
    name: "Cloudflare",
    mark: "CF",
    markColor: "bg-[#f6821f]",
    synced: "Synced 6m ago",
    checks: 5,
    controls: 9,
    evidence: 41,
  },
];

/** Figma A2 · Connections (121:5989) — Phase 1 shell with mock connector health. */
export function ConnectionsPage() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-[28px] font-extrabold leading-8 tracking-[-0.56px] text-text-primary">
        Connection health &amp; impact
      </h1>
      <p className="mt-2 text-[14px] leading-5 text-text-secondary">
        Every connector shows the controls, checks and evidence it feeds.
      </p>

      <div className="mt-5 flex items-center gap-2 rounded-lg border border-status-danger-border bg-status-danger-bg px-4 py-3 text-[13px] font-medium text-status-danger-text">
        <span className="size-1.5 rounded-full bg-status-danger-base" />
        2 connections down · breaking 3 controls · 23 evidence items now stale
      </div>

      <div className="mt-4 space-y-2.5">
        {DOWN.map((row) => (
          <div
            key={row.id}
            className="flex items-center gap-3 rounded-lg border border-border bg-surface-primary px-4 py-3.5"
          >
            <span
              className={`flex size-9 items-center justify-center rounded-md text-[11px] font-bold text-white ${row.markColor}`}
            >
              {row.mark}
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-[14px] font-semibold text-text-primary">{row.name}</p>
              <p className="text-[12px] text-text-subtle">{row.status}</p>
              <p className="mt-1 text-[12px] font-medium text-status-danger-text">{row.impact}</p>
            </div>
            <Button size="sm">Reconnect</Button>
          </div>
        ))}
      </div>

      <h2 className="mb-3 mt-8 text-[14px] font-semibold text-text-primary">
        Healthy connections
      </h2>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {HEALTHY.map((row) => (
          <div
            key={row.id}
            className="rounded-lg border border-border bg-surface-primary p-4"
          >
            <div className="flex items-center gap-2.5">
              <span
                className={`flex size-8 items-center justify-center rounded-md text-[10px] font-bold text-white ${row.markColor}`}
              >
                {row.mark}
              </span>
              <div>
                <p className="text-[13px] font-semibold text-text-primary">{row.name}</p>
                <p className="flex items-center gap-1.5 text-[12px] text-status-success-text">
                  <span className="size-1.5 rounded-full bg-status-success-base" />
                  {row.synced}
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
      <p className="font-display text-[18px] font-bold tabular text-text-primary">{value}</p>
      <p className="text-[11px] text-text-subtle">{label}</p>
    </div>
  );
}
