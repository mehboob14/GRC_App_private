import { useState } from "react";
import {
  BarList,
  Button,
  Card,
  ChartCard,
  ChartLegend,
  Donut,
  FAMILY_CHART,
  Icon,
  PageHeader,
  SegmentedControl,
  StatTile,
  StatusPill,
  statusFamilyFor,
  type ChartSegment,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";
import { Donut as Ring } from "./donut";

// A single-value progress ring, which the shared `Donut` (a distribution chart
// with its own legend) does not cover. `Ring` paints an SVG stroke, so its
// colour arrives as `currentColor` from a literal Tailwind `text-*` class on
// the wrapper. Tailwind's JIT scans source text, so a class assembled at
// runtime would be purged from the build.
const ring = (pct: number) => [
  { value: pct, color: "currentColor" },
  { value: 100 - pct, color: "transparent" },
];

// Admin posture dashboard: framework rings, TSC coverage and the posture
// tiles. Mock data until each module's backend lands.

/** Ring colours, as literal classes for the same JIT reason. */
const RING = {
  accent: "text-action-accent",
  success: "text-status-success-base",
  warning: "text-status-warning-base",
  danger: "text-status-danger-base",
} as const;

// ── Data ─────────────────────────────────────────────────────────────────
const FRAMEWORKS = [
  { name: "SOC 2 Type II", phase: "Type II window", status: "On track", pct: 91, pass: 124, fail: 3, review: 4, ring: RING.success },
  { name: "ISO 27001", phase: "Stage 2 · Nov", status: "At risk", pct: 78, pass: 74, fail: 6, review: 7, ring: RING.warning },
  { name: "HIPAA Security", phase: "Readiness Q1", status: "Behind", pct: 64, pass: 59, fail: 9, review: 11, ring: RING.danger },
];

// have = passing; the remainder splits into needs-review then failing.
const TSC = [
  { name: "Security (Common Criteria)", have: 88, total: 95, review: 5, fail: 2, pct: 93 },
  { name: "Availability", have: 7, total: 10, review: 2, fail: 1, pct: 70 },
  { name: "Confidentiality", have: 8, total: 8, review: 0, fail: 0, pct: 100 },
  { name: "Processing Integrity", have: 4, total: 6, review: 2, fail: 0, pct: 67 },
  { name: "Privacy", have: 5, total: 9, review: 2, fail: 2, pct: 56 },
];

// The severity axis (F12), not the status axis: "how bad", not "where in the
// lifecycle".
const VULN_SEGMENTS: ChartSegment[] = [
  { key: "critical", label: "Critical", value: 4, strokeClass: "stroke-severity-critical", dotClass: "bg-severity-critical" },
  { key: "high", label: "High", value: 5, strokeClass: "stroke-severity-high", dotClass: "bg-severity-high" },
  { key: "medium", label: "Medium", value: 4, strokeClass: "stroke-severity-medium", dotClass: "bg-severity-medium" },
  { key: "low", label: "Low", value: 1, strokeClass: "stroke-severity-low", dotClass: "bg-severity-low" },
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
  { key: "restricted", label: "Restricted", value: 24, barClass: "bg-severity-critical" },
  { key: "confidential", label: "Confidential", value: 162, barClass: "bg-severity-high" },
  { key: "internal", label: "Internal / Public", value: 1098, barClass: "bg-action-accent" },
];

function riskScoreTone(score: number): string {
  if (score >= 15) return "bg-status-danger-bg text-status-danger-text";
  if (score >= 10) return "bg-status-warning-bg text-status-warning-text";
  return "bg-status-progress-bg text-status-progress-text";
}

// Heatmap cell tone by severity rank (likelihood + impact). Solid bg/text
// token pairs rather than opacity: a translucent fill has no fixed contrast
// ratio, and the count sitting on it has to stay legible.
function heatTone(rowFromTop: number, col: number): string {
  const sev = (4 - rowFromTop) + col; // 0..8
  if (sev >= 6) return "bg-status-danger-bg text-status-danger-text";
  if (sev >= 4) return "bg-status-warning-bg text-status-warning-text";
  if (sev >= 2) return "bg-status-success-bg text-status-success-text";
  return "bg-surface-sunken text-text-subtle";
}

export function AdminDashboard() {
  const [range, setRange] = useState<"Live" | "Weekly">("Live");

  return (
    <div className="w-full">
      <PageHeader title="Compliance posture" />

      {/* The range switch governs the whole page, so it leads the page rather
          than sitting over one section of it. */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SegmentedControl
          label="Posture range"
          value={range}
          onChange={setRange}
          items={[
            { id: "Live", label: "Live" },
            { id: "Weekly", label: "Weekly" },
          ]}
        />
        <div className="flex flex-wrap items-center gap-3">
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

      <div className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile icon="controls" label="Controls" value={124} tone="progress" />
        <StatTile icon="doc" label="Evidence" value={842} tone="progress" />
        <StatTile icon="risk" label="Risks" value={12} tone="warning" />
        <StatTile icon="bug" label="Vulnerabilities" value={64} tone="danger" />
      </div>

      {/* SOC 2 readiness: the headline number, so it leads the page. */}
      <Card className="mt-4 p-5">
        <div className="flex flex-wrap items-center gap-6">
          <div className={cn("shrink-0", RING.accent)}>
            <Ring size={132} stroke={14} segments={ring(91)}>
              <span className="font-display text-numeral-lg tabular text-text-primary">91%</span>
              <span className="mt-1 text-caption text-action-accent">124 / 136 controls</span>
            </Ring>
          </div>
          <div className="min-w-[240px] flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-display text-title-md text-text-primary">SOC 2 Type II readiness</p>
              <span className="inline-flex items-center gap-0.5 rounded-full bg-status-success-bg px-2.5 py-1 text-caption font-bold text-status-success-text">
                <Icon name="arrowup" className="size-3.5" />
                +4%
              </span>
            </div>
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
      </Card>

      {/* Framework compliance cards: donut rings */}
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        {FRAMEWORKS.map((fw) => (
          <Card key={fw.name} className="p-4">
            <div className="flex items-center gap-2.5">
              {/* The framework's own mark, in the same contained treatment as
                  the sign-in marquee and the controls table. */}
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
              <div className={cn("shrink-0", fw.ring)}>
                <Ring size={92} stroke={11} segments={ring(fw.pct)}>
                  <span className="font-display text-numeral-md tabular text-text-primary">{fw.pct}%</span>
                </Ring>
              </div>
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

      {/* Coverage by SOC 2 Trust Services Criteria: stacked bars */}
      <ChartCard
        className="mt-4"
        title="Coverage by SOC 2 Trust Services Criteria"
        action={
          <Button variant="link" size="sm">
            View controls
            <Icon name="arrowr" className="size-4" />
          </Button>
        }
      >
        <ChartLegend
          className="mb-4"
          items={[
            { key: "passing", label: "Passing", swatchClass: FAMILY_CHART.success.dot },
            { key: "review", label: "Needs review", swatchClass: FAMILY_CHART.warning.dot },
            { key: "failing", label: "Failing", swatchClass: FAMILY_CHART.danger.dot },
          ]}
        />
        <div className="space-y-3">
          {TSC.map((row) => (
            <div key={row.name} className="flex items-center gap-3">
              <span className="w-56 shrink-0 truncate text-body-md text-text-secondary">{row.name}</span>
              <div className="flex h-2.5 flex-1 gap-0.5 overflow-hidden rounded-full bg-surface-sunken">
                <div className={FAMILY_CHART.success.bar} style={{ width: `${(row.have / row.total) * 100}%` }} />
                <div className={FAMILY_CHART.warning.bar} style={{ width: `${(row.review / row.total) * 100}%` }} />
                <div className={FAMILY_CHART.danger.bar} style={{ width: `${(row.fail / row.total) * 100}%` }} />
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
      </ChartCard>

      {/* Supporting tiles. Every card spans one column so the grid closes into
          even rows. */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <ChartCard title="Vulnerabilities">
          <Donut segments={VULN_SEGMENTS} size={150} thickness={16} centerValue={64} />
          <p className="mt-3 text-center text-body-sm text-status-danger-text">2 on CISA KEV · 3 past SLA</p>
        </ChartCard>

        <ChartCard title="Evidence">
          <div className="flex flex-col items-center gap-3">
            <div className={cn("shrink-0", RING.success)}>
              <Ring size={132} stroke={16} segments={ring(78)}>
                <span className="font-display text-numeral-md tabular text-text-primary">78%</span>
                <span className="text-caption text-text-subtle">current</span>
              </Ring>
            </div>
            <p className="text-center text-body-sm text-text-secondary">
              <span className="tabular font-semibold text-text-primary">842</span> items, 73% auto-collected
            </p>
            <p className="text-center text-body-sm text-status-warning-text">19 expiring · 6 expired</p>
          </div>
        </ChartCard>

        <ChartCard title="Risk register">
          <div className="flex items-center justify-center gap-5">
            <div className="grid grid-cols-5 gap-1">
              {HEAT.map((rowArr, r) =>
                rowArr.map((count, c) => (
                  <span
                    key={`${r}-${c}`}
                    className={cn(
                      "flex size-7 items-center justify-center rounded-xs text-caption font-semibold",
                      heatTone(r, c),
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
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-2xs bg-status-danger-base" />High residual <span className="tabular ml-auto font-medium">3</span></div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-2xs bg-status-warning-base" />Medium <span className="tabular ml-auto font-medium">7</span></div>
                <div className="flex items-center gap-1.5"><span className="h-2.5 w-4 rounded-2xs bg-status-success-base" />Low · treated <span className="tabular ml-auto font-medium">2</span></div>
              </div>
            </div>
          </div>
          <p className="mt-3 text-center text-caption text-text-subtle">Likelihood × impact</p>
        </ChartCard>

        <ChartCard title="Assets">
          <p className="text-center">
            <span className="font-display text-numeral-lg tabular text-text-primary">1,284</span>
            <span className="ml-1.5 text-body-sm text-text-subtle">auto-discovered</span>
          </p>
          <div className="mt-4">
            <BarList items={ASSETS} />
          </div>
        </ChartCard>

        <ChartCard
          title="Top risks"
          action={
            <Button variant="link" size="sm">
              All
              <Icon name="arrowr" className="size-4" />
            </Button>
          }
        >
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
        </ChartCard>

        <ChartCard title="Policies">
          <p className="text-center">
            <span className="font-display text-numeral-lg tabular text-text-primary">11/12</span>
            <span className="ml-1.5 text-body-sm text-text-subtle">current</span>
          </p>
          <p className="text-center text-body-sm text-status-warning-text">1 renewal overdue</p>
          <div className="mt-5 flex items-center justify-between text-body-sm">
            <span className="text-text-secondary">Acknowledged</span>
            <span className="tabular font-semibold text-status-success-text">93%</span>
          </div>
          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-surface-sunken">
            <div className="h-full rounded-full bg-status-success-base" style={{ width: "93%" }} />
          </div>
        </ChartCard>
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
