import { useState } from "react";
import { Badge, Button, Card, Icon, SegmentedControl } from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { Donut } from "./donut";

// Operations · My Day — the personal work queue for non-admin roles. Mock data
// mirrors the reference dashboard; a live backend replaces it module by module.

type Module = "Vuln" | "Control" | "Access" | "Evidence" | "Vendor" | "Policy";

const MODULE_META: Record<Module, { icon: IconName; tone: string }> = {
  Vuln: { icon: "bug", tone: "bg-status-danger-bg text-status-danger-text" },
  Control: { icon: "shield", tone: "bg-action-accent-tint text-action-accent" },
  Access: { icon: "users", tone: "bg-status-progress-bg text-status-progress-text" },
  Evidence: { icon: "doc", tone: "bg-status-pending-bg text-status-pending-text" },
  Vendor: { icon: "vendor", tone: "bg-status-warning-bg text-status-warning-text" },
  Policy: { icon: "book", tone: "bg-status-neutral-bg text-status-neutral-text" },
};

type Task = {
  title: string;
  module: Module;
  detail: string;
  due: string;
  overdue?: boolean;
  today?: boolean;
  action: string;
};

const TASKS: Task[] = [
  { title: "Remediate CVE-2026-1284 on prod-api-gateway", module: "Vuln", detail: "CVSS 9.8 · CISA KEV · openssl 3.0.11", due: "Overdue 2d", overdue: true, action: "Fix" },
  { title: "Restore SIEM log forwarding for CC7.2", module: "Control", detail: "3 of 15 hosts not reporting", due: "Overdue 3d", overdue: true, action: "Open" },
  { title: "Certify Q3 access review · Engineering", module: "Access", detail: "24 accounts · Okta", due: "Due today", today: true, action: "Review" },
  { title: "Enforce TLS 1.2+ on 2 public endpoints (CC6.6)", module: "Control", detail: "api-gateway, cdn-edge", due: "Due today", today: true, action: "Fix" },
  { title: "Re-upload AWS Config export for CC6.1", module: "Evidence", detail: "Auto-collection expiring", due: "in 2d", action: "Upload" },
  { title: "Reassess Tier-1 vendor: Datadog", module: "Vendor", detail: "Annual review overdue 189d", due: "in 4d", action: "Start" },
  { title: "Approve Data Retention Policy renewal", module: "Policy", detail: "v2.0 → v2.1", due: "in 6d", action: "Review" },
];

// Donut segments — colours match the reference legend (violet has no DS token).
const OPEN_WORK = [
  { label: "Vulnerabilities", value: 9, color: "rgb(var(--color-status-danger-base))" },
  { label: "Controls", value: 8, color: "rgb(var(--color-action-accent))" },
  { label: "Access & reviews", value: 6, color: "#8b5cf6" },
  { label: "Evidence & docs", value: 4, color: "rgb(var(--color-status-warning-base))" },
];

// left = days remaining in the remediation window; negative = overdue. Bar
// fills as the window burns down; colour steps red → orange → green by urgency.
const SLA = [
  { cve: "CVE-2026-1284", left: -4 },
  { cve: "CVE-2024-3094", left: 2 },
  { cve: "CVE-2026-0331", left: 11 },
  { cve: "CVE-2024-21762", left: 20 },
  { cve: "CVE-2026-1777", left: 26 },
  { cve: "CVE-2024-6387", left: 31 },
];

function slaRow(left: number) {
  if (left < 0) return { label: `${-left}d overdue`, pct: 100, color: "rgb(var(--color-status-danger-base))", danger: true };
  const pct = Math.max(14, 96 - left * 2.5);
  const color = left <= 12 ? "#f97316" : "rgb(var(--color-status-success-base))";
  return { label: `${left}d left`, pct, color, danger: false };
}

const DEADLINES = [
  { d: "23", m: "JUL", title: "Q3 access review closes", detail: "Engineering · 24 to certify", dot: "bg-status-danger-base" },
  { d: "25", m: "JUL", title: "AWS Config evidence expires", detail: "CC6.1", dot: "bg-status-warning-base" },
  { d: "29", m: "JUL", title: "Vendor reassessment · Datadog", detail: "TPRM Tier 1", dot: "bg-status-warning-base" },
  { d: "01", m: "AUG", title: "Monthly control test cycle", detail: "218 automated checks", dot: "bg-action-accent" },
  { d: "15", m: "SEP", title: "SOC 2 observation window closes", detail: "Audit · Brenner & Associates", dot: "bg-action-accent" },
];

const STATS = [
  { value: 3, label: "Overdue", num: "text-status-danger-text", bar: "bg-status-danger-base" },
  { value: 5, label: "Due today", num: "text-status-warning-text", bar: "bg-status-warning-base" },
  { value: 27, label: "My open tasks", num: "text-text-primary", bar: "bg-action-accent" },
  { value: 8, label: "Awaiting review", num: "text-text-primary", bar: "bg-status-progress-base" },
  { value: 12, label: "Closed this week", num: "text-status-success-text", bar: "bg-status-success-base" },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function dueTone(task: Task): string {
  if (task.overdue) return "bg-status-danger-bg text-status-danger-text";
  if (task.today) return "bg-status-warning-bg text-status-warning-text";
  return "bg-status-neutral-bg text-status-neutral-text";
}

export function MyDayDashboard() {
  const { principal } = useAuth();
  const firstName = (principal?.user.full_name ?? "there").split(" ")[0];
  const [scope, setScope] = useState<"Mine" | "Team">("Mine");

  return (
    <div className="w-full">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {/* No summary line: the overdue and due-today counts it hardcoded are
              the first two tiles of the stat row directly below. */}
          <h1 className="font-display text-heading-lg text-text-primary">
            {greeting()}, {firstName}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" size="sm">
            <Icon name="grid" className="size-4" />
            My board
          </Button>
          <Button size="sm">
            <Icon name="plus" className="size-4" />
            New task
          </Button>
        </div>
      </div>

      {/* Stat row — colour-accented tiles */}
      <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {STATS.map((s) => (
          <div
            key={s.label}
            className="relative overflow-hidden rounded-lg border border-border bg-surface-primary px-4 py-3 pl-5"
          >
            <span className={cn("absolute inset-y-0 left-0 w-1", s.bar)} />
            <span className={cn("font-display text-numeral-lg tabular", s.num)}>{s.value}</span>
            <span className="mt-0.5 block text-body-sm text-text-subtle">{s.label}</span>
          </div>
        ))}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1.6fr_1fr]">
        {/* Needs your attention — the SLA-ranked queue */}
        <Card className="p-0">
          <div className="flex items-center justify-between gap-3 border-b border-border px-5 py-4">
            <div>
              <h2 className="font-display text-title-md text-text-primary">Needs your attention</h2>
              <p className="mt-0.5 text-body-sm text-text-subtle">
                Prioritized across every module · SLA-ranked
              </p>
            </div>
            <SegmentedControl
              label="Queue scope"
              value={scope}
              onChange={setScope}
              items={[
                { id: "Mine", label: "Mine" },
                { id: "Team", label: "Team" },
              ]}
            />
          </div>
          <ul className="divide-y divide-border">
            {TASKS.map((task) => {
              const meta = MODULE_META[task.module];
              return (
                <li key={task.title} className="flex items-center gap-3 px-5 py-3">
                  <span
                    className={cn(
                      "flex size-8 shrink-0 items-center justify-center rounded-md",
                      meta.tone,
                    )}
                  >
                    <Icon name={meta.icon} className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-body-md font-medium text-text-primary">
                      {task.title}
                    </p>
                    <p className="flex items-center gap-1.5 text-body-sm text-text-subtle">
                      <Badge variant="neutral">{task.module}</Badge>
                      <span className="truncate">{task.detail}</span>
                    </p>
                  </div>
                  <span
                    className={cn(
                      "inline-flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-caption font-medium",
                      dueTone(task),
                    )}
                  >
                    <Icon name="clock" className="size-3" />
                    {task.due}
                  </span>
                  <Button size="sm" className="shrink-0">
                    {task.action}
                  </Button>
                </li>
              );
            })}
          </ul>
        </Card>

        {/* Right rail */}
        <div className="flex flex-col gap-6">
          {/* My open work — donut + legend */}
          <Card className="p-5">
            {/* The count lives in the donut centre, so the heading does not
                repeat it. */}
            <h2 className="mb-4 font-display text-title-md text-text-primary">
              My open work
            </h2>
            <div className="flex items-center gap-5">
              <Donut size={116} stroke={16} segments={OPEN_WORK}>
                <span className="font-display text-numeral-lg tabular text-text-primary">27</span>
                <span className="mt-0.5 text-caption text-text-subtle">open</span>
              </Donut>
              <ul className="flex-1 space-y-2">
                {OPEN_WORK.map((w) => (
                  <li key={w.label} className="flex items-center gap-2 text-body-sm">
                    <span className="size-2.5 shrink-0 rounded-full" style={{ background: w.color }} />
                    <span className="flex-1 text-text-secondary">{w.label}</span>
                    <span className="tabular font-semibold text-text-primary">{w.value}</span>
                  </li>
                ))}
              </ul>
            </div>
          </Card>

          {/* Vulnerability SLA countdown */}
          <Card className="p-5">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <h2 className="font-display text-title-md text-text-primary">Vulnerability SLA countdown</h2>
                <p className="mt-0.5 text-body-sm text-text-subtle">
                  Bar fills as the remediation window burns down
                </p>
              </div>
              <Button variant="link" size="sm" className="shrink-0">
                All
                <Icon name="arrowr" className="size-4" />
              </Button>
            </div>
            <div className="space-y-2.5">
              {SLA.map((row) => {
                const r = slaRow(row.left);
                return (
                  <div key={row.cve} className="flex items-center gap-3">
                    <span className="tabular w-28 shrink-0 text-caption text-text-secondary">{row.cve}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                      <div className="h-full rounded-full" style={{ width: `${r.pct}%`, background: r.color }} />
                    </div>
                    <span
                      className={cn(
                        "w-20 shrink-0 text-right text-caption font-medium",
                        r.danger ? "text-status-danger-text" : "text-text-subtle",
                      )}
                    >
                      {r.label}
                    </span>
                  </div>
                );
              })}
            </div>
          </Card>

          {/* Upcoming deadlines */}
          <Card className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="font-display text-title-md text-text-primary">Upcoming deadlines</h2>
              <Button variant="link" size="sm">
                Calendar
                <Icon name="arrowr" className="size-4" />
              </Button>
            </div>
            <ul className="space-y-3">
              {DEADLINES.map((item) => (
                <li key={item.title} className="flex items-center gap-3">
                  <span className="flex size-11 shrink-0 flex-col items-center justify-center rounded-md border border-border bg-surface-sunken leading-none">
                    <span className="font-display text-body-md font-bold text-text-primary">{item.d}</span>
                    <span className="mt-0.5 text-overline uppercase text-text-subtle">{item.m}</span>
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-body-md font-medium text-text-primary">{item.title}</p>
                    <p className="truncate text-body-sm text-text-subtle">{item.detail}</p>
                  </div>
                  <span className={cn("size-2 shrink-0 rounded-full", item.dot)} />
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
