import { useState } from "react";
import { Button, Card, Icon, StatusPill, statusFamilyFor } from "@/components/ui";
import { cn } from "@/lib/cn";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";
import { Donut } from "./donut";

const ring = (pct: number, color: string) => [
  { value: pct, color },
  { value: 100 - pct, color: "transparent" },
];

// Admin posture dashboard — framework rings + TSC coverage from the Executive
// Briefing, and the Bento posture tiles (minus "Controls by SOC 2 family" and
// "Connectors"). Charts replicate the reference: donut rings, stacked coverage
// bars, and the risk heatmap. Mock data until each module's backend lands.

const TOKEN = {
  green: "rgb(var(--color-status-success-base))",
  amber: "rgb(var(--color-status-warning-base))",
  red: "rgb(var(--color-status-danger-base))",
  blue: "rgb(var(--color-action-accent))",
  neutral: "rgb(var(--color-status-neutral-base))",
};

// ── Data ─────────────────────────────────────────────────────────────────
const FRAMEWORKS = [
  { name: "SOC 2 Type II", phase: "Type II window", status: "On track", pct: 91, pass: 124, fail: 3, review: 4, color: TOKEN.green },
  { name: "ISO 27001", phase: "Stage 2 · Nov", status: "At risk", pct: 78, pass: 74, fail: 6, review: 7, color: TOKEN.amber },
  { name: "HIPAA Security", phase: "Readiness Q1", status: "Behind", pct: 64, pass: 59, fail: 9, review: 11, color: TOKEN.red },
];

// have = passing; the remainder splits into needs-review then failing.
const TSC = [
  { name: "Security (Common Criteria)", have: 88, total: 95, review: 5, fail: 2, pct: 93 },
  { name: "Availability", have: 7, total: 10, review: 2, fail: 1, pct: 70 },
  { name: "Confidentiality", have: 8, total: 8, review: 0, fail: 0, pct: 100 },
  { name: "Processing Integrity", have: 4, total: 6, review: 2, fail: 0, pct: 67 },
  { name: "Privacy", have: 5, total: 9, review: 2, fail: 2, pct: 56 },
];

const VULN_SEGMENTS = [
  { label: "Critical", value: 4, color: TOKEN.red },
  { label: "High", value: 5, color: "#f97316" },
  { label: "Medium", value: 4, color: "#eab308" },
  { label: "Low", value: 1, color: TOKEN.neutral },
];

// Likelihood (row, top = highest) × impact (col, right = highest). Counts sum
// to the 12 active risks; colour follows the severity diagonal.
const HEAT: number[][] = [
  [0, 0, 1, 1, 1],
  [0, 1, 3, 2, 0],
  [0, 1, 1, 0, 0],
  [1, 0, 0, 0, 0],
  [0, 0, 0, 0, 0],
];

const TOP_RISKS = [
  { score: 16, title: "Unpatched critical vulnerability in prod", ref: "R-052 · Security" },
  { score: 15, title: "Ransomware / malware outbreak", ref: "R-001 · Security" },
  { score: 12, title: "Sub-processor data breach", ref: "R-029 · Vendor" },
  { score: 12, title: "Phishing → credential theft", ref: "R-058 · Security" },
  { score: 9, title: "Vendor concentration risk", ref: "R-041 · Vendor" },
];

const ASSETS = [
  { label: "Restricted", value: 24, color: TOKEN.red },
  { label: "Confidential", value: 162, color: "#f97316" },
  { label: "Internal / Public", value: 1098, color: TOKEN.blue },
];

function riskScoreTone(score: number): string {
  if (score >= 15) return "bg-status-danger-bg text-status-danger-text";
  if (score >= 10) return "bg-status-warning-bg text-status-warning-text";
  return "bg-status-progress-bg text-status-progress-text";
}

// Heatmap cell colour by severity rank (likelihood + impact).
function heatColor(rowFromTop: number, col: number): string {
  const sev = (4 - rowFromTop) + col; // 0..8
  if (sev >= 6) return "bg-status-danger-base/80";
  if (sev >= 4) return "bg-status-warning-base/70";
  if (sev >= 2) return "bg-status-warning-base/25";
  return "bg-status-success-base/25";
}

export function AdminDashboard() {
  const [range, setRange] = useState<"Live" | "Weekly">("Live");
  const assetMax = Math.max(...ASSETS.map((a) => a.value));

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="font-display text-heading-lg text-text-primary">Compliance posture</h1>
        <div className="flex flex-wrap items-center gap-3">
          {/* The range switch governs the whole page, so it sits with the page
              title rather than over one section of it. */}
          <div className="flex shrink-0 rounded-md border border-border p-0.5">
            {(["Live", "Weekly"] as const).map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setRange(r)}
                className={cn(
                  "rounded-sm px-3 py-1 text-label-sm transition-colors duration-80 ease-state",
                  range === r
                    ? "bg-action-accent-tint text-action-accent"
                    : "text-text-secondary hover:text-text-primary",
                )}
              >
                {r}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3 py-1.5">
            <span className="text-body-sm text-text-subtle">Overall trust score</span>
            <span className="font-display text-title-sm font-bold text-status-success-text">A · Strong</span>
          </div>
          <Button variant="secondary" size="sm">
            <Icon name="doc" className="size-4" />
            Export brief
          </Button>
        </div>
      </div>

      {/* SOC 2 readiness — the headline number, so it leads the page. Full
          width: it is the only tile with a hero donut and a stat strip, and
          boxing it into two of three columns left it visually unbalanced. */}
      <Card
        className="mt-5 p-5"
        style={{
          background:
            "linear-gradient(135deg, rgb(var(--color-action-accent) / 0.14), rgb(var(--color-action-accent) / 0.04))",
          borderColor: "rgb(var(--color-action-accent) / 0.18)",
        }}
      >
        <div className="flex items-center justify-between">
          <p className="text-overline font-bold uppercase text-action-accent">
            SOC 2 Type II readiness
          </p>
          <span className="inline-flex items-center gap-0.5 rounded-full bg-surface-primary px-2.5 py-1 text-caption font-bold text-status-success-text shadow-sm">
            <Icon name="arrowup" className="size-3.5" />
            +4%
          </span>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-6">
          <Donut size={132} stroke={14} segments={ring(91, TOKEN.blue)}>
            <span className="font-display text-numeral-lg tabular text-text-primary">91%</span>
            <span className="mt-1 text-caption text-action-accent">124 / 136 controls</span>
          </Donut>
          <div className="min-w-[240px] flex-1">
            <p className="font-display text-title-md text-text-primary">Audit-ready</p>
            <p className="mt-1 text-body-sm text-text-secondary">
              On track for the Sep 15 window. 2 critical exceptions in remediation.
            </p>
            <div className="mt-3 flex flex-wrap gap-6">
              <MiniStat value="3" label="Failing" tone="text-status-danger-text" />
              <MiniStat value="6" label="Review" tone="text-status-warning-text" />
              <MiniStat value="55d" label="To audit" />
            </div>
          </div>
        </div>
        <div className="mt-4 grid grid-cols-2 gap-2 border-t border-action-accent/15 pt-4 sm:grid-cols-4">
          {(
            [
              ["Controls", "124", "shield", "text-action-accent"],
              ["Evidence", "842", "doc", "text-action-accent"],
              ["Risks", "12", "risk", "text-status-warning-text"],
              ["Vulns", "64", "sun", "text-status-danger-text"],
            ] as const
          ).map(([label, value, icon, tone]) => (
            <div
              key={label}
              className="rounded-lg border border-border bg-surface-primary px-3 py-2.5"
            >
              <p className="flex items-center gap-1.5 text-caption text-text-secondary">
                <Icon name={icon} className={cn("size-4", tone)} />
                {label}
              </p>
              <p className="mt-1 font-display text-numeral-md tabular text-text-primary">{value}</p>
            </div>
          ))}
        </div>
      </Card>

      {/* Framework compliance cards — donut rings */}
      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-3">
        {FRAMEWORKS.map((fw) => (
          <Card key={fw.name} className="p-4">
            <div className="flex items-center gap-2.5">
              {/* The framework's own mark, in the same contained treatment as
                  the sign-in marquee and the controls table — one presentation
                  of a framework across the product. */}
              <span className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface-primary ring-1 ring-border">
                <FrameworkLogo name={fw.name} size={24} eager />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-body-md font-semibold text-text-primary">{fw.name}</p>
                <p className="text-caption text-text-subtle">{fw.phase}</p>
              </div>
              <StatusPill kind="inline" status={statusFamilyFor(fw.status) ?? "unknown"} label={fw.status} />
            </div>
            <div className="mt-3 flex items-center gap-4">
              <Donut size={92} stroke={11} segments={ring(fw.pct, fw.color)}>
                <span className="font-display text-numeral-md tabular text-text-primary">{fw.pct}%</span>
              </Donut>
              <div className="flex-1 space-y-1.5 text-body-sm">
                <div className="flex justify-between">
                  <span className="text-text-secondary">Passing</span>
                  <span className="tabular font-semibold text-status-success-text">{fw.pass}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Failing</span>
                  <span className="tabular font-semibold text-status-danger-text">{fw.fail}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-text-secondary">Review</span>
                  <span className="tabular font-semibold text-status-warning-text">{fw.review}</span>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Coverage by SOC 2 Trust Services Criteria — stacked bars */}
      <Card className="mt-6 p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-title-md text-text-primary">
            Coverage by SOC 2 Trust Services Criteria
          </h2>
          <Button variant="link" size="sm">
            View controls
            <Icon name="arrowr" className="size-4" />
          </Button>
        </div>
        <div className="space-y-3">
          {TSC.map((row) => (
            <div key={row.name} className="flex items-center gap-3">
              <span className="w-56 shrink-0 truncate text-body-md text-text-secondary">{row.name}</span>
              <div className="flex h-2.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                <div style={{ width: `${(row.have / row.total) * 100}%`, background: TOKEN.green }} />
                <div style={{ width: `${(row.review / row.total) * 100}%`, background: TOKEN.amber }} />
                <div style={{ width: `${(row.fail / row.total) * 100}%`, background: TOKEN.red }} />
              </div>
              <span className="tabular w-14 shrink-0 text-right text-body-sm text-text-subtle">
                {row.have}/{row.total}
              </span>
              <span className="tabular w-10 shrink-0 text-right text-body-md font-semibold text-text-primary">
                {row.pct}%
              </span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center gap-4 border-t border-border pt-3 text-body-sm text-text-subtle">
          <Legend color={TOKEN.green} label="Passing" />
          <Legend color={TOKEN.amber} label="Needs review" />
          <Legend color={TOKEN.red} label="Failing" />
        </div>
      </Card>

      {/* Supporting tiles. Every card spans one column so the grid closes into
          even rows — the old layout left a hole beside the last tile. */}
      <div className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {/* Vulnerabilities — multi-segment donut */}
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-title-sm text-text-primary">Vulnerabilities</h3>
            <Icon name="bug" className="size-4 text-status-danger-text" />
          </div>
          <div className="flex items-center gap-4">
            <Donut size={88} stroke={12} segments={VULN_SEGMENTS}>
              <span className="font-display text-numeral-md tabular text-text-primary">64</span>
            </Donut>
            <div className="flex-1 space-y-1 text-body-sm">
              {VULN_SEGMENTS.map((v) => (
                <div key={v.label} className="flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-text-secondary">
                    <span className="size-2 rounded-full" style={{ background: v.color }} />
                    {v.label}
                  </span>
                  <span className="tabular font-medium text-text-primary">{v.value}</span>
                </div>
              ))}
            </div>
          </div>
          <p className="mt-3 text-body-sm text-status-danger-text">2 on CISA KEV · 3 past SLA</p>
        </Card>

        {/* Evidence — green donut */}
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-title-sm text-text-primary">Evidence</h3>
            <Icon name="doc" className="size-4 text-text-secondary" />
          </div>
          <div className="flex items-center gap-4">
            <Donut size={88} stroke={12} segments={ring(78, TOKEN.green)}>
              <span className="font-display text-numeral-md tabular text-text-primary">78%</span>
            </Donut>
            <div>
              <p className="font-display text-numeral-lg tabular text-text-primary">842</p>
              <p className="text-body-sm text-text-subtle">total items</p>
              <p className="text-body-sm text-text-subtle">73% auto-collected</p>
            </div>
          </div>
          <p className="mt-3 text-body-sm text-status-warning-text">19 expiring · 6 expired</p>
        </Card>

        {/* Risk register — heatmap */}
        <Card className="p-5">
          <h3 className="mb-3 flex items-center gap-2 font-display text-title-sm text-text-primary">
            <Icon name="risk" className="size-4 text-text-secondary" />
            Risk register
          </h3>
          <div className="flex items-center gap-4">
            <div className="grid grid-cols-5 gap-1">
              {HEAT.map((rowArr, r) =>
                rowArr.map((count, c) => (
                  <span
                    key={`${r}-${c}`}
                    className={cn(
                      "flex size-6 items-center justify-center rounded-xs text-caption font-semibold text-text-primary",
                      heatColor(r, c),
                    )}
                  >
                    {count > 0 ? count : ""}
                  </span>
                )),
              )}
            </div>
            <div>
              <p className="font-display text-numeral-lg tabular text-text-primary">12</p>
              <p className="mb-2 text-caption text-text-subtle">active risks</p>
              <div className="space-y-1 text-body-sm">
                <div className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-status-danger-base" />High residual <span className="tabular ml-auto font-medium">3</span></div>
                <div className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-status-warning-base" />Medium <span className="tabular ml-auto font-medium">7</span></div>
                <div className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-status-success-base" />Low · treated <span className="tabular ml-auto font-medium">2</span></div>
              </div>
            </div>
          </div>
          <p className="mt-3 text-caption text-text-subtle">Likelihood × impact</p>
        </Card>

        {/* Assets — coloured category bars */}
        <Card className="p-5">
          <h3 className="mb-1 flex items-center gap-2 font-display text-title-sm text-text-primary">
            <Icon name="box" className="size-4 text-text-secondary" />
            Assets
          </h3>
          <p className="mt-1 font-display text-numeral-lg tabular text-text-primary">1,284</p>
          <p className="text-body-sm text-text-subtle">auto-discovered</p>
          <div className="mt-3 space-y-2">
            {ASSETS.map((a) => (
              <div key={a.label}>
                <div className="flex justify-between text-body-sm">
                  <span className="text-text-secondary">{a.label}</span>
                  <span className="tabular font-medium text-text-primary">{a.value.toLocaleString()}</span>
                </div>
                <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-sunken">
                  <div className="h-full rounded-full" style={{ width: `${(a.value / assetMax) * 100}%`, background: a.color }} />
                </div>
              </div>
            ))}
          </div>
        </Card>

        {/* Top risks — one column like the rest, so the row closes evenly. */}
        <Card className="p-5">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-display text-title-sm text-text-primary">Top risks</h3>
            <Button variant="link" size="sm">
              All
              <Icon name="arrowr" className="size-4" />
            </Button>
          </div>
          <ul className="divide-y divide-border">
            {TOP_RISKS.map((risk) => (
              <li key={risk.title} className="flex items-center gap-2.5 py-2">
                <span
                  className={cn(
                    "flex size-8 shrink-0 items-center justify-center rounded-md font-display text-body-md font-bold",
                    riskScoreTone(risk.score),
                  )}
                >
                  {risk.score}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-body-sm font-medium text-text-primary">
                    {risk.title}
                  </p>
                  <p className="text-caption text-text-subtle">{risk.ref}</p>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        {/* Policies */}
        <Card className="p-5">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-display text-title-sm text-text-primary">
              <Icon name="book" className="size-4 text-text-secondary" />
              Policies
            </h3>
            <span className="font-display text-numeral-md tabular text-text-primary">11/12</span>
          </div>
          <p className="text-body-sm text-text-subtle">current · 1 renewal overdue</p>
          <div className="mt-4 flex items-center justify-between text-body-sm">
            <span className="text-text-secondary">Acknowledged</span>
            <span className="tabular font-semibold text-status-success-text">93%</span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-sunken">
            <div className="h-full rounded-full bg-status-success-base" style={{ width: "93%" }} />
          </div>
        </Card>
      </div>
    </div>
  );
}

function MiniStat({ value, label, tone }: { value: string; label: string; tone?: string }) {
  return (
    <div>
      <p className={cn("font-display text-numeral-sm tabular", tone ?? "text-text-primary")}>{value}</p>
      <p className="text-caption text-text-subtle">{label}</p>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="size-2.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
