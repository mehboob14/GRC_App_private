import { useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Icon,
  type IconName,
  Skeleton,
  useToast,
} from "@/components/ui";
import { Donut } from "@/features/dashboard/donut";
import { controlsApi, engagementApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { cn } from "@/lib/cn";
import type {
  ActivityItem,
  EvidenceFreshness,
  TimelinePoint,
} from "@/lib/api/types";

/**
 * The compliance dashboard — one honest read across frameworks, controls and
 * evidence. Every figure is measured; nothing is estimated, and where the
 * platform cannot yet measure something (automated checks need a connector) the
 * panel says so rather than showing a zero that reads as a finding.
 *
 * Every chart is a way into the control library: a slice, a bar, or an owner
 * links through to /controls with exactly that filter applied.
 *
 * Coverage and readiness are deliberately different numbers. Coverage asks only
 * whether a control exists for a criterion; readiness asks whether it is
 * implemented and currently evidenced. A fully adopted but unworked library
 * reads high on the first and near-zero on the second.
 */

function pct(part: number, whole: number): number {
  return whole === 0 ? 0 : Math.round((part / whole) * 100);
}

const BAND_FILL: Record<string, string> = {
  success: "rgb(var(--color-status-success-base))",
  warning: "rgb(var(--color-status-warning-base))",
  danger: "rgb(var(--color-status-danger-base))",
  accent: "rgb(var(--color-action-accent))",
  neutral: "rgb(var(--color-status-neutral-base))",
};
const BAND_TEXT: Record<string, string> = {
  success: "text-status-success-text",
  warning: "text-status-warning-text",
  danger: "text-status-danger-text",
};

const STATUS_META: Record<string, { label: string; color: string }> = {
  implemented: {
    label: "Implemented",
    color: "rgb(var(--color-status-success-base))",
  },
  in_progress: {
    label: "In progress",
    color: "rgb(var(--color-action-accent))",
  },
  not_started: {
    label: "Not started",
    color: "rgb(var(--color-status-neutral-base))",
  },
  not_applicable: {
    label: "Not applicable",
    color: "rgb(var(--color-border-strong))",
  },
};

const FRESHNESS_FILL: Record<EvidenceFreshness, string> = {
  current: "rgb(var(--color-status-success-base))",
  aging: "rgb(var(--color-status-warning-base))",
  stale: "rgb(var(--color-status-danger-base))",
  no_expiry: "rgb(var(--color-status-neutral-base))",
};

const CATEGORY_ICON: Record<string, IconName> = {
  Security: "shield",
  Availability: "activity",
  Confidentiality: "book",
  "Processing Integrity": "controls",
  Privacy: "users",
};

const ACTION_VERB: Record<string, string> = {
  create: "added",
  update: "updated",
  disable: "disabled",
  enable: "re-enabled",
  delete: "removed",
};
const ACTION_DOT: Record<string, string> = {
  create: "bg-status-success-base",
  enable: "bg-status-success-base",
  update: "bg-action-accent",
  disable: "bg-status-neutral-base",
  delete: "bg-status-danger-base",
};

function relativeTime(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 90) return "just now";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.round(h / 24);
  if (d < 30) return `${d}d ago`;
  const mo = Math.round(d / 30);
  if (mo < 12) return `${mo}mo ago`;
  return `${Math.round(mo / 12)}y ago`;
}

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? "";
  const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? "") : "";
  return (first + last).toUpperCase() || "?";
}

// --- primitives -------------------------------------------------------------

function Card({
  title,
  meta,
  action,
  children,
  className,
}: {
  title?: string;
  meta?: React.ReactNode;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-surface-primary p-5",
        className,
      )}
    >
      {title || action ? (
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-baseline gap-2">
            {title ? <p className="type-overline">{title}</p> : null}
            {meta ? (
              <span className="text-body-sm text-text-subtle">{meta}</span>
            ) : null}
          </div>
          {action}
        </div>
      ) : null}
      {children}
    </div>
  );
}

function Meter({
  value,
  total,
  fill,
}: {
  value: number;
  total: number;
  fill: string;
}) {
  return (
    <span className="block h-[7px] w-full overflow-hidden rounded-full border border-border bg-surface-sunken">
      <span
        className="block h-full rounded-full transition-[width] duration-150 ease-state motion-reduce:transition-none"
        style={{ width: `${pct(value, total)}%`, backgroundColor: fill }}
      />
    </span>
  );
}

/** A single-value ring with a percentage centre and a caption beneath. */
function Ring({
  value,
  total,
  color,
  caption,
}: {
  value: number;
  total: number;
  color: string;
  caption: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <Donut
        size={104}
        stroke={12}
        segments={[
          { value, color },
          { value: Math.max(total - value, 0), color: "transparent" },
        ]}
      >
        <span className="font-display text-numeral-md tabular text-text-primary">
          {pct(value, total)}
          <span className="text-body-md text-text-subtle">%</span>
        </span>
      </Donut>
      <p className="text-body-sm text-text-secondary">{caption}</p>
    </div>
  );
}

// --- timeline chart ---------------------------------------------------------

const CHART_W = 720;
const CHART_H = 200;
const PAD = { top: 12, right: 16, bottom: 26, left: 34 };
const MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(" ");

function shortDate(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return `${MONTHS[m - 1]} ${d}`;
}

function TimelineChart({ points }: { points: TimelinePoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const inner = {
    w: CHART_W - PAD.left - PAD.right,
    h: CHART_H - PAD.top - PAD.bottom,
  };
  const rawMax = Math.max(1, ...points.map((p) => Math.max(p.controls, p.evidence)));
  const step = Math.max(1, Math.ceil(rawMax / 4));
  const max = step * 4;
  const n = points.length;
  const x = (i: number) =>
    PAD.left + (n <= 1 ? inner.w / 2 : (i / (n - 1)) * inner.w);
  const y = (v: number) => PAD.top + inner.h - (v / max) * inner.h;

  const line = (key: "controls" | "evidence") =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p[key])}`).join(" ");
  const area = (key: "controls" | "evidence") =>
    `${line(key)} L${x(n - 1)},${PAD.top + inner.h} L${x(0)},${PAD.top + inner.h} Z`;

  const ticks = [0, 1, 2, 3, 4].map((k) => k * step);
  const labelEvery = Math.max(1, Math.ceil(n / 6));

  function onMove(e: React.MouseEvent) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const vbX = ((e.clientX - rect.left) / rect.width) * CHART_W;
    let best = 0;
    let bd = Infinity;
    points.forEach((_, i) => {
      const d = Math.abs(x(i) - vbX);
      if (d < bd) {
        bd = d;
        best = i;
      }
    });
    setHover(best);
  }

  const hp = hover !== null ? points[hover] : null;

  return (
    <div className="relative">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${CHART_W} ${CHART_H}`}
        className="w-full"
        role="img"
        aria-label="Controls adopted and evidence collected over time"
        onMouseMove={onMove}
        onMouseLeave={() => setHover(null)}
      >
        {ticks.map((t) => (
          <g key={t}>
            <line
              x1={PAD.left}
              y1={y(t)}
              x2={CHART_W - PAD.right}
              y2={y(t)}
              stroke="rgb(var(--color-border-default))"
              strokeWidth={1}
              opacity={t === 0 ? 1 : 0.5}
            />
            <text
              x={PAD.left - 6}
              y={y(t) + 3}
              textAnchor="end"
              className="fill-text-subtle text-[10px] tabular"
            >
              {t}
            </text>
          </g>
        ))}
        <path d={area("evidence")} fill="rgb(var(--color-action-accent) / 0.10)" />
        <path
          d={line("controls")}
          fill="none"
          stroke="rgb(var(--color-status-neutral-base))"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        <path
          d={line("evidence")}
          fill="none"
          stroke="rgb(var(--color-action-accent))"
          strokeWidth={2}
          strokeLinejoin="round"
        />
        {points.map((p, i) =>
          i % labelEvery === 0 || i === n - 1 ? (
            <text
              key={p.on}
              x={x(i)}
              y={CHART_H - 8}
              textAnchor={i === 0 ? "start" : i === n - 1 ? "end" : "middle"}
              className="fill-text-subtle text-[10px]"
            >
              {shortDate(p.on)}
            </text>
          ) : null,
        )}
        {hp && hover !== null ? (
          <g>
            <line
              x1={x(hover)}
              y1={PAD.top}
              x2={x(hover)}
              y2={PAD.top + inner.h}
              stroke="rgb(var(--color-border-strong))"
              strokeWidth={1}
            />
            <circle
              cx={x(hover)}
              cy={y(hp.controls)}
              r={3.5}
              fill="rgb(var(--color-surface-primary))"
              stroke="rgb(var(--color-status-neutral-base))"
              strokeWidth={2}
            />
            <circle
              cx={x(hover)}
              cy={y(hp.evidence)}
              r={3.5}
              fill="rgb(var(--color-surface-primary))"
              stroke="rgb(var(--color-action-accent))"
              strokeWidth={2}
            />
          </g>
        ) : null}
      </svg>
      {hp && hover !== null ? (
        <div
          className="pointer-events-none absolute top-0 z-10 -translate-x-1/2 rounded-md border border-border bg-surface-primary px-2.5 py-1.5 shadow-2"
          style={{ left: `${(x(hover) / CHART_W) * 100}%` }}
        >
          <p className="text-caption font-semibold text-text-primary">
            {shortDate(hp.on)}
          </p>
          <p className="mt-0.5 flex items-center gap-1.5 text-caption text-text-secondary">
            <span className="inline-block size-2 rounded-full bg-action-accent" />
            {hp.evidence} evidence
          </p>
          <p className="flex items-center gap-1.5 text-caption text-text-secondary">
            <span className="inline-block size-2 rounded-full bg-status-neutral-base" />
            {hp.controls} controls
          </p>
        </div>
      ) : null}
      <div className="mt-2 flex items-center gap-4">
        <span className="flex items-center gap-1.5 text-body-sm text-text-secondary">
          <span className="inline-block h-[2px] w-4 rounded bg-action-accent" />
          Evidence collected
        </span>
        <span className="flex items-center gap-1.5 text-body-sm text-text-secondary">
          <span className="inline-block h-[2px] w-4 rounded bg-status-neutral-base" />
          Controls adopted
        </span>
      </div>
    </div>
  );
}

// --- activity feed ----------------------------------------------------------

function ActivityRow({ item }: { item: ActivityItem }) {
  const verb = ACTION_VERB[item.action] ?? item.action;
  const who = item.actor_name ?? "System";
  return (
    <li className="flex items-start gap-3 border-t border-border py-2.5 first:border-t-0">
      <span
        className={cn(
          "mt-1.5 size-2 shrink-0 rounded-full",
          ACTION_DOT[item.action] ?? "bg-action-accent",
        )}
      />
      <span className="min-w-0 flex-1 text-body-sm text-text-secondary">
        <span className="font-semibold text-text-primary">{who}</span> {verb}{" "}
        {item.control_code ? (
          <span className="font-display font-semibold text-text-primary">
            {item.control_code}
          </span>
        ) : (
          "a control"
        )}
        {item.control_name ? (
          <span className="text-text-subtle"> · {item.control_name}</span>
        ) : null}
      </span>
      <span className="shrink-0 text-body-sm tabular text-text-subtle">
        {relativeTime(item.occurred_at)}
      </span>
    </li>
  );
}

// --- page -------------------------------------------------------------------

export function ComplianceDashboardPage() {
  const { principal } = useAuth();
  const tenantId = principal?.tenant_id;
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [range, setRange] = useState<{ from?: string; to?: string }>({});

  const query = useQuery({
    queryKey: ["compliance-dashboard", tenantId, range.from, range.to],
    queryFn: () => engagementApi.dashboard(range),
  });
  const data = query.data;

  const enableMutation = useMutation({
    mutationFn: (id: string) => controlsApi.enable(id),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["compliance-dashboard"] });
      void queryClient.invalidateQueries({ queryKey: ["controls"] });
      toast({ title: "Control re-enabled", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "control"), tone: "danger" }),
  });

  const statusSegments = useMemo(
    () =>
      (data?.by_status ?? []).map((row) => ({
        value: row.count,
        color:
          STATUS_META[row.status]?.color ?? "rgb(var(--color-border-strong))",
      })),
    [data?.by_status],
  );

  if (query.isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-40 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }
  if (query.isError) {
    const failure = describeError(query.error, "dashboard");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void query.refetch() : undefined}
      />
    );
  }
  if (!data) return null;

  if (!data.has_engagement) {
    return (
      <EmptyState
        icon="shield"
        title="Set your audit scope first"
        description="The dashboard measures your workspace against the criteria your engagement covers. Choose an audit type and its Trust Services categories, and this fills in."
        action={
          <Link
            to="/frameworks/scope"
            className="text-body-md font-semibold text-text-link"
          >
            Go to Scope
          </Link>
        }
      />
    );
  }

  const auditTypeLabel =
    data.audit_type === "type_2"
      ? "Type II"
      : data.audit_type === "type_1"
        ? "Type I"
        : "";
  const categories = data.by_category.map((c) => c.category);
  const total = data.controls_total;
  const remaining = Math.max(
    total - data.controls_ready - data.controls_in_progress,
    0,
  );
  const ownerMax = Math.max(1, ...data.by_owner.map((o) => o.count));
  const today = data.timeline_to;
  const evidencedControls = data.controls_evidenced;

  return (
    <div className="space-y-4">
      {/* Framework progress */}
      <Card title="Framework progress">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-center">
          <div className="flex shrink-0 items-center gap-5">
            <Donut
              size={132}
              stroke={13}
              segments={[
                {
                  value: data.criteria_covered,
                  color: "rgb(var(--color-action-accent))",
                },
                {
                  value: Math.max(data.criteria_total - data.criteria_covered, 0),
                  color: "transparent",
                },
              ]}
            >
              <span className="font-display text-numeral-lg tabular text-text-primary">
                {pct(data.criteria_covered, data.criteria_total)}
                <span className="text-numeral-sm text-text-subtle">%</span>
              </span>
              <span className="type-overline mt-0.5">Coverage</span>
            </Donut>
            <div>
              <p className="font-display text-heading-sm text-text-primary">
                {data.framework_name ?? "Framework"}{" "}
                {auditTypeLabel ? (
                  <span className="text-text-secondary">{auditTypeLabel}</span>
                ) : null}
              </p>
              <p className="mt-0.5 text-body-sm text-text-subtle">
                {categories.length > 0 ? categories.join(" · ") : "No scope set"}
              </p>
              <div className="mt-4 flex gap-6">
                {[
                  ["In scope", data.criteria_total],
                  ["Ready", data.controls_ready],
                  ["Evidence", data.evidence_total],
                ].map(([label, value]) => (
                  <div key={label}>
                    <p className="font-display text-numeral-sm tabular text-text-primary">
                      {value}
                    </p>
                    <p className="text-body-sm text-text-subtle">{label}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="min-w-0 flex-1 lg:border-l lg:border-border lg:pl-6">
            <div className="mb-2 flex items-baseline justify-between">
              <p className="text-body-sm text-text-secondary">Audit readiness</p>
              <p className="text-body-sm tabular text-text-subtle">
                {data.controls_ready} ready · {remaining} to go
              </p>
            </div>
            <div className="flex h-2.5 gap-0.5 overflow-hidden rounded-full">
              {[
                { value: data.controls_ready, fill: BAND_FILL.success },
                { value: data.controls_in_progress, fill: BAND_FILL.accent },
                { value: remaining, fill: "rgb(var(--color-surface-sunken))" },
              ]
                .filter((s) => s.value > 0)
                .map((s, i) => (
                  <span
                    key={i}
                    className="h-full"
                    style={{
                      width: `${(s.value / Math.max(total, 1)) * 100}%`,
                      backgroundColor: s.fill,
                    }}
                  />
                ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-5 gap-y-1.5">
              <LegendDot color={BAND_FILL.success} label="Ready" value={data.controls_ready} />
              <LegendDot color={BAND_FILL.accent} label="In progress" value={data.controls_in_progress} />
              <LegendDot color="rgb(var(--color-status-neutral-base))" label="Remaining" value={remaining} />
            </div>
          </div>
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Controls by status */}
        <Card title="Controls by status" meta={`${total} in scope`}>
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <Donut size={124} stroke={16} segments={statusSegments}>
              <span className="font-display text-numeral-md tabular text-text-primary">
                {total}
              </span>
              <span className="text-body-sm text-text-subtle">in scope</span>
            </Donut>
            <ul className="min-w-0 flex-1 space-y-1">
              {data.by_status.map((row) => (
                <li key={row.status}>
                  <Link
                    to={`/controls?status=${row.status}`}
                    className="flex items-center gap-3 rounded-sm px-1.5 py-1 text-body-sm hover:bg-surface-hover"
                  >
                    <span
                      className="size-2.5 shrink-0 rounded-[3px]"
                      style={{ backgroundColor: STATUS_META[row.status]?.color }}
                    />
                    <span className="flex-1 text-text-secondary">
                      {STATUS_META[row.status]?.label ?? row.status}
                    </span>
                    <span className="w-8 text-right tabular font-semibold text-text-primary">
                      {row.count}
                    </span>
                    <span className="w-10 text-right tabular text-text-subtle">
                      {pct(row.count, total)}%
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          {data.controls_disabled > 0 ? (
            <div className="mt-4 flex items-center gap-2 border-t border-border pt-3">
              <Badge variant="neutral">Disabled</Badge>
              <Link
                to="/controls?status=disabled"
                className="text-body-sm text-text-secondary hover:text-text-primary"
              >
                {data.controls_disabled} controls out of scope — shown separately
                below
              </Link>
            </div>
          ) : null}
        </Card>

        {/* Coverage breakdown */}
        <Card title="Coverage breakdown">
          <div className="grid grid-cols-3 gap-3">
            <Link to="/controls?evidence=with" className="rounded-md py-1 hover:bg-surface-hover">
              <Ring
                value={evidencedControls}
                total={total}
                color="rgb(var(--color-action-accent))"
                caption="Evidence"
              />
            </Link>
            <Link to="/controls?status=implemented" className="rounded-md py-1 hover:bg-surface-hover">
              <Ring
                value={data.controls_ready}
                total={total}
                color="rgb(var(--color-status-success-base))"
                caption="Ready"
              />
            </Link>
            <Link to="/controls?owner=assigned" className="rounded-md py-1 hover:bg-surface-hover">
              <Ring
                value={data.controls_owned}
                total={total}
                color="rgb(var(--color-status-pending-base))"
                caption="Owners"
              />
            </Link>
          </div>
          <ul className="mt-4 border-t border-border">
            {[
              ["Controls with evidence", evidencedControls, "/controls?evidence=with"],
              ["Controls with an owner", data.controls_owned, "/controls?owner=assigned"],
              ["Ready for audit", data.controls_ready, "/controls?status=implemented"],
            ].map(([label, value, to]) => (
              <li key={label as string}>
                <Link
                  to={to as string}
                  className="flex items-center justify-between border-b border-border py-2.5 last:border-0 hover:text-text-primary"
                >
                  <span className="text-body-md text-text-secondary">{label}</span>
                  <span className="tabular text-body-md font-semibold text-text-primary">
                    {value} <span className="text-text-subtle">/ {total}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>

      </div>

      {/* Automated checks · Evidence */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card
          title="Automated checks & monitoring"
          action={<Badge variant="neutral">Not enabled</Badge>}
        >
          <p className="flex items-baseline gap-2">
            <span className="font-display text-numeral-md tabular text-text-primary">
              0<span className="text-body-md text-text-subtle"> / {total}</span>
            </span>
            <span className="text-body-sm text-text-subtle">
              controls continuously monitored
            </span>
          </p>
          <div className="mt-3">
            <Meter value={0} total={total} fill="rgb(var(--color-status-neutral-base))" />
          </div>
          <ul className="mt-4 space-y-2">
            {[
              ["Passing", 0, "bg-status-success-base"],
              ["Failing", 0, "bg-status-danger-base"],
              ["Not monitored", total, "bg-status-neutral-base"],
            ].map(([label, value, dot]) => (
              <li
                key={label as string}
                className="flex items-center gap-2 text-body-sm"
              >
                <span className={cn("size-2.5 rounded-full", dot as string)} />
                <span className="flex-1 text-text-secondary">{label}</span>
                <span className="tabular font-semibold text-text-primary">
                  {value}
                </span>
              </li>
            ))}
          </ul>
          <div className="mt-4 rounded-md border border-border bg-surface-sunken p-3">
            <p className="flex items-start gap-2 text-body-sm text-text-secondary">
              <Icon name="plug" className="mt-0.5 size-4 shrink-0 text-text-subtle" />
              Connect an integration such as AWS, GitHub or Okta to test these
              controls automatically. Until then, controls are verified manually
              from uploaded evidence.
            </p>
            <Button asChild size="sm" className="mt-3">
              <Link to="/connectors">
                <Icon name="plus" className="size-4" />
                Connect an integration
              </Link>
            </Button>
          </div>
        </Card>

        <Card
          title="Evidence"
          action={
            <Link
              to="/evidence"
              className="text-body-sm font-semibold text-text-link"
            >
              View all
            </Link>
          }
        >
          <p className="flex items-baseline gap-2">
            <span className="font-display text-numeral-md tabular text-text-primary">
              {data.evidence_total}
            </span>
            <span className="text-body-sm text-text-subtle">
              files · covering {evidencedControls} of {total} controls (
              {pct(evidencedControls, total)}%)
            </span>
          </p>
          <ul className="mt-4 space-y-2.5">
            {[
              ["Fresh", data.evidence_fresh, FRESHNESS_FILL.current],
              ["Expiring ≤ 30 days", data.evidence_aging, FRESHNESS_FILL.aging],
              ["Stale · needs refresh", data.evidence_stale, FRESHNESS_FILL.stale],
            ].map(([label, value, fill]) => (
              <li key={label as string} className="flex items-center gap-3">
                <span className="w-36 shrink-0 text-body-sm text-text-secondary">
                  {label}
                </span>
                <span className="flex-1">
                  <Meter
                    value={value as number}
                    total={Math.max(data.evidence_total, 1)}
                    fill={fill as string}
                  />
                </span>
                <span className="w-8 shrink-0 text-right tabular text-body-sm font-semibold text-text-primary">
                  {value}
                </span>
              </li>
            ))}
          </ul>
          {data.evidence_recent.length > 0 ? (
            <>
              <p className="type-overline mt-5 mb-2">Recently added</p>
              <ul className="space-y-1">
                {data.evidence_recent.map((ev, i) => (
                  <li
                    key={`${ev.title}-${i}`}
                    className="flex items-center gap-2 text-body-sm"
                  >
                    {ev.control_code ? (
                      <Badge variant="role">{ev.control_code}</Badge>
                    ) : null}
                    <span className="min-w-0 flex-1 truncate text-text-primary">
                      {ev.title}
                    </span>
                    <span className="shrink-0 tabular text-text-subtle">
                      {relativeTime(ev.collected_on)}
                    </span>
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </Card>
      </div>

      {/* Owners · Disabled */}
      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Owners & assignment">
          {data.by_owner.length === 0 ? (
            <p className="text-body-sm text-text-subtle">No controls yet.</p>
          ) : (
            <ul className="space-y-1">
              {data.by_owner.map((owner) => {
                const unassigned = owner.membership_id === null;
                return (
                  <li key={owner.membership_id ?? "unassigned"}>
                    <Link
                      to={`/controls?owner=${owner.membership_id ?? "unassigned"}`}
                      className="flex items-center gap-3 rounded-sm px-1.5 py-1.5 hover:bg-surface-hover"
                    >
                      <span
                        className={cn(
                          "flex size-7 shrink-0 items-center justify-center rounded-full text-caption font-bold",
                          unassigned
                            ? "bg-surface-sunken text-text-subtle"
                            : "bg-action-accent-tint text-action-accent",
                        )}
                      >
                        {unassigned ? "?" : initials(owner.name)}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span
                          className={cn(
                            "block truncate text-body-sm font-semibold",
                            unassigned
                              ? "text-status-warning-text"
                              : "text-text-primary",
                          )}
                        >
                          {owner.name}
                        </span>
                        {owner.role ? (
                          <span className="block truncate text-caption text-text-subtle">
                            {owner.role}
                          </span>
                        ) : unassigned ? (
                          <span className="block text-caption text-text-subtle">
                            needs an owner
                          </span>
                        ) : null}
                      </span>
                      <span className="h-[6px] w-24 shrink-0 overflow-hidden rounded-full bg-surface-sunken">
                        <span
                          className="block h-full rounded-full"
                          style={{
                            width: `${(owner.count / ownerMax) * 100}%`,
                            backgroundColor: unassigned
                              ? "rgb(var(--color-status-neutral-base))"
                              : "rgb(var(--color-action-accent))",
                          }}
                        />
                      </span>
                      <span className="w-6 shrink-0 text-right tabular text-body-sm font-semibold text-text-primary">
                        {owner.count}
                      </span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <Card
          title="Disabled controls"
          meta={`${data.disabled.length} out of scope`}
        >
          {data.disabled.length === 0 ? (
            <p className="text-body-sm text-text-subtle">
              No disabled controls.
            </p>
          ) : (
            <ul className="-my-1">
              {data.disabled.map((control) => (
                <li
                  key={control.control_id}
                  className="flex items-start gap-3 border-b border-border py-2.5 last:border-0"
                >
                  <span className="mt-0.5 flex size-7 shrink-0 items-center justify-center rounded-md bg-surface-sunken text-text-subtle">
                    <Icon name="x" className="size-3.5" aria-hidden />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <Badge variant="role">{control.code}</Badge>
                      <Link
                        to={`/controls/${control.control_id}`}
                        className="truncate text-body-sm font-semibold text-text-primary hover:text-text-link"
                      >
                        {control.name}
                      </Link>
                    </span>
                    {control.reason ? (
                      <span className="mt-0.5 block text-caption text-text-subtle">
                        {control.reason}
                      </span>
                    ) : null}
                  </span>
                  {canManage ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      className="shrink-0"
                      disabled={enableMutation.isPending}
                      onClick={() => enableMutation.mutate(control.control_id)}
                    >
                      Re-enable
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Coverage by category — each bar splits ready / in progress / no control */}
        <Card title="Coverage by Trust Services Criteria">
          {data.by_category.length === 0 ? (
            <p className="text-body-sm text-text-subtle">
              No categories in scope yet.
            </p>
          ) : (
            <>
              <ul className="space-y-3.5">
                {data.by_category.map((row) => {
                  const ready = row.ready;
                  const partial = Math.max(row.covered - row.ready, 0);
                  const gap = Math.max(row.in_scope - row.covered, 0);
                  const coverage = pct(row.covered, row.in_scope);
                  const coverageTone =
                    coverage >= 80 ? "success" : coverage >= 40 ? "warning" : "danger";
                  return (
                    <li key={row.category}>
                      <Link
                        to={`/controls?trust=${encodeURIComponent(row.category)}`}
                        className="group block rounded-sm px-1 py-1 hover:bg-surface-hover"
                      >
                        <div className="mb-1.5 flex items-center gap-2">
                          <Icon
                            name={CATEGORY_ICON[row.category] ?? "shield"}
                            className="size-4 shrink-0 text-text-subtle"
                            aria-hidden
                          />
                          <span className="min-w-0 flex-1 truncate text-body-md text-text-primary">
                            {row.category}
                            {row.category === "Security" ? (
                              <span className="text-text-subtle"> (Common Criteria)</span>
                            ) : null}
                          </span>
                          <span className="shrink-0 text-body-sm tabular text-text-subtle">
                            {row.covered}/{row.in_scope}
                          </span>
                          <span
                            className={cn(
                              "w-10 shrink-0 text-right font-display text-body-md tabular font-semibold",
                              BAND_TEXT[coverageTone],
                            )}
                          >
                            {coverage}%
                          </span>
                        </div>
                        {/* Ready · in progress · no control, 2px gaps between fills */}
                        <div className="flex h-2 gap-0.5 overflow-hidden rounded-full">
                          {[
                            { value: ready, fill: BAND_FILL.success },
                            { value: partial, fill: BAND_FILL.warning },
                            { value: gap, fill: BAND_FILL.danger },
                          ]
                            .filter((s) => s.value > 0)
                            .map((s, i) => (
                              <span
                                key={i}
                                className="h-full"
                                style={{
                                  width: `${(s.value / Math.max(row.in_scope, 1)) * 100}%`,
                                  backgroundColor: s.fill,
                                }}
                              />
                            ))}
                          {row.in_scope === 0 ? (
                            <span className="h-full w-full bg-surface-sunken" />
                          ) : null}
                        </div>
                      </Link>
                    </li>
                  );
                })}
              </ul>
              <div className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 border-t border-border pt-3">
                <LegendDot color={BAND_FILL.success} label="Ready" />
                <LegendDot color={BAND_FILL.warning} label="In progress" />
                <LegendDot color={BAND_FILL.danger} label="No control" />
              </div>
            </>
          )}
        </Card>

        {/* Progress over time */}
        <Card
          title="Progress over time"
          action={
            <div className="flex flex-wrap items-center gap-2">
              <input
                type="date"
                aria-label="From date"
                value={range.from ?? data.timeline_from}
                min={data.tenant_created_on}
                max={range.to ?? today}
                onChange={(e) =>
                  setRange((r) => ({ ...r, from: e.target.value || undefined }))
                }
                className="rounded-sm border border-border bg-surface-primary px-2 py-1 text-body-sm text-text-primary"
              />
              <span className="text-body-sm text-text-subtle">to</span>
              <input
                type="date"
                aria-label="To date"
                value={range.to ?? data.timeline_to}
                min={range.from ?? data.tenant_created_on}
                max={today}
                onChange={(e) =>
                  setRange((r) => ({ ...r, to: e.target.value || undefined }))
                }
                className="rounded-sm border border-border bg-surface-primary px-2 py-1 text-body-sm text-text-primary"
              />
              {(range.from || range.to) && (
                <button
                  type="button"
                  onClick={() => setRange({})}
                  className="text-body-sm font-semibold text-text-link"
                >
                  Reset
                </button>
              )}
            </div>
          }
        >
          {data.timeline.length > 0 ? (
            <TimelineChart points={data.timeline} />
          ) : (
            <p className="text-body-sm text-text-subtle">
              Nothing recorded in this range.
            </p>
          )}
        </Card>

      </div>

      {/* Recent activity */}
      <Card
        title="Recent activity"
        meta="controls module"
        action={
          <Link
            to="/audit-log"
            className="text-body-sm font-semibold text-text-link"
          >
            View audit log
          </Link>
        }
      >
        {data.recent_activity.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            No changes to controls yet.
          </p>
        ) : (
          <ul>
            {data.recent_activity.map((item, i) => (
              <ActivityRow key={`${item.occurred_at}-${i}`} item={item} />
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function LegendDot({
  color,
  label,
  value,
}: {
  color: string;
  label: string;
  value?: number;
}) {
  return (
    <span className="flex items-center gap-1.5 text-body-sm text-text-secondary">
      <span
        className="size-2.5 rounded-[3px]"
        style={{ backgroundColor: color }}
      />
      {label}
      {value !== undefined ? (
        <span className="tabular font-semibold text-text-primary">{value}</span>
      ) : null}
    </span>
  );
}
