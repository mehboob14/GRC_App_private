import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getFacets, listMembers, listVendors } from "../api";
import type { Vendor, VendorFilters } from "../types";
import {
  CLASSIFICATION_META,
  fmtDate,
  fmtMoney,
  HEALTHY_LINE,
  LIFECYCLE_META,
  nextAction,
  NOT_TIERED,
  TIER_META,
  VENDOR_TYPE_LABEL,
} from "../tokens";
import { VendorFormDrawer } from "./vendor-form-drawer";
import { RequestVendorDialog } from "./request-vendor-dialog";

const PAGE_SIZE = 25;

/**
 * Only the optional columns belong here — the vendor name, the next action and
 * the row actions are never toggleable. The next action is the reason this
 * register exists: a list of vendors tells you nothing, a list of what each one
 * is waiting on is a work queue.
 */
const COLUMNS = [
  { key: "status", label: "Status" },
  { key: "grade", label: "Residual grade" },
  { key: "owner", label: "Business owner" },
  { key: "unit", label: "Business unit" },
  { key: "classification", label: "Data classification" },
  { key: "reassessment", label: "Next reassessment" },
  { key: "value", label: "Annual value" },
] as const satisfies readonly ColumnDef<string>[];

type ColumnKey = (typeof COLUMNS)[number]["key"];
type SortKey = "name" | "tier" | "grade" | "owner" | "reassessment" | "value";

/** Worst first, so sorting by tier ranks risk rather than the alphabet. */
const TIER_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

const EMPTY: VendorFilters = {
  search: "",
  vendor_type: null,
  statuses: [],
  tiers: [],
  classifications: [],
  business_units: [],
  owner: null,
  stores_pii: false,
};

function withCount(label: string, n: number | undefined): string {
  return n === undefined ? label : `${label} (${n})`;
}

export function VendorsRegisterPage() {
  const navigate = useNavigate();
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const canRead = hasPermission(principal, "vendors:read");

  const [filters, setFilters] = useState<VendorFilters>(EMPTY);
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [requestOpen, setRequestOpen] = useState(false);

  // Any filter change resets to page 1: staying on page 4 of a narrower result
  // set shows an empty table and reads as "no matches".
  const set = <K extends keyof VendorFilters>(key: K, value: VendorFilters[K]) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };

  const cols = useColumnPrefs<ColumnKey>("verity.vendors.columns", COLUMNS, [
    "unit",
    "classification",
    "value",
  ]);

  const query = useQuery({
    queryKey: ["vendors", filters, page],
    queryFn: () => listVendors(filters, page, PAGE_SIZE),
  });
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  const facets = facetsQuery.data;

  /**
   * Sorting is client-side over the page the server returned. The register's
   * server order is deliberate — worst tier first, then unowned, then
   * alphabetical — so the initial key is null and that ranking survives until
   * someone asks for something else. There is no `sort` query parameter.
   */
  const { thProps, sortRows } = useTableSort<Vendor, SortKey>(null, {
    name: (v) => v.name,
    tier: (v) => (v.tier ? TIER_ORDER[v.tier] : 99),
    grade: (v) => v.current_grade,
    owner: (v) => v.ownership.business_owner_name,
    reassessment: (v) => (v.next_reassessment_on ? new Date(v.next_reassessment_on) : null),
    value: (v) => v.annual_contract_value,
  });

  const listError = query.isError ? describeError(query.error, "vendor register") : null;
  const total = query.data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const filtered =
    filters.search !== "" ||
    filters.vendor_type !== null ||
    filters.owner !== null ||
    filters.stores_pii ||
    filters.statuses.length > 0 ||
    filters.tiers.length > 0 ||
    filters.classifications.length > 0 ||
    filters.business_units.length > 0;

  const ownerOptions = [
    { value: "me", label: "Mine" },
    { value: "unassigned", label: "Unassigned" },
    ...(membersQuery.data ?? []).map((m) => ({ value: m.membership_id, label: m.name })),
  ];

  return (
    <div>
      <Toolbar
        searchLabel="Filter vendors"
        search={
          <SearchInput
            value={filters.search}
            onChange={(v) => set("search", v)}
            placeholder="Search name, service or industry…"
            aria-label="Search vendors"
          />
        }
        actions={
          <>
            {canRead && !canManage ? (
              <Button variant="secondary" onClick={() => setRequestOpen(true)}>
                <Icon name="plus" className="size-4" />
                Request a vendor
              </Button>
            ) : null}
            {canManage ? (
              <Button onClick={() => setFormOpen(true)}>
                <Icon name="plus" className="size-4" />
                Add vendor
              </Button>
            ) : null}
          </>
        }
      >
        <FilterFacet
          label="Tier"
          options={(facets?.tiers ?? Object.keys(TIER_META)).map((t) => ({
            value: t,
            label: TIER_META[t]?.label ?? t,
          }))}
          values={filters.tiers}
          onChange={(v) => set("tiers", v)}
        />
        <FilterFacet
          label="Status"
          options={(facets?.statuses ?? []).map((s) => ({
            value: s,
            label: LIFECYCLE_META[s]?.label ?? s,
          }))}
          values={filters.statuses}
          onChange={(v) => set("statuses", v)}
        />
        <FilterFacet
          label="Type"
          options={(facets?.vendor_types ?? []).map((t) => ({
            value: t,
            label: VENDOR_TYPE_LABEL[t] ?? t,
          }))}
          // Single-select by convention: keep only the last value chosen.
          values={filters.vendor_type ? [filters.vendor_type] : []}
          onChange={(v) => set("vendor_type", v[v.length - 1] ?? null)}
        />
        <FilterFacet
          label="Business owner"
          options={ownerOptions}
          values={filters.owner ? [filters.owner] : []}
          onChange={(v) => set("owner", v[v.length - 1] ?? null)}
          searchable
        />
        <FilterFacet
          label="Data"
          options={[{ value: "pii", label: withCount("Stores personal data", undefined) }]}
          values={filters.stores_pii ? ["pii"] : []}
          onChange={(v) => set("stores_pii", v.includes("pii"))}
        />
        {facets?.business_units.length ? (
          <FilterFacet
            label="Business unit"
            options={facets.business_units.map((b) => ({ value: b, label: b }))}
            values={filters.business_units}
            onChange={(v) => set("business_units", v)}
          />
        ) : null}
        {filtered ? (
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

      <div className="mt-4">
        {query.isError ? (
          <ErrorState
            title={listError!.title}
            description={listError!.message}
            referenceId={listError!.referenceId}
            onRetry={listError!.retryable ? () => void query.refetch() : undefined}
          />
        ) : query.isLoading ? (
          <TableSkeleton rows={8} />
        ) : total === 0 ? (
          <EmptyState
            icon="vendor"
            variant={filtered ? "no-match" : "no-data"}
            title={filtered ? "No vendors match these filters" : "No vendors yet"}
            description={
              filtered
                ? "Adjust or clear the filters to see more."
                : "Add the third parties you share data or systems with. Tier each one, then work its lifecycle from intake to approval."
            }
            onClearFilters={
              filtered
                ? () => {
                    setFilters(EMPTY);
                    setPage(1);
                  }
                : undefined
            }
            action={
              !filtered && canManage ? (
                <Button onClick={() => setFormOpen(true)}>Add vendor</Button>
              ) : undefined
            }
          />
        ) : (
          <Table actions={<ColumnPicker {...cols} />}>
            <THead>
              <TR>
                <TH {...thProps("name")}>Vendor</TH>
                <TH {...thProps("tier")}>Tier</TH>
                {cols.isVisible("status") ? <TH>Status</TH> : null}
                <TH>Blocker / next action</TH>
                {cols.isVisible("grade") ? <TH {...thProps("grade")}>Grade</TH> : null}
                {cols.isVisible("owner") ? <TH {...thProps("owner")}>Business owner</TH> : null}
                {cols.isVisible("unit") ? <TH>Business unit</TH> : null}
                {cols.isVisible("classification") ? <TH>Classification</TH> : null}
                {cols.isVisible("reassessment") ? (
                  <TH {...thProps("reassessment")}>Next reassessment</TH>
                ) : null}
                {cols.isVisible("value") ? (
                  <TH numeric {...thProps("value")}>
                    Annual value
                  </TH>
                ) : null}
                <TH className="w-12">
                  <span className="sr-only">Actions</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {sortRows(query.data!.items).map((v) => (
                <VendorRow
                  key={v.id}
                  vendor={v}
                  isVisible={cols.isVisible}
                  onOpen={() => navigate(`/vendors/${v.id}`)}
                />
              ))}
            </TBody>
          </Table>
        )}
      </div>

      {pageCount > 1 ? (
        <div className="mt-4 flex items-center justify-between">
          <span className="text-body-sm text-text-subtle">
            {total} {total === 1 ? "vendor" : "vendors"}
          </span>
          <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      ) : null}

      <VendorFormDrawer open={formOpen} onOpenChange={setFormOpen} />
      <RequestVendorDialog open={requestOpen} onOpenChange={setRequestOpen} />
    </div>
  );
}

function VendorRow({
  vendor: v,
  isVisible,
  onOpen,
}: {
  vendor: Vendor;
  isVisible: (key: ColumnKey) => boolean;
  onOpen: () => void;
}) {
  const navigate = useNavigate();
  const tier = v.tier ? (TIER_META[v.tier] ?? NOT_TIERED) : NOT_TIERED;
  const status = LIFECYCLE_META[v.lifecycle_status] ?? {
    label: v.lifecycle_status,
    family: "neutral" as const,
  };
  const action = nextAction(v);
  const owner = v.ownership.business_owner_name;

  return (
    <TR onClick={onOpen} className="cursor-pointer">
      <TD>
        <div className="flex min-w-0 items-center gap-2.5">
          <Avatar name={v.name} seed={v.id} size="sm" />
          <div className="min-w-0">
            <p className="truncate text-body-md font-semibold text-text-primary">{v.name}</p>
            <p className="truncate text-caption text-text-subtle">
              {[VENDOR_TYPE_LABEL[v.vendor_type] ?? v.vendor_type, v.industry]
                .filter(Boolean)
                .join(" · ")}
            </p>
          </div>
          {v.stores_pii ? (
            <Tooltip content="Holds personal data">
              <span className="shrink-0">
                <Badge variant="countWarn">PII</Badge>
              </span>
            </Tooltip>
          ) : null}
        </div>
      </TD>
      <TD>
        <StatusPill status={tier.family} label={tier.label} kind="inline" />
      </TD>
      {isVisible("status") ? (
        <TD>
          <StatusPill status={status.family} label={status.label} kind="inline" />
        </TD>
      ) : null}
      <TD>
        {action ? (
          <span
            className={cn(
              "inline-flex items-center gap-1.5 text-body-sm",
              action.family === "danger"
                ? "text-status-danger-text"
                : action.family === "warning"
                  ? "text-status-warning-text"
                  : "text-status-progress-text",
            )}
          >
            <Icon
              name={action.family === "progress" ? "clock" : "alert"}
              className="size-3.5 shrink-0"
            />
            {action.label}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 text-body-sm text-text-subtle">
            <Icon name="check" className="size-3.5 shrink-0 text-status-success-base" />
            {HEALTHY_LINE}
          </span>
        )}
      </TD>
      {isVisible("grade") ? (
        <TD>
          {v.current_grade ? (
            <span className="tabular text-body-md font-semibold text-text-primary">
              {v.current_grade}
              {v.current_residual_score !== null ? (
                <span className="ml-1.5 text-caption font-normal text-text-subtle">
                  {v.current_residual_score}
                </span>
              ) : null}
            </span>
          ) : (
            <span className="text-caption text-text-subtle">Not scored</span>
          )}
        </TD>
      ) : null}
      {isVisible("owner") ? (
        <TD>
          {owner ? (
            <div className="flex items-center gap-2">
              <Avatar name={owner} seed={v.ownership.business_owner_membership_id ?? owner} size="sm" />
              <span className="truncate text-body-sm text-text-secondary">{owner}</span>
            </div>
          ) : (
            <span className="text-caption text-text-subtle">Unassigned</span>
          )}
        </TD>
      ) : null}
      {isVisible("unit") ? (
        <TD>
          <span className="text-body-sm text-text-secondary">{v.business_unit || "—"}</span>
        </TD>
      ) : null}
      {isVisible("classification") ? (
        <TD>
          {v.data_classification ? (
            <StatusPill
              status={CLASSIFICATION_META[v.data_classification]?.family ?? "neutral"}
              label={CLASSIFICATION_META[v.data_classification]?.label ?? v.data_classification}
              kind="inline"
            />
          ) : (
            <span className="text-caption text-text-subtle">—</span>
          )}
        </TD>
      ) : null}
      {isVisible("reassessment") ? (
        <TD>
          <span className="tabular text-body-sm text-text-secondary">
            {fmtDate(v.next_reassessment_on)}
          </span>
        </TD>
      ) : null}
      {isVisible("value") ? (
        <TD numeric>
          <span className="text-body-sm text-text-secondary">
            {fmtMoney(v.annual_contract_value)}
          </span>
        </TD>
      ) : null}
      <TD onClick={(e) => e.stopPropagation()} className="w-12">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <TableIconButton aria-label={`Actions for ${v.name}`}>
              <Icon name="more" className="size-4" />
            </TableIconButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onSelect={() => navigate(`/vendors/${v.id}`)}>
              Open vendor
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => navigate(`/vendors/${v.id}?tab=${action?.tab ?? "lifecycle"}`)}
            >
              {action ? "Go to what is blocking" : "Open the lifecycle"}
            </DropdownMenuItem>
            {v.website ? (
              <DropdownMenuItem onSelect={() => window.open(v.website!, "_blank", "noopener")}>
                Visit website
              </DropdownMenuItem>
            ) : null}
          </DropdownMenuContent>
        </DropdownMenu>
      </TD>
    </TR>
  );
}
