import { useMemo } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  ColumnPicker,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  Pagination,
  SearchInput,
  StatusPill,
  Table,
  TableIconButton,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  Tooltip,
  useColumnPrefs,
  useTableSort,
  type ColumnDef,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getOptions, getSummary, listRisks } from "../api";
import type { Attention, Risk, RiskFilters, RiskSort } from "../types";
import {
  ATTENTION_META,
  daysUntil,
  fmtDate,
  STATUS_META,
  TREATMENT_META,
} from "../tokens";
import { useCustomFields } from "@/features/custom-fields/hooks";
import { AppetitePill } from "./risk-extras";
import { ScoreChip } from "./score";
import { useRisksOutlet } from "./risks-outlet";

const PAGE_SIZE = 25;

const COLUMNS = [
  { key: "inherent", label: "Inherent" },
  { key: "treatment", label: "Treatment" },
  { key: "owner", label: "Business owner" },
  { key: "unit", label: "Business unit" },
  { key: "controls", label: "Controls" },
  { key: "review", label: "Next review" },
] as const satisfies readonly ColumnDef<string>[];
type ColumnKey = (typeof COLUMNS)[number]["key"];

const EMPTY: RiskFilters = {
  search: "",
  statuses: [],
  bands: [],
  category_ids: [],
  treatments: [],
  owner: null,
  department_ids: [],
  attention: [],
  cell: null,
  custom: [],
};

function readFilters(p: URLSearchParams): RiskFilters {
  return {
    search: p.get("search") ?? "",
    statuses: p.getAll("statuses"),
    bands: p.getAll("bands"),
    category_ids: p.getAll("category_ids"),
    treatments: p.getAll("treatments"),
    owner: p.get("owner"),
    department_ids: p.getAll("department_ids"),
    attention: p.getAll("attention"),
    cell: p.get("cell"),
    custom: p.getAll("custom"),
  };
}

function writeFilters(f: RiskFilters, page: number): URLSearchParams {
  const p = new URLSearchParams();
  if (f.search) p.set("search", f.search);
  for (const v of f.statuses) p.append("statuses", v);
  for (const v of f.bands) p.append("bands", v);
  for (const v of f.category_ids) p.append("category_ids", v);
  for (const v of f.treatments) p.append("treatments", v);
  for (const v of f.department_ids) p.append("department_ids", v);
  for (const v of f.attention) p.append("attention", v);
  if (f.owner) p.set("owner", f.owner);
  if (f.cell) p.set("cell", f.cell);
  for (const v of f.custom) p.append("custom", v);
  if (page > 1) p.set("page", String(page));
  return p;
}

const withCount = (label: string, n: number | undefined) => (n ? `${label} (${n})` : label);

/**
 * The register as a work list: worst exposure first, what each risk is missing
 * beside it, and every facet in the query string so a filtered view survives
 * Back and can be sent to a colleague.
 */
export function RisksRegisterPage() {
  const navigate = useNavigate();
  const { register, addRisk, openImport, canManage } = useRisksOutlet();
  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => readFilters(params), [params]);
  const page = Number(params.get("page") ?? 1) || 1;

  const apply = (next: RiskFilters, nextPage = 1) => setParams(writeFilters(next, nextPage), { replace: true });
  const set = <K extends keyof RiskFilters>(key: K, value: RiskFilters[K]) => apply({ ...filters, [key]: value });
  const clear = () => apply(EMPTY);

  const cols = useColumnPrefs<ColumnKey>("verity.risks.columns", COLUMNS, ["unit", "treatment"]);
  const { key: sortKey, dir, thProps } = useTableSort<Risk, RiskSort>(null, {
    code: (r) => r.code,
    title: (r) => r.title,
    inherent: (r) => r.inherent_score,
    residual: (r) => r.residual_score ?? r.inherent_score,
    status: (r) => r.status,
    next_review: (r) => r.next_review_on,
    updated: (r) => r.updated_at,
  });

  const query = useQuery({
    queryKey: ["risks", register.id, filters, page, sortKey, dir],
    queryFn: () => listRisks(register.id, filters, page, PAGE_SIZE, sortKey, dir),
  });
  const summaryQuery = useQuery({ queryKey: ["risk-summary", register.id], queryFn: () => getSummary(register.id) });
  const optionsQuery = useQuery({ queryKey: ["risk-options"], queryFn: getOptions, staleTime: 60_000 });
  const summary = summaryQuery.data;
  const customFacets = (useCustomFields("risks").data ?? []).filter(
    (f) => f.field_type === "select" || f.field_type === "checkbox",
  );

  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered = JSON.stringify(filters) !== JSON.stringify(EMPTY);

  const categoryOptions = register.categories
    .filter((c) => !c.archived)
    .flatMap((c) => [
      { value: c.id, label: c.name },
      ...c.children.filter((s) => !s.archived).map((s) => ({ value: s.id, label: `${c.name} · ${s.name}` })),
    ]);

  const cellLabel = (() => {
    if (!filters.cell) return null;
    const [kind, l, i] = filters.cell.split(":");
    const lk = register.likelihood_scale.find((s) => String(s.level) === l)?.label ?? l;
    const im = register.impact_scale.find((s) => String(s.level) === i)?.label ?? i;
    return `${kind === "residual" ? "Residual" : "Inherent"}: ${lk} × ${im}`;
  })();

  return (
    <div>
      <Toolbar
        searchLabel="Filter risks"
        search={
          <SearchInput
            value={filters.search}
            onChange={(v) => set("search", v)}
            placeholder="Search title, code or description"
            aria-label="Search risks"
          />
        }
      >
        <FilterFacet
          label="Needs attention"
          options={(Object.keys(ATTENTION_META) as Attention[]).map((a) => ({
            value: a,
            label: withCount(ATTENTION_META[a].label, summary?.attention[a]),
          }))}
          values={filters.attention}
          onChange={(v) => set("attention", v)}
        />
        <FilterFacet
          label="Severity"
          options={[
            ...[...register.severity_bands].reverse().map((b) => ({
              value: b.key,
              label: withCount(b.label, summary?.by_band[b.key]),
            })),
            { value: "unscored", label: withCount("Not scored", summary?.by_band.unscored) },
          ]}
          values={filters.bands}
          onChange={(v) => set("bands", v)}
        />
        <FilterFacet
          label="Status"
          options={Object.entries(STATUS_META).map(([value, meta]) => ({
            value,
            label: withCount(meta.label, summary?.by_status[value]),
          }))}
          values={filters.statuses}
          onChange={(v) => set("statuses", v)}
        />
        <FilterFacet label="Category" options={categoryOptions} values={filters.category_ids} onChange={(v) => set("category_ids", v)} searchable />
        <FilterFacet
          label="Treatment"
          options={[
            ...Object.entries(TREATMENT_META).map(([value, meta]) => ({ value, label: meta.label })),
            { value: "undecided", label: "Undecided" },
          ]}
          values={filters.treatments}
          onChange={(v) => set("treatments", v)}
        />
        <FilterFacet
          label="Owner"
          options={[
            { value: "me", label: "Mine" },
            { value: "unassigned", label: "No owner" },
            ...(optionsQuery.data?.members ?? []).map((m) => ({ value: m.membership_id, label: m.name })),
          ]}
          values={filters.owner ? [filters.owner] : []}
          onChange={(v) => set("owner", v[v.length - 1] ?? null)}
          searchable
        />
        {optionsQuery.data?.business_units.length ? (
          <FilterFacet
            label="Business unit"
            options={optionsQuery.data.business_units.map((u) => ({ value: u.id, label: u.name }))}
            values={filters.department_ids}
            onChange={(v) => set("department_ids", v)}
          />
        ) : null}
        {customFacets.map((f) => (
          <FilterFacet
            key={f.id}
            label={f.label}
            options={
              f.field_type === "checkbox"
                ? [
                    { value: `${f.key}:true`, label: "Yes" },
                    { value: `${f.key}:false`, label: "No" },
                  ]
                : f.options.map((o) => ({ value: `${f.key}:${o}`, label: o }))
            }
            values={filters.custom.filter((v) => v.startsWith(`${f.key}:`))}
            onChange={(v) => set("custom", [...filters.custom.filter((c) => !c.startsWith(`${f.key}:`)), ...v])}
          />
        ))}
        {cellLabel ? (
          <button
            type="button"
            onClick={() => set("cell", null)}
            className="inline-flex h-9 items-center gap-1.5 rounded-full border border-action-accent-border bg-action-accent-tint px-3.5 text-label-sm text-action-accent"
          >
            <Icon name="heatmap" className="size-3.5" />
            {cellLabel}
            <Icon name="x" className="size-3.5" />
          </button>
        ) : null}
        {filtered ? (
          <Button variant="ghost" size="sm" onClick={clear}>
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      <div className="mt-4">
        {query.isError ? (
          <ErrorState
            title={describeError(query.error, "risk register").title}
            description={describeError(query.error, "risk register").message}
            onRetry={() => void query.refetch()}
          />
        ) : query.isLoading ? (
          <TableSkeleton rows={8} />
        ) : total === 0 ? (
          <EmptyState
            icon="risk"
            variant={filtered ? "no-match" : "no-data"}
            title={filtered ? "No risks match these filters" : "No risks in this register yet"}
            description={
              filtered ? "Adjust or clear the filters." : "Add one, import a spreadsheet, or start from the library."
            }
            onClearFilters={filtered ? clear : undefined}
            action={
              !filtered && canManage ? (
                <div className="flex flex-wrap justify-center gap-2">
                  <Button onClick={addRisk}>
                    <Icon name="plus" className="size-4" />
                    Add risk
                  </Button>
                  <Button variant="secondary" onClick={() => navigate("/risks/library")}>
                    <Icon name="book" className="size-4" />
                    Browse library
                  </Button>
                  <Button variant="secondary" onClick={openImport}>
                    <Icon name="upload" className="size-4" />
                    Import
                  </Button>
                </div>
              ) : undefined
            }
          />
        ) : (
          <Table actions={<ColumnPicker {...cols} />}>
            <THead>
              <TR>
                <TH {...thProps("title")}>Risk</TH>
                {cols.isVisible("inherent") ? <TH {...thProps("inherent")}>Inherent</TH> : null}
                <TH {...thProps("residual")}>Residual</TH>
                <TH {...thProps("status")}>Status</TH>
                {cols.isVisible("treatment") ? <TH>Treatment</TH> : null}
                {cols.isVisible("owner") ? <TH>Business owner</TH> : null}
                {cols.isVisible("unit") ? <TH>Business unit</TH> : null}
                {cols.isVisible("controls") ? <TH>Controls</TH> : null}
                {cols.isVisible("review") ? <TH {...thProps("next_review")}>Next review</TH> : null}
                <TH className="w-12">
                  <span className="sr-only">Actions</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {query.data!.items.map((r) => (
                <RiskRow key={r.id} risk={r} isVisible={cols.isVisible} />
              ))}
            </TBody>
          </Table>
        )}
      </div>

      {pageCount > 1 ? (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-body-sm text-text-subtle">
            {total} {total === 1 ? "risk" : "risks"}
          </span>
          <Pagination page={page} pageCount={pageCount} onPageChange={(p) => apply(filters, p)} />
        </div>
      ) : null}
    </div>
  );
}

function RiskRow({ risk: r, isVisible }: { risk: Risk; isVisible: (key: ColumnKey) => boolean }) {
  const navigate = useNavigate();
  const { register } = useRisksOutlet();
  const bands = register.severity_bands;
  const flags = r.attention.filter((a) => a !== "unscored");
  const reviewIn = daysUntil(r.next_review_on);
  return (
    <TR onClick={() => navigate(`/risks/${r.id}`)} className="cursor-pointer">
      <TD>
        <div className="min-w-0 max-w-[26rem]">
          <div className="flex items-center gap-2">
            <span className="tabular shrink-0 text-caption font-semibold text-text-subtle">{r.code}</span>
            <Link
              to={`/risks/${r.id}`}
              onClick={(e) => e.stopPropagation()}
              className="truncate text-body-md font-semibold text-text-primary hover:underline"
            >
              {r.title}
            </Link>
          </div>
          <div className="mt-0.5 flex min-w-0 items-center gap-1.5">
            <span className="truncate text-caption text-text-subtle">
              {[r.category_name, r.sub_category_name].filter(Boolean).join(" · ")}
            </span>
            {flags.slice(0, 2).map((a) => (
              <Tooltip key={a} content={ATTENTION_META[a].label}>
                <span
                  className={cn(
                    "inline-flex shrink-0 items-center gap-1 rounded-full px-1.5 py-px text-[11px] font-semibold",
                    ATTENTION_META[a].family === "danger"
                      ? "bg-status-danger-bg text-status-danger-text"
                      : ATTENTION_META[a].family === "warning"
                        ? "bg-status-warning-bg text-status-warning-text"
                        : "bg-action-accent-tint text-action-accent",
                  )}
                >
                  <Icon name={ATTENTION_META[a].icon} className="size-3" />
                  {ATTENTION_META[a].label}
                </span>
              </Tooltip>
            ))}
          </div>
        </div>
      </TD>
      {isVisible("inherent") ? (
        <TD>
          <ScoreChip score={r.inherent_score} bands={bands} size="sm" />
        </TD>
      ) : null}
      <TD>
        {r.residual_score !== null ? (
          <span className="inline-flex flex-wrap items-center gap-1.5">
            <ScoreChip score={r.residual_score} bands={bands} size="sm" />
            {r.appetite_status && r.appetite_status !== "within" ? <AppetitePill status={r.appetite_status} /> : null}
          </span>
        ) : (
          <span className="whitespace-nowrap text-caption text-text-subtle">Not assessed</span>
        )}
      </TD>
      <TD className="whitespace-nowrap">
        <StatusPill status={STATUS_META[r.status].family} label={STATUS_META[r.status].label} kind="inline" />
      </TD>
      {isVisible("treatment") ? (
        <TD>
          {r.treatment ? (
            <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-body-sm text-text-secondary">
              <Icon name={TREATMENT_META[r.treatment].icon} className="size-3.5 text-text-subtle" />
              {TREATMENT_META[r.treatment].label}
            </span>
          ) : (
            <span className="text-caption text-text-subtle">Undecided</span>
          )}
        </TD>
      ) : null}
      {isVisible("owner") ? (
        <TD>
          {r.owner ? (
            <div className="flex items-center gap-2">
              <Avatar name={r.owner.name} seed={r.owner.membership_id} size="sm" />
              <span className="truncate whitespace-nowrap text-body-sm text-text-secondary">{r.owner.name}</span>
            </div>
          ) : (
            <span className="text-caption text-text-subtle">No owner</span>
          )}
        </TD>
      ) : null}
      {isVisible("unit") ? (
        <TD>
          <span className="text-body-sm text-text-secondary">{r.department_name ?? "Not set"}</span>
        </TD>
      ) : null}
      {isVisible("controls") ? (
        <TD>
          {r.control_count ? (
            <Badge variant="neutral">{r.control_count}</Badge>
          ) : r.status === "closed" || r.status === "accepted" ? (
            <span className="text-caption text-text-subtle">None</span>
          ) : (
            <span className="inline-flex items-center gap-1 text-caption font-semibold text-status-danger-text">
              <Icon name="alert" className="size-3.5" />
              None
            </span>
          )}
        </TD>
      ) : null}
      {isVisible("review") ? (
        <TD>
          <span
            className={cn(
              "tabular whitespace-nowrap text-body-sm",
              reviewIn !== null && reviewIn < 0 && r.status !== "closed"
                ? "font-semibold text-status-danger-text"
                : "text-text-secondary",
            )}
          >
            {fmtDate(r.next_review_on)}
          </span>
        </TD>
      ) : null}
      <TD onClick={(e) => e.stopPropagation()} className="w-12">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <TableIconButton aria-label={`Actions for ${r.code}`}>
              <Icon name="more" className="size-4" />
            </TableIconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => navigate(`/risks/${r.id}`)}>Open</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => navigate(`/risks/${r.id}?tab=treatment`)}>Treatment</DropdownMenuItem>
            <DropdownMenuItem onSelect={() => navigate(`/risks/${r.id}?tab=controls`)}>Controls</DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => void navigator.clipboard.writeText(`${window.location.origin}/risks/${r.id}`)}
            >
              Copy link
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TD>
    </TR>
  );
}
