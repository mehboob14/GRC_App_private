import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
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
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
  type ColumnDef,
  StatTile,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { getFacets, getSummary, listAssets, listMembers } from "../api";
import { AssetFormDrawer } from "./asset-form-drawer";
import { useAssetsOutlet } from "./assets-outlet";
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

type SortKey = "name" | "type" | "owner" | "criticality" | "lifecycle" | "lastSeen" | "value";

// Optional columns only. Asset (identity) and the actions column always render.
const COLUMNS = [
  { key: "type", label: "Type" },
  { key: "owner", label: "Owner" },
  { key: "criticality", label: "Criticality" },
  { key: "cia", label: "CIA" },
  { key: "lifecycle", label: "Lifecycle" },
  { key: "lastSeen", label: "Last seen" },
  { key: "value", label: "Value" },
] as const satisfies readonly ColumnDef<string>[];

type ColKey = (typeof COLUMNS)[number]["key"];

const EMPTY: AssetFilters = {
  search: "",
  asset_type: "all",
  tiers: [],
  statuses: [],
  environments: [],
  classifications: [],
  exposure: null,
  owner: null,
};

export function AssetsRegisterPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { addAsset, registerView } = useAssetsOutlet();
  const [filters, setFilters] = useState<AssetFilters>(EMPTY);
  const [page, setPage] = useState(1);
  // Add asset lives in the layout; edit needs the row, so its drawer stays here.
  const [editingId, setEditingId] = useState<string | undefined>(undefined);
  const [formOpen, setFormOpen] = useState(false);
  const openEdit = (id: string) => {
    setEditingId(id);
    setFormOpen(true);
  };
  const onSaved = () => {
    queryClient.invalidateQueries({ queryKey: ["assets"] });
    queryClient.invalidateQueries({ queryKey: ["asset-summary"] });
    queryClient.invalidateQueries({ queryKey: ["asset-facets"] });
  };
  // Export sits in the header and downloads this same page, filters included.
  useEffect(() => {
    registerView.current = { filters, page, pageSize: PAGE_SIZE };
    return () => {
      registerView.current = null;
    };
  }, [registerView, filters, page]);
  const cols = useColumnPrefs("verity.assets.columns", COLUMNS);

  const set = <K extends keyof AssetFilters>(key: K, value: AssetFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };

  const summaryQuery = useQuery({ queryKey: ["asset-summary"], queryFn: getSummary });
  const facetsQuery = useQuery({ queryKey: ["asset-facets"], queryFn: getFacets });
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

  const activeCount =
    filters.tiers.length +
    filters.statuses.length +
    filters.environments.length +
    filters.classifications.length +
    (filters.asset_type !== "all" ? 1 : 0) +
    (filters.exposure ? 1 : 0) +
    (filters.owner ? 1 : 0);

  // Sorts the page the server returned, not the whole register.
  const { thProps, sortRows } = useTableSort<Asset, SortKey>(null, {
    name: (a) => a.name,
    type: (a) => ASSET_TYPE_META[a.asset_type].label,
    owner: (a) => a.ownership.primary_owner?.name ?? null,
    // Hottest tier is the highest number, so "desc" reads critical first.
    criticality: (a) => {
      const tier = displayTier(a.criticality);
      return tier ? CRITICALITY_TIERS.length - CRITICALITY_TIERS.indexOf(tier) : null;
    },
    lifecycle: (a) => STATUS_META[a.status].label,
    lastSeen: (a) => (a.last_seen_at ? new Date(a.last_seen_at) : null),
    value: (a) => a.valuation,
  });

  const listError = query.isError ? describeError(query.error, "asset register") : null;
  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const s = summaryQuery.data;

  return (
    <div>
      {/* Headline metrics — one compact strip. */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatTile icon="box" label="Total assets" value={s?.total ?? 0} />
        <StatTile icon="alert" label="Critical" value={s?.by_tier.critical ?? 0} tone="danger" />
        <StatTile icon="gauge" label="Need CIA rating" value={s?.needs_cia ?? 0} tone="warning" />
        <StatTile icon="shield" label="Regulated" value={s?.regulated ?? 0} tone="progress" />
        <StatTile icon="clock" label="Stale over 90 days" value={s?.stale ?? 0} tone="warning" />
      </div>

      {/* Toolbar: search and filters. Module actions live in the header. */}
      <Toolbar
        searchLabel="Filter assets"
        search={
          <SearchInput
            value={filters.search}
            onChange={(v) => set("search", v)}
            placeholder="Search name, host or IP…"
            aria-label="Search assets"
          />
        }
      >
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
        <FilterFacet
          label="Exposure"
          options={[{ value: "internet_facing", label: "Internet-facing" }]}
          values={filters.exposure === "internet_facing" ? ["internet_facing"] : []}
          onChange={(v) => set("exposure", v.length > 0 ? "internet_facing" : null)}
        />
        {activeCount > 0 || filters.search ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setFilters(EMPTY);
              setPage(1);
            }}
          >
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      {/* Table */}
      <div className="mt-4">
        {query.isLoading ? (
          <TableSkeleton rows={8} />
        ) : listError ? (
          <ErrorState
            title={listError.title}
            description={listError.message}
            referenceId={listError.referenceId}
            onRetry={listError.retryable ? () => void query.refetch() : undefined}
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
            action={<Button onClick={addAsset}>Add asset</Button>}
          />
        ) : (
          <Table actions={<ColumnPicker {...cols} />}>
            <THead>
              <TR>
                <TH {...thProps("name")}>Asset</TH>
                {cols.isVisible("type") ? <TH {...thProps("type")}>Type</TH> : null}
                {cols.isVisible("owner") ? <TH {...thProps("owner")}>Owner</TH> : null}
                {cols.isVisible("criticality") ? <TH {...thProps("criticality")}>Criticality</TH> : null}
                {cols.isVisible("cia") ? <TH>CIA</TH> : null}
                {cols.isVisible("lifecycle") ? <TH {...thProps("lifecycle")}>Lifecycle</TH> : null}
                {cols.isVisible("lastSeen") ? <TH {...thProps("lastSeen")}>Last seen</TH> : null}
                {cols.isVisible("value") ? (
                  <TH numeric {...thProps("value")}>
                    Value
                  </TH>
                ) : null}
                <TH className="w-12">
                  <span className="sr-only">Actions</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {sortRows(query.data!.items).map((a) => (
                <AssetRow
                  key={a.id}
                  asset={a}
                  isVisible={cols.isVisible}
                  onOpen={() => navigate(`/assets/${a.id}`)}
                  onEdit={() => openEdit(a.id)}
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

      <AssetFormDrawer open={formOpen} onOpenChange={setFormOpen} assetId={editingId} onSaved={onSaved} />
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

function AssetRow({
  asset,
  isVisible,
  onOpen,
  onEdit,
}: {
  asset: Asset;
  isVisible: (key: ColKey) => boolean;
  onOpen: () => void;
  onEdit: () => void;
}) {
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
            {regulated ? <Badge variant="countWarn">Regulated</Badge> : null}
          </span>
        </div>
      </TD>
      {isVisible("type") ? (
        <TD>
          <span className="text-body-sm text-text-secondary">{ASSET_TYPE_META[asset.asset_type].label}</span>
        </TD>
      ) : null}
      {isVisible("owner") ? (
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
      ) : null}
      {isVisible("criticality") ? (
        <TD>
          {tier && tierMeta ? (
            <StatusPill status={tierMeta.family} label={tierMeta.label} />
          ) : (
            <span className="text-caption text-text-subtle">Not rated</span>
          )}
        </TD>
      ) : null}
      {isVisible("cia") ? (
        <TD>
          <CiaCell asset={asset} />
        </TD>
      ) : null}
      {isVisible("lifecycle") ? (
        <TD>
          <StatusPill status={STATUS_META[asset.status].family} label={STATUS_META[asset.status].label} />
        </TD>
      ) : null}
      {isVisible("lastSeen") ? (
        <TD>
          <span className={cn("text-body-sm", asset.hygiene.is_stale ? "text-status-danger-text" : "text-text-secondary")}>
            {relativeTime(asset.last_seen_at)}
          </span>
        </TD>
      ) : null}
      {isVisible("value") ? (
        <TD numeric>
          <span className="text-body-sm text-text-secondary">{fmtMoney(asset.valuation)}</span>
        </TD>
      ) : null}
      <TD onClick={(e) => e.stopPropagation()} className="w-12">
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
