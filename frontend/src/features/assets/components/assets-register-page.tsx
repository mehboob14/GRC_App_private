import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
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
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { getFacets, getSummary, listAssets, listMembers, listSavedViews } from "../api";
import {
  ASSET_STATUSES,
  ASSET_TYPES,
  CRITICALITY_TIERS,
  DATA_CLASSIFICATIONS,
  ENVIRONMENTS,
  type Asset,
  type AssetFilters,
  type AssetStatus,
  type AssetType,
  type CriticalityTier,
  type DataClassification,
  type Environment,
  type SavedView,
} from "../types";
import {
  ASSET_TYPE_META,
  CLASSIFICATION_META,
  ENVIRONMENT_LABEL,
  STATUS_META,
  TIER_META,
  displayTier,
  fmtMoney,
  relativeTime,
} from "../tokens";

const PAGE_SIZE = 25;

const EMPTY: AssetFilters = {
  search: "",
  asset_type: "all",
  tiers: [],
  statuses: [],
  environments: [],
  classifications: [],
  exposure: null,
  owner: null,
  needs_attention: false,
};

export function AssetsRegisterPage() {
  const navigate = useNavigate();
  const [filters, setFilters] = useState<AssetFilters>(EMPTY);
  const [activeView, setActiveView] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  const set = <K extends keyof AssetFilters>(key: K, value: AssetFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setActiveView(null);
    setPage(1);
  };

  const summaryQuery = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });
  const facetsQuery = useQuery({ queryKey: ["asset-facets"], queryFn: getFacets });
  const viewsQuery = useQuery({ queryKey: ["asset-saved-views"], queryFn: listSavedViews });
  const membersQuery = useQuery({ queryKey: ["asset-members"], queryFn: listMembers });
  const query = useQuery({
    queryKey: ["assets", filters, page],
    queryFn: () => listAssets(filters, page, PAGE_SIZE),
  });

  const facets = facetsQuery.data;
  const withCount = (label: string, n: number | undefined) => (n ? `${label} (${n})` : label);

  const ownerOptions = useMemo(
    () => [
      { value: "me", label: "Owned by me" },
      { value: "unassigned", label: "Unassigned" },
      ...(membersQuery.data ?? []).map((m) => ({ value: m.membership_id, label: m.name })),
    ],
    [membersQuery.data],
  );

  function applyView(v: SavedView) {
    setFilters({ ...EMPTY, ...v.filters });
    setActiveView(v.id);
    setPage(1);
  }

  const activeCount =
    filters.tiers.length +
    filters.statuses.length +
    filters.environments.length +
    filters.classifications.length +
    (filters.asset_type !== "all" ? 1 : 0) +
    (filters.exposure ? 1 : 0) +
    (filters.owner ? 1 : 0) +
    (filters.needs_attention ? 1 : 0);

  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const s = summaryQuery.data;
  const savedViews = viewsQuery.data ?? [];

  return (
    <div>
      {/* Headline metrics — one compact strip. */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <Kpi label="Total assets" value={s?.total} />
        <Kpi label="Critical" value={s?.by_tier.critical} tone="danger" />
        <Kpi label="Need CIA rating" value={s?.needs_cia} tone="warning" />
        <Kpi label="Regulated" value={s?.regulated} />
        <Kpi label="Stale > 90d" value={s?.stale} tone="warning" />
      </div>

      {/* Toolbar — search left, actions right, all one line. */}
      <div className="mt-4 flex items-center gap-2">
        <SearchInput
          value={filters.search}
          onChange={(v) => set("search", v)}
          placeholder="Search name, host or IP…"
          className="w-64"
        />
        <div className="ml-auto flex items-center gap-2">
          <Button variant="secondary" onClick={() => navigate("/assets/import")}>
            Import
          </Button>
          <Button onClick={() => navigate("/assets/new")}>New asset</Button>
        </div>
      </div>

      {/* Filters */}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <FilterFacet
          label="Type"
          options={ASSET_TYPES.map((t) => ({ value: t, label: withCount(ASSET_TYPE_META[t].label, facets?.asset_type[t]) }))}
          values={filters.asset_type !== "all" ? [filters.asset_type] : []}
          onChange={(v) => set("asset_type", (v[v.length - 1] as AssetType) ?? "all")}
        />
        <FilterFacet
          label="Criticality"
          options={CRITICALITY_TIERS.map((t) => ({ value: t, label: withCount(TIER_META[t].label, facets?.tier[t]) }))}
          values={filters.tiers}
          onChange={(v) => set("tiers", v as CriticalityTier[])}
        />
        <FilterFacet
          label="Lifecycle"
          options={ASSET_STATUSES.map((st) => ({ value: st, label: withCount(STATUS_META[st].label, facets?.status[st]) }))}
          values={filters.statuses}
          onChange={(v) => set("statuses", v as AssetStatus[])}
        />
        <FilterFacet
          label="Environment"
          options={ENVIRONMENTS.map((e) => ({ value: e, label: withCount(ENVIRONMENT_LABEL[e], facets?.environment[e]) }))}
          values={filters.environments}
          onChange={(v) => set("environments", v as Environment[])}
        />
        <FilterFacet
          label="Classification"
          options={DATA_CLASSIFICATIONS.map((c) => ({ value: c, label: CLASSIFICATION_META[c].label }))}
          values={filters.classifications}
          onChange={(v) => set("classifications", v as DataClassification[])}
        />
        <FilterFacet
          label="Owner"
          options={ownerOptions}
          values={filters.owner ? [filters.owner] : []}
          onChange={(v) => set("owner", v[v.length - 1] ?? null)}
        />
        <button
          type="button"
          onClick={() => set("exposure", filters.exposure === "internet_facing" ? null : "internet_facing")}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-1.5 text-body-sm transition-colors",
            filters.exposure === "internet_facing"
              ? "border-action-accent bg-action-accent-tint text-action-accent"
              : "border-border text-text-secondary hover:border-border-strong",
          )}
        >
          <Icon name="globe" className="size-3.5" />
          Internet-facing
        </button>
        <button
          type="button"
          onClick={() => set("needs_attention", !filters.needs_attention)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-sm border px-2.5 py-1.5 text-body-sm transition-colors",
            filters.needs_attention
              ? "border-status-warning-border bg-status-warning-bg text-status-warning-text"
              : "border-border text-text-secondary hover:border-border-strong",
          )}
        >
          <Icon name="alert" className="size-3.5" />
          Needs attention
          {facets?.needs_attention ? <span className="tabular">· {facets.needs_attention}</span> : null}
        </button>
        {activeCount > 0 || filters.search ? (
          <button
            type="button"
            onClick={() => {
              setFilters(EMPTY);
              setActiveView(null);
              setPage(1);
            }}
            className="text-body-sm font-semibold text-text-link"
          >
            Clear
          </button>
        ) : null}
      </div>

      {/* Saved views — only when the tenant has some. */}
      {savedViews.length > 0 ? (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {savedViews.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => applyView(v)}
              className={cn(
                "rounded-full border px-3 py-1 text-body-sm transition-colors",
                activeView === v.id
                  ? "border-action-accent bg-action-accent-tint text-action-accent"
                  : "border-border bg-surface-primary text-text-secondary hover:border-border-strong",
              )}
            >
              {v.name}
            </button>
          ))}
        </div>
      ) : null}

      {/* Table */}
      <div className="mt-4">
        {query.isLoading ? (
          <TableSkeleton rows={8} />
        ) : query.isError ? (
          <ErrorState
            title="Couldn’t load assets"
            description="The request failed. Retry, or contact support if it keeps happening."
            onRetry={() => void query.refetch()}
          />
        ) : total === 0 ? (
          <EmptyState
            icon="audit"
            title={activeCount || filters.search ? "No assets match these filters" : "No assets yet"}
            description={
              activeCount || filters.search
                ? "Adjust or clear the filters to see more."
                : "Add an asset, or import your inventory from a CSV, to start."
            }
            action={<Button onClick={() => navigate("/assets/new")}>New asset</Button>}
          />
        ) : (
          <Table>
            <THead>
              <TR>
                <TH>Asset</TH>
                <TH>Type</TH>
                <TH>Owner</TH>
                <TH>Criticality</TH>
                <TH>CIA</TH>
                <TH>Lifecycle</TH>
                <TH>Last seen</TH>
                <TH>Value</TH>
                <TH className="w-10" />
              </TR>
            </THead>
            <TBody>
              {query.data!.items.map((a) => (
                <AssetRow
                  key={a.id}
                  asset={a}
                  onOpen={() => navigate(`/assets/${a.id}`)}
                  onEdit={() => navigate(`/assets/${a.id}/edit`)}
                />
              ))}
            </TBody>
          </Table>
        )}
      </div>

      {pageCount > 1 ? (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-body-sm text-text-subtle">
            {total} {total === 1 ? "asset" : "assets"}
          </span>
          <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      ) : null}
    </div>
  );
}

function Kpi({ label, value, tone }: { label: string; value: number | undefined; tone?: "danger" | "warning" }) {
  return (
    <div className="rounded-md border border-border bg-surface-primary px-3.5 py-3">
      <p className="text-caption text-text-subtle">{label}</p>
      <p
        className={cn(
          "mt-1 font-display text-title-lg tabular",
          tone === "danger" ? "text-status-danger-text" : tone === "warning" ? "text-status-warning-text" : "text-text-primary",
        )}
      >
        {value ?? 0}
      </p>
    </div>
  );
}

function CiaCell({ asset }: { asset: Asset }) {
  const { confidentiality: c, integrity: i, availability: a } = asset.criticality;
  if (c == null && i == null && a == null) {
    return <span className="text-caption text-text-subtle">Not rated</span>;
  }
  const fmt = (n: number | null) => (n == null ? "·" : String(n));
  return (
    <span className="font-mono text-body-sm text-text-secondary tabular">
      {fmt(c)}·{fmt(i)}·{fmt(a)}
    </span>
  );
}

function AssetRow({ asset, onOpen, onEdit }: { asset: Asset; onOpen: () => void; onEdit: () => void }) {
  const tier = displayTier(asset.criticality);
  const tierMeta = tier ? TIER_META[tier] : null;
  const regulated = asset.regulated_data_type || asset.compliance_scope.includes("PCI");
  const host = asset.hostname || asset.fqdn || asset.ip_address;
  return (
    <TR onClick={onOpen} className="cursor-pointer">
      <TD>
        <div className="min-w-0">
          <span className="block truncate text-body-md font-medium text-text-primary">{asset.name}</span>
          <span className="flex items-center gap-2 text-caption text-text-subtle">
            {host ? <span className="font-mono">{host}</span> : null}
            {asset.vuln_count > 0 ? <span className="text-status-danger-text">· {asset.vuln_count} vulns</span> : null}
            {regulated ? <Badge variant="warning">Regulated</Badge> : null}
          </span>
        </div>
      </TD>
      <TD>
        <span className="text-body-sm text-text-secondary">{ASSET_TYPE_META[asset.asset_type].label}</span>
      </TD>
      <TD>
        {asset.ownership.primary_owner ? (
          <span className="inline-flex items-center gap-2">
            <Avatar name={asset.ownership.primary_owner.name} size="sm" />
            <span className="text-body-sm text-text-secondary">{asset.ownership.primary_owner.name}</span>
          </span>
        ) : (
          <span className="text-body-sm text-status-warning-text">Unassigned</span>
        )}
      </TD>
      <TD>
        {tier && tierMeta ? (
          <StatusPill status={tierMeta.family} label={tierMeta.label} />
        ) : (
          <span className="text-caption text-text-subtle">Not rated</span>
        )}
      </TD>
      <TD>
        <CiaCell asset={asset} />
      </TD>
      <TD>
        <StatusPill status={STATUS_META[asset.status].family} label={STATUS_META[asset.status].label} />
      </TD>
      <TD>
        <span className={cn("text-body-sm", asset.hygiene.is_stale ? "text-status-danger-text" : "text-text-secondary")}>
          {relativeTime(asset.last_seen_at)}
        </span>
      </TD>
      <TD>
        <span className="text-body-sm text-text-secondary tabular">{fmtMoney(asset.valuation)}</span>
      </TD>
      <TD onClick={(e) => e.stopPropagation()} className="w-10">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              aria-label={`Actions for ${asset.name}`}
              className="inline-flex size-7 items-center justify-center rounded-sm text-text-subtle transition-colors hover:bg-surface-hover"
            >
              <Icon name="more" className="size-4" />
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={onOpen}>View details</DropdownMenuItem>
            <DropdownMenuItem onSelect={onEdit}>Edit</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </TD>
    </TR>
  );
}
