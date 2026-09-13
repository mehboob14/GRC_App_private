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
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getFacets, listMembers, listVendors } from "../api";
import type { Vendor, VendorFilters } from "../types";
import {
  CLASSIFICATION_META,
  fmtDate,
  fmtMoney,
  ATTENTION_LABEL,
  HEALTHY_LINE,
  LIFECYCLE_META,
  nextAction,
  TIER_META,
  VENDOR_TYPE_LABEL,
} from "../tokens";
import { TierBadge } from "./tier-badge";
import { useVendorsOutlet } from "./vendors-outlet";

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
type SortKey = "name" | "tier" | "grade" | "owner" | "reassessment" | "value" | "status";

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
  attention: [],
};

/**
 * Filters live in the query string, not in component state.
 *
 * Three things follow from that and none of them are cosmetic: opening a vendor
 * and pressing Back returns the register you left rather than an unfiltered page
 * one; a filtered view can be sent to a colleague; and every tile on the
 * overview is a real link instead of a decoration.
 */
function readFilters(params: URLSearchParams): VendorFilters {
  return {
    search: params.get("search") ?? "",
    vendor_type: params.get("vendor_type"),
    statuses: params.getAll("statuses"),
    tiers: params.getAll("tiers"),
    classifications: params.getAll("classifications"),
    business_units: params.getAll("business_units"),
    owner: params.get("owner"),
    stores_pii: params.get("stores_pii") === "true",
    attention: params.getAll("attention"),
  };
}

function writeFilters(filters: VendorFilters, page: number): URLSearchParams {
  const p = new URLSearchParams();
  if (filters.search) p.set("search", filters.search);
  if (filters.vendor_type) p.set("vendor_type", filters.vendor_type);
  for (const v of filters.statuses) p.append("statuses", v);
  for (const v of filters.tiers) p.append("tiers", v);
  for (const v of filters.classifications) p.append("classifications", v);
  for (const v of filters.business_units) p.append("business_units", v);
  if (filters.owner) p.set("owner", filters.owner);
  if (filters.stores_pii) p.set("stores_pii", "true");
  for (const v of filters.attention) p.append("attention", v);
  if (page > 1) p.set("page", String(page));
  return p;
}

function withCount(label: string, n: number | undefined): string {
  return n === undefined ? label : `${label} (${n})`;
}

export function VendorsRegisterPage() {
  const navigate = useNavigate();
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");

  const [params, setParams] = useSearchParams();
  const filters = useMemo(() => readFilters(params), [params]);
  const page = Number(params.get("page") ?? 1) || 1;
  const { addVendor } = useVendorsOutlet();

  // replace, not push: a reader adjusting four facets should not have to press
  // Back four times to leave the register.
  const apply = (next: VendorFilters, nextPage = 1) =>
    setParams(writeFilters(next, nextPage), { replace: true });

  // Any filter change resets to page 1: staying on page 4 of a narrower result
  // set shows an empty table and reads as "no matches".
  const set = <K extends keyof VendorFilters>(key: K, value: VendorFilters[K]) => {
    apply({ ...filters, [key]: value });
  };
  const setPage = (next: number) => apply(filters, next);
  const clearFilters = () => apply(EMPTY);

  const cols = useColumnPrefs<ColumnKey>("verity.vendors.columns", COLUMNS, [
    "unit",
    "classification",
    "value",
  ]);

  /**
   * Sorting is the server's, so it orders the whole register rather than the
   * twenty-five rows this page happened to return — a client sort over one page
   * of four hundred silently answers a different question from the one asked.
   * The hook still owns the header state and the tri-state toggle; its third
   * click clears the key and the server's risk ranking comes back.
   */
  const { key: sortKey, dir, thProps } = useTableSort<Vendor, SortKey>(null, {
    name: (v) => v.name,
    tier: (v) => (v.tier ? TIER_ORDER[v.tier] : 99),
    grade: (v) => v.current_grade,
    owner: (v) => v.ownership.business_owner_name,
    reassessment: (v) => (v.next_reassessment_on ? new Date(v.next_reassessment_on) : null),
    value: (v) => v.annual_contract_value,
    status: (v) => v.lifecycle_status,
  });

  const query = useQuery({
    queryKey: ["vendors", filters, page, sortKey, dir],
    queryFn: () => listVendors(filters, page, PAGE_SIZE, sortKey, dir),
  });
  const facetsQuery = useQuery({ queryKey: ["vendor-facets"], queryFn: getFacets });
  const membersQuery = useQuery({ queryKey: ["vendor-members"], queryFn: listMembers });

  const facets = facetsQuery.data;


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
    filters.business_units.length > 0 ||
    filters.attention.length > 0;

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
      >
        <FilterFacet
          label="Needs attention"
          options={Object.entries(ATTENTION_LABEL).map(([value, label]) => ({ value, label }))}
          values={filters.attention}
          onChange={(v) => set("attention", v)}
        />
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
            onClick={clearFilters}
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
                ? "Adjust or clear the filters."
                : "Add the third parties you share data or systems with."
            }
            onClearFilters={filtered ? clearFilters : undefined}
            action={
              !filtered && canManage ? (
                <Button onClick={addVendor}>
                  <Icon name="plus" className="size-4" />
                  Add vendor
                </Button>
              ) : undefined
            }
          />
        ) : (
          <Table actions={<ColumnPicker {...cols} />}>
            <THead>
              <TR>
                <TH {...thProps("name")}>Vendor</TH>
                <TH {...thProps("tier")}>Tier</TH>
                {cols.isVisible("status") ? <TH {...thProps("status")}>Status</TH> : null}
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
              {query.data!.items.map((v) => (
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
            {/* A real link, not just a row click: without it there is no
                keyboard access, no ctrl or middle click into a new tab, and no
                URL on hover. stopPropagation so a new-tab click does not also
                navigate the current one. */}
            <Link
              to={`/vendors/${v.id}`}
              onClick={(e) => e.stopPropagation()}
              className="block truncate text-body-md font-semibold text-text-primary hover:underline"
            >
              {v.name}
            </Link>
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
        <TierBadge tier={v.tier} variant="dot" />
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
          {v.business_unit ? (
            <span className="text-body-sm text-text-secondary">{v.business_unit}</span>
          ) : (
            <span className="text-caption text-text-subtle">Not set</span>
          )}
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
            <span className="text-caption text-text-subtle">Not set</span>
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
            <DropdownMenuItem
              onSelect={() => {
                void navigator.clipboard.writeText(
                  `${window.location.origin}/vendors/${v.id}`,
                );
              }}
            >
              Copy link
            </DropdownMenuItem>
            <DropdownMenuItem
              onSelect={() => navigate(`/vendors/${v.id}?tab=${action?.tab ?? "lifecycle"}`)}
            >
              {action ? "View blocker" : "Open lifecycle"}
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
