import { Link } from "react-router-dom";
import {
  Button,
  Card,
  ChartLegend,
  FAMILY_CHART,
  Icon,
  PageHeader,
  Skeleton,
  StatTile,
  type IconName,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";
import {
  AssetsCard,
  EvidenceCard,
  PoliciesCard,
  RiskCard,
  TasksCard,
  TopRisksCard,
  VendorsCard,
  VulnerabilitiesCard,
} from "./admin-cards";
import { ProgressRing } from "./donut";
import {
  isForbidden,
  useAccess,
  useEngagement,
  useFrameworks,
  usePosture,
  useRisks,
  useVulnerabilities,
} from "./hooks";
import { coverageParts, dayDelta, localDay, pct, ringToneFor, type CoverageKey, type CoveragePart } from "./model";
import { Empty, Panel, Settled, Tile, ViewAll } from "./section";
import type { CategoryCoverage, FrameworkSummary, Posture } from "./types";

/**
 * The admin posture view. Every number comes from the workspace's own data:
 * readiness and per category coverage from the engagement dashboard, the
 * frameworks from the controls the workspace has actually adopted, and a card
 * per module from that module's summary. A tile with no source is not here
 * (there is no trend, no score and no estimate), and a role that cannot read a
 * module does not see its tile.
 */

const CATEGORY_ICON: Record<string, IconName> = {
  Security: "shield",
  Availability: "activity",
  Confidentiality: "book",
  "Processing Integrity": "controls",
  Privacy: "users",
};

export function AdminDashboard() {
  const access = useAccess();
  const posture = usePosture(access.compliance);
  const subtitle = posture.data
    ? `${posture.data.controls_ready} of ${posture.data.controls_total} controls ready`
    : undefined;

  return (
    <div className="w-full">
      <PageHeader title="Compliance posture" subtitle={subtitle} />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {access.compliance ? <ControlsTile /> : null}
        {access.compliance && access.evidence ? <EvidenceTile /> : null}
        {access.risks ? <RisksTile /> : null}
        {access.vulnerabilities ? <VulnerabilitiesTile /> : null}
      </div>

      {access.compliance ? (
        <>
          <ReadinessCard />
          <FrameworkCards />
          <CoverageCard />
        </>
      ) : null}

      {/* Supporting cards. Each spans one column except Top risks, which takes
          two, so the grid closes into even rows. */}
      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {access.vulnerabilities ? <VulnerabilitiesCard /> : null}
        {access.compliance && access.evidence ? <EvidenceCard /> : null}
        {access.risks ? <RiskCard /> : null}
        {access.assets ? <AssetsCard /> : null}
        {access.tasks ? <TasksCard /> : null}
        {access.vendors ? <VendorsCard /> : null}
        {access.risks ? <TopRisksCard /> : null}
        {access.documents ? <PoliciesCard /> : null}
      </div>
    </div>
  );
}

// -- headline tiles -----------------------------------------------------------

function ControlsTile() {
  const query = usePosture();
  return (
    <Tile label="Controls" subject="posture" query={query}>
      {(p) => (
        <StatTile
          icon="controls"
          label="Controls"
          value={p.controls_total}
          tone="progress"
          caption={p.controls_total > 0 ? `${p.controls_ready} ready` : undefined}
          to="/controls"
        />
      )}
    </Tile>
  );
}

function EvidenceTile() {
  const query = usePosture();
  return (
    <Tile label="Evidence" subject="posture" query={query}>
      {(p) => (
        <StatTile
          icon="doc"
          label="Evidence"
          value={p.evidence_total}
          tone="progress"
          caption={p.evidence_stale > 0 ? `${p.evidence_stale} expired` : undefined}
          to="/evidence"
        />
      )}
    </Tile>
  );
}

function RisksTile() {
  const query = useRisks();
  return (
    <Tile label="Risks" subject="risk summary" query={query}>
      {(picture) => {
        const total = picture?.summary.total ?? 0;
        const high = (picture?.summary.by_band.critical ?? 0) + (picture?.summary.by_band.high ?? 0);
        return (
          <StatTile
            icon="risk"
            label="Risks"
            value={total}
            tone="warning"
            caption={high > 0 ? `${high} high or critical` : undefined}
            to="/risks"
          />
        );
      }}
    </Tile>
  );
}

function VulnerabilitiesTile() {
  const query = useVulnerabilities();
  return (
    <Tile label="Vulnerabilities" subject="vulnerability summary" query={query}>
      {(kpis) => (
        <StatTile
          icon="bug"
          label="Vulnerabilities"
          value={kpis.open_total}
          tone="danger"
          caption={kpis.overdue > 0 ? `${kpis.overdue} past SLA` : undefined}
          to="/vulnerabilities"
        />
      )}
    </Tile>
  );
}

// -- readiness ----------------------------------------------------------------

function MiniStat({ value, label, tone, to }: { value: string | number; label: string; tone?: string; to?: string }) {
  const body = (
    <>
      <p className={cn("font-display text-numeral-sm tabular", tone ?? "text-text-primary")}>{value}</p>
      <p className="text-caption text-text-subtle">{label}</p>
    </>
  );
  return to ? (
    <Link
      to={to}
      className="rounded-sm hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
    >
      {body}
    </Link>
  ) : (
    <div>{body}</div>
  );
}

function ReadinessBody({ posture: p }: { posture: Posture }) {
  // The observation window belongs to the engagement, not the posture. It is
  // extra context, so its absence or failure just leaves that figure out.
  const engagement = useEngagement();
  const frameworks = useFrameworks();
  // The framework this readiness is for: the engagement's, or else the only one
  // the workspace has adopted. With several and no engagement it is just "Audit".
  const framework = p.framework_name ?? (frameworks.data?.length === 1 ? frameworks.data[0].name : null);
  const ready = pct(p.controls_ready, p.controls_total);
  const auditType = p.audit_type === "type_2" ? "Type II" : p.audit_type === "type_1" ? "Type I" : "";
  const title = [framework ?? "Audit", auditType, "readiness"].filter(Boolean).join(" ");
  const windowEnd = engagement.data?.window_end;
  const daysToWindowClose = windowEnd ? dayDelta(windowEnd, localDay(new Date())) : null;

  const noControls = p.controls_total === 0;
  const cta = noControls
    ? { to: "/controls", label: "Open controls" }
    : !p.has_engagement
      ? { to: "/frameworks/scope", label: "Set audit scope" }
      : null;
  const note = noControls
    ? "No controls yet. Adopt the control library to start."
    : p.has_engagement
      ? "A control is ready when it is implemented and backed by current evidence."
      : "Set your audit scope to measure readiness against your criteria. A control is ready when it is implemented and backed by current evidence.";

  return (
    <div className="flex flex-wrap items-center gap-6">
      <ProgressRing
        percent={ready}
        tone={ringToneFor(ready)}
        size={132}
        stroke={14}
        label={`${p.controls_ready} of ${p.controls_total} controls ready, ${ready} percent`}
      >
        <span className="font-display text-numeral-lg tabular text-text-primary">{ready}%</span>
        <span className="mt-1 text-caption text-text-subtle">
          {p.controls_ready} / {p.controls_total} controls
        </span>
      </ProgressRing>
      <div className="min-w-[240px] flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            {framework ? <FrameworkMark name={framework} /> : null}
            <p className="font-display text-title-md text-text-primary">{title}</p>
          </div>
          <ViewAll to="/frameworks/dashboard" label="Full posture" />
        </div>
        <p className="mt-1 text-body-sm text-text-secondary">{note}</p>
        {cta ? (
          <Button asChild size="sm" className="mt-3">
            <Link to={cta.to}>{cta.label}</Link>
          </Button>
        ) : null}
        {noControls ? null : (
          <div className="mt-3 flex flex-wrap gap-6">
            <MiniStat value={p.controls_in_progress} label="In progress" to="/controls?status=in_progress" />
            <MiniStat
              value={p.controls_no_evidence}
              label="No evidence"
              tone={p.controls_no_evidence > 0 ? "text-status-warning-text" : undefined}
              to="/controls?evidence=none"
            />
            {p.checks_available ? (
              <MiniStat
                value={p.automation_failing}
                label="Failing tests"
                tone={p.automation_failing > 0 ? "text-status-danger-text" : undefined}
              />
            ) : null}
            {daysToWindowClose !== null && daysToWindowClose >= 0 ? (
              <MiniStat value={`${daysToWindowClose}d`} label="To window close" />
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

function ReadinessCard() {
  const query = usePosture();
  if (isForbidden(query.error)) return null;
  return (
    <Card className="mt-4 p-5">
      <Settled query={query} subject="posture" skeleton={<Skeleton className="h-32 w-full" />}>
        {(p) => <ReadinessBody posture={p} />}
      </Settled>
    </Card>
  );
}

// -- frameworks ---------------------------------------------------------------

/** The framework's own mark, in the same contained treatment as the sign-in
 *  marquee and the controls table. */
function FrameworkMark({ name }: { name: string }) {
  return (
    <span className="flex size-9 shrink-0 items-center justify-center overflow-hidden rounded-full bg-surface-primary ring-1 ring-border">
      <FrameworkLogo name={name} size={24} eager />
    </span>
  );
}

function FrameworkCard({ framework: fw }: { framework: FrameworkSummary }) {
  const implemented = pct(fw.implemented, fw.controls);
  const rows = [
    { label: "Implemented", value: fw.implemented, tone: "text-status-success-text" },
    { label: "In progress", value: fw.inProgress, tone: "text-text-primary" },
    { label: "Remaining", value: fw.controls - fw.implemented - fw.inProgress, tone: "text-text-primary" },
  ];
  return (
    <Card
      asChild
      className="transition-colors duration-80 ease-state hover:border-action-accent-border hover:bg-surface-hover"
    >
      <Link
        to={`/controls?framework=${encodeURIComponent(fw.name)}`}
        className="block p-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
      >
        <div className="flex items-center gap-2.5">
          <FrameworkMark name={fw.name} />
          <div className="min-w-0 flex-1">
            <p className="truncate text-body-md font-semibold text-text-primary">{fw.name}</p>
            <p className="text-caption text-text-subtle">
              {fw.controls} {fw.controls === 1 ? "control" : "controls"}
            </p>
          </div>
        </div>
        <div className="mt-3 flex items-center gap-4">
          <ProgressRing
            percent={implemented}
            tone={ringToneFor(implemented)}
            size={92}
            stroke={11}
            label={`${fw.name}: ${fw.implemented} of ${fw.controls} controls implemented, ${implemented} percent`}
          >
            <span className="font-display text-numeral-md tabular text-text-primary">{implemented}%</span>
          </ProgressRing>
          <div className="flex-1 space-y-1.5 text-body-sm">
            {rows.map((row) => (
              <div key={row.label} className="flex justify-between">
                <span className="text-text-secondary">{row.label}</span>
                <span className={cn("tabular font-semibold", row.tone)}>{row.value}</span>
              </div>
            ))}
          </div>
        </div>
      </Link>
    </Card>
  );
}

/**
 * One card per framework the workspace has adopted, and no others. A workspace
 * with a single framework (every new one starts with SOC 2 only) has it in the
 * readiness card above, so the row appears once there are several to compare.
 * It is a refinement of that card, so while it loads or if it fails it simply
 * is not drawn.
 */
function FrameworkCards() {
  const query = useFrameworks();
  if (!query.isSuccess || query.data.length < 2) return null;
  return (
    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
      {query.data.map((framework) => (
        <FrameworkCard key={framework.name} framework={framework} />
      ))}
    </div>
  );
}

// -- coverage -----------------------------------------------------------------

const COVERAGE_FAMILY = {
  ready: FAMILY_CHART.success,
  partial: FAMILY_CHART.warning,
  gap: FAMILY_CHART.danger,
} as const;

const percentText = (part: CoveragePart) => (part.percent === 0 && part.count > 0 ? "<1%" : `${part.percent}%`);

/**
 * Each category is one status bar: how many of its criteria are ready, need work
 * (a control exists but is not ready) or are missing (no control). The words under
 * the bar say the same in percent, so the colour is never the only signal.
 */
function CoverageCard() {
  const query = usePosture();
  return (
    <Panel
      className="mt-4"
      title="Coverage by Trust Services Criteria"
      subject="coverage"
      query={query}
      action={<ViewAll to="/controls" label="View controls" />}
      skeleton={<Skeleton className="h-64 w-full" />}
    >
      {(p) => {
        if (p.by_category.length === 0) {
          return (
            <Empty to="/frameworks/scope" cta="Set audit scope">
              No audit scope yet.
            </Empty>
          );
        }
        const rows = p.by_category.map((row) => ({ row, parts: coverageParts(row) }));
        const totalOf = (key: CoverageKey) =>
          rows.reduce((sum, { parts }) => sum + (parts.find((part) => part.key === key)?.count ?? 0), 0);
        return (
          <>
            <ChartLegend
              className="mb-4"
              items={rows[0].parts.map((part) => ({
                key: part.key,
                label: part.label,
                swatchClass: COVERAGE_FAMILY[part.key].dot,
                value: totalOf(part.key),
              }))}
            />
            <ul className="space-y-1">
              {rows.map(({ row, parts }) => (
                <CoverageRow key={row.category} row={row} parts={parts} />
              ))}
            </ul>
          </>
        );
      }}
    </Panel>
  );
}

function CoverageRow({ row, parts }: { row: CategoryCoverage; parts: CoveragePart[] }) {
  const total = parts.reduce((sum, part) => sum + part.count, 0);
  const ready = parts.find((part) => part.key === "ready")?.count ?? 0;
  return (
    <li>
      <Link
        to={`/controls?trust=${encodeURIComponent(row.category)}`}
        className="flex flex-wrap items-start gap-x-3 gap-y-1 rounded-sm px-1 py-1.5 transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
      >
        <span className="flex h-6 w-full items-center gap-3 sm:w-56 sm:shrink-0">
          <Icon name={CATEGORY_ICON[row.category] ?? "shield"} className="size-4 shrink-0 text-text-subtle" />
          <span className="truncate text-body-md text-text-secondary">
            {row.category}
            {row.category === "Security" ? " (Common Criteria)" : ""}
          </span>
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex h-6 items-center" aria-hidden>
            <span className="flex h-2.5 w-full gap-0.5 overflow-hidden rounded-full bg-surface-sunken">
              {parts
                .filter((part) => part.count > 0)
                .map((part) => (
                  <span
                    key={part.key}
                    className={COVERAGE_FAMILY[part.key].bar}
                    style={{ width: `${(part.count / total) * 100}%` }}
                    title={`${part.label}: ${part.count} of ${total} criteria. ${part.hint}`}
                  />
                ))}
            </span>
          </span>
          <span className="flex flex-wrap gap-x-4 gap-y-0.5 text-caption text-text-subtle">
            {total === 0
              ? "No criteria in scope"
              : parts
                  .filter((part) => part.key === "ready" || part.count > 0)
                  .map((part) => (
                    <span
                      key={part.key}
                      className={cn("inline-flex items-center gap-1.5", part.key === "gap" && "text-status-danger-text")}
                    >
                      <span className={cn("size-2 shrink-0 rounded-full", COVERAGE_FAMILY[part.key].dot)} aria-hidden />
                      {part.label}
                      <span className={cn("tabular font-semibold", part.key !== "gap" && "text-text-secondary")}>
                        {percentText(part)}
                      </span>
                    </span>
                  ))}
          </span>
        </span>
        <span className="tabular flex h-6 w-24 shrink-0 items-center justify-end gap-1 text-body-sm text-text-subtle">
          <span className="font-semibold text-text-primary">{ready}</span> of {total} ready
        </span>
      </Link>
    </li>
  );
}
