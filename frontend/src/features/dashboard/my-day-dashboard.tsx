import { useState } from "react";
import { Badge, Button, Card, ChartCard, Donut, Icon, SegmentedControl, StatTile, type StatTone } from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";

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

const OPEN_WORK = [
  { key: "vulns", label: "Vulnerabilities", value: 9, strokeClass: "stroke-status-danger-base", dotClass: "bg-status-danger-base" },
  { key: "controls", label: "Controls", value: 8, strokeClass: "stroke-action-accent", dotClass: "bg-action-accent" },
  { key: "access", label: "Access & reviews", value: 6, strokeClass: "stroke-status-pending-base", dotClass: "bg-status-pending-base" },
  { key: "evidence", label: "Evidence & docs", value: 4, strokeClass: "stroke-status-warning-base", dotClass: "bg-status-warning-base" },
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

const STATS: { value: number; label: string; icon: IconName; tone: StatTone }[] = [
  { value: 3, label: "Overdue", icon: "alert", tone: "danger" },
  { value: 5, label: "Due today", icon: "clock", tone: "warning" },
  { value: 27, label: "My open tasks", icon: "list", tone: "progress" },
  { value: 8, label: "Awaiting review", icon: "audit", tone: "neutral" },
  { value: 12, label: "Closed this week", icon: "check", tone: "success" },
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
          <StatTile key={s.label} icon={s.icon} label={s.label} value={s.value} tone={s.tone} />
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
          <ChartCard title="My open work">
            <Donut segments={OPEN_WORK} size={160} centerValue={27} centerLabel="Open" />
          </ChartCard>

          {/* Vulnerability SLA countdown */}
          <ChartCard
            title="Vulnerability SLA countdown"
            action={
              <Button variant="link" size="sm" className="shrink-0">
                All
                <Icon name="arrowr" className="size-4" />
              </Button>
            }
          >
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
          </ChartCard>

          {/* Upcoming deadlines */}
          <ChartCard
            title="Upcoming deadlines"
            action={
              <Button variant="link" size="sm">
                Calendar
                <Icon name="arrowr" className="size-4" />
              </Button>
            }
          >
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
          </ChartCard>
        </div>
      </div>
    </div>
  );
}
