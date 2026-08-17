import { Badge, Button, Card, Icon } from "@/components/ui";
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
  action: string;
};

const TASKS: Task[] = [
  { title: "Remediate CVE-2026-1284 on prod-api-gateway", module: "Vuln", detail: "CVSS 9.8 · CISA KEV · openssl 3.0.11", due: "Overdue 2d", overdue: true, action: "Fix" },
  { title: "Restore SIEM log forwarding for CC7.2", module: "Control", detail: "3 of 15 hosts not reporting", due: "Overdue 3d", overdue: true, action: "Open" },
  { title: "Certify Q3 access review — Engineering", module: "Access", detail: "24 accounts · Okta", due: "Due today", action: "Review" },
  { title: "Enforce TLS 1.2+ on 2 public endpoints (CC6.6)", module: "Control", detail: "api-gateway, cdn-edge", due: "Due today", action: "Fix" },
  { title: "Re-upload AWS Config export for CC6.1", module: "Evidence", detail: "Auto-collection expiring", due: "in 2d", action: "Upload" },
  { title: "Reassess Tier-1 vendor: Datadog", module: "Vendor", detail: "Annual review overdue 189d", due: "in 4d", action: "Start" },
  { title: "Approve Data Retention Policy renewal", module: "Policy", detail: "v2.0 → v2.1", due: "in 6d", action: "Review" },
];

const OPEN_WORK = [
  { label: "Vulnerabilities", value: 9 },
  { label: "Controls", value: 8 },
  { label: "Access & reviews", value: 6 },
  { label: "Evidence & docs", value: 4 },
];

// Each CVE's remediation window: negative days left = overdue. `pct` fills the
// bar as the window burns down.
const SLA = [
  { cve: "CVE-2026-1284", label: "4d overdue", pct: 100, overdue: true },
  { cve: "CVE-2024-3094", label: "2d left", pct: 92 },
  { cve: "CVE-2026-0331", label: "11d left", pct: 64 },
  { cve: "CVE-2024-21762", label: "20d left", pct: 45 },
  { cve: "CVE-2026-1777", label: "26d left", pct: 32 },
  { cve: "CVE-2024-6387", label: "31d left", pct: 20 },
];

const DEADLINES = [
  { d: "23", m: "JUL", title: "Q3 access review closes", detail: "Engineering · 24 to certify" },
  { d: "25", m: "JUL", title: "AWS Config evidence expires", detail: "CC6.1" },
  { d: "29", m: "JUL", title: "Vendor reassessment — Datadog", detail: "TPRM Tier 1" },
  { d: "01", m: "AUG", title: "Monthly control test cycle", detail: "218 automated checks" },
  { d: "15", m: "SEP", title: "SOC 2 observation window closes", detail: "Audit · Brenner & Associates" },
];

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function Stat({ value, label, tone }: { value: number; label: string; tone?: string }) {
  return (
    <div className="flex flex-col rounded-lg border border-border bg-surface-primary px-4 py-3">
      <span className={cn("font-display text-numeral-lg tabular", tone ?? "text-text-primary")}>
        {value}
      </span>
      <span className="mt-0.5 text-body-sm text-text-subtle">{label}</span>
    </div>
  );
}

export function MyDayDashboard() {
  const { principal } = useAuth();
  const firstName = (principal?.user.full_name ?? "there").split(" ")[0];

  return (
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-heading-lg text-text-primary">
        {greeting()}, {firstName}
      </h1>
      <p className="mt-2 text-body-lg text-text-secondary">
        You have <span className="font-semibold text-status-danger-text">3 items overdue</span> and{" "}
        <span className="font-semibold text-text-primary">5 due today</span> across 4 modules. Here&rsquo;s your day.
      </p>

      <div className="mb-6 mt-5 flex items-center justify-between gap-3">
        <p className="type-overline text-text-subtle">My board</p>
        <Button size="sm">
          <Icon name="plus" className="size-4" />
          New task
        </Button>
      </div>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Stat value={3} label="Overdue" tone="text-status-danger-text" />
        <Stat value={5} label="Due today" tone="text-status-warning-text" />
        <Stat value={27} label="My open tasks" />
        <Stat value={8} label="Awaiting review" />
        <Stat value={12} label="Closed this week" tone="text-status-success-text" />
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
                      "shrink-0 whitespace-nowrap text-body-sm font-medium",
                      task.overdue ? "text-status-danger-text" : "text-text-subtle",
                    )}
                  >
                    {task.due}
                  </span>
                  <Button variant="secondary" size="sm" className="shrink-0">
                    {task.action}
                  </Button>
                </li>
              );
            })}
          </ul>
        </Card>

        <div className="flex flex-col gap-6">
          {/* My open work */}
          <Card className="p-5">
            <div className="flex items-baseline justify-between">
              <h2 className="font-display text-title-md text-text-primary">My open work</h2>
              <span className="font-display text-numeral-md tabular text-text-primary">27</span>
            </div>
            <p className="mb-3 text-body-sm text-text-subtle">items open</p>
            <div className="space-y-2.5">
              {OPEN_WORK.map((row) => (
                <div key={row.label} className="flex items-center gap-3">
                  <span className="w-32 shrink-0 text-body-sm text-text-secondary">{row.label}</span>
                  <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                    <div
                      className="h-full rounded-full bg-action-accent"
                      style={{ width: `${(row.value / 9) * 100}%` }}
                    />
                  </div>
                  <span className="tabular w-5 text-right text-body-sm font-medium text-text-primary">
                    {row.value}
                  </span>
                </div>
              ))}
            </div>
          </Card>

          {/* Upcoming deadlines */}
          <Card className="p-5">
            <h2 className="mb-3 font-display text-title-md text-text-primary">Upcoming deadlines</h2>
            <ul className="space-y-3">
              {DEADLINES.map((item) => (
                <li key={item.title} className="flex items-center gap-3">
                  <span className="flex size-11 shrink-0 flex-col items-center justify-center rounded-md border border-border bg-surface-sunken leading-none">
                    <span className="font-display text-body-md font-bold text-text-primary">{item.d}</span>
                    <span className="mt-0.5 text-overline uppercase text-text-subtle">{item.m}</span>
                  </span>
                  <div className="min-w-0">
                    <p className="truncate text-body-md font-medium text-text-primary">{item.title}</p>
                    <p className="truncate text-body-sm text-text-subtle">{item.detail}</p>
                  </div>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      </div>

      {/* Vulnerability SLA countdown — full width */}
      <Card className="mt-6 p-5">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <h2 className="font-display text-title-md text-text-primary">Vulnerability SLA countdown</h2>
            <p className="mt-0.5 text-body-sm text-text-subtle">
              Bar fills as the remediation window burns down
            </p>
          </div>
        </div>
        <div className="space-y-3">
          {SLA.map((row) => (
            <div key={row.cve} className="flex items-center gap-3">
              <span className="tabular w-32 shrink-0 text-body-sm text-text-secondary">{row.cve}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-sunken">
                <div
                  className={cn(
                    "h-full rounded-full",
                    row.overdue
                      ? "bg-status-danger-base"
                      : row.pct > 80
                        ? "bg-status-warning-base"
                        : "bg-action-accent",
                  )}
                  style={{ width: `${row.pct}%` }}
                />
              </div>
              <span
                className={cn(
                  "w-20 shrink-0 text-right text-body-sm font-medium",
                  row.overdue ? "text-status-danger-text" : "text-text-subtle",
                )}
              >
                {row.label}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
