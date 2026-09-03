import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ColumnPicker,
  type ColumnDef,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  KevBadge,
  PageHeader,
  SearchInput,
  Table,
  TableSkeleton,
  TabStrip,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import {
  downloadVulnImportTemplate,
  listAssetOptions,
  listVulnerabilities,
  vulnerabilityKpis,
} from "../api";
import type { Severity, VulnInstance, VulnListFilters } from "../types";
import { STATE_META } from "../tokens";
import { SeverityBadge } from "./severity-badge";
import { vulnerabilityTabs } from "./vulnerability-tabs";
import { AddFindingDrawer } from "./add-finding-drawer";
import {
  CveCell,
  CvssCell,
  CweCell,
  EpssCell,
  ExploitCell,
  OwnerCell,
  parseAttackVector,
  PatchCell,
  PriorityContextualCell,
  shortenTitle,
  VectorCell,
} from "./register-cells";

const SEVERITIES: Severity[] = ["critical", "high", "medium", "low"];

/** Sort rank so the Severity column orders by danger, not alphabetically. */
const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

const SEVERITY_OPTIONS = SEVERITIES.map((s) => ({
  value: s,
  label: s.charAt(0).toUpperCase() + s.slice(1),
}));

const EXPLOIT_OPTIONS = [
  { value: "yes", label: "Has public exploit" },
  { value: "no", label: "No public exploit" },
];

const FLAG_OPTIONS = [
  { value: "kev", label: "Known exploited (KEV)" },
  { value: "overdue", label: "Overdue" },
];

type SortKey =
  | "severity"
  | "finding"
  | "cve"
  | "cvss"
  | "epss"
  | "vector"
  | "asset"
  | "priority_ctx"
  | "state"
  | "owner"
  | "sla";

/** Optional columns. Finding identifies the row, so it always renders. Columns
 *  match the reference register left→right: face-value → evidence → verdict. */
const COLUMNS = [
  { key: "id", label: "ID" },
  { key: "cve", label: "CVE" },
  { key: "cwe", label: "CWE" },
  { key: "severity", label: "Severity" },
  { key: "cvss", label: "CVSS" },
  { key: "epss", label: "EPSS" },
  { key: "vector", label: "Vector" },
  { key: "exploit", label: "Exploit" },
  { key: "patch", label: "Patch" },
  { key: "kev", label: "KEV" },
  { key: "asset", label: "Asset" },
  { key: "priority_ctx", label: "Priority · Contextual" },
  { key: "state", label: "State" },
  { key: "sla", label: "SLA" },
  { key: "owner", label: "Owner" },
] as const satisfies readonly ColumnDef<string>[];

type ColKey = (typeof COLUMNS)[number]["key"];

/** Kept out of the default view to keep the table readable; all reachable via
 *  the Columns picker. */
const DEFAULT_HIDDEN: ColKey[] = ["exploit", "patch", "kev"];

function fmtDue(iso: string | null, overdue: boolean): string {
  if (!iso) return "No SLA";
  const d = new Date(iso);
  const label = d.toLocaleDateString(undefined, { day: "numeric", month: "short" });
  return overdue ? `Overdue (${label})` : `Due ${label}`;
}

function Kpi({ label, value, tone }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary px-4 py-3">
      <p className="text-caption text-text-subtle">{label}</p>
      <p className={cn("mt-1 font-display text-heading-md tabular", tone ?? "text-text-primary")}>
        {value}
      </p>
    </div>
  );
}

export function VulnerabilitiesRegisterPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const assetIdParam = params.get("asset_id") ?? undefined;

  const [filters, setFilters] = useState<VulnListFilters>({
    state: "open",
    kev_only: params.get("kev") === "1",
    overdue_only: params.get("overdue") === "1",
  });
  const [search, setSearch] = useState("");
  const [exploit, setExploit] = useState<"all" | "yes" | "no">("all");
  const [addOpen, setAddOpen] = useState(false);

  const set = <K extends keyof VulnListFilters>(key: K, value: VulnListFilters[K]) =>
    setFilters((f) => ({ ...f, [key]: value }));

  // Asset facet: prefer the URL param, else the picked facet value.
  const assetId = assetIdParam ?? filters.asset_id;
  const effective: VulnListFilters = { ...filters, asset_id: assetId, search: search || undefined };

  const kpisQuery = useQuery({ queryKey: ["vuln-kpis"], queryFn: vulnerabilityKpis });
  const listQuery = useQuery({
    queryKey: ["vulnerabilities", effective],
    queryFn: () => listVulnerabilities(effective),
  });
  // Asset facet options (shared with the overview's cache).
  const assetOptQuery = useQuery({ queryKey: ["vuln-asset-options"], queryFn: listAssetOptions });

  // Exploit is a client-side facet (no server param): filter after fetch.
  const rows = useMemo(() => {
    const r = listQuery.data ?? [];
    if (exploit === "all") return r;
    return r.filter((v) =>
      exploit === "yes" ? (v.public_exploit_count ?? 0) > 0 : (v.public_exploit_count ?? 0) === 0,
    );
  }, [listQuery.data, exploit]);

  const listError = describeError(listQuery.error, "vulnerability register");

  const assetOptions = useMemo(
    () => (assetOptQuery.data ?? []).map((a) => ({ value: a.id, label: a.name })),
    [assetOptQuery.data],
  );

  const handleExport = () => {
    const cols = [
      "id", "title", "cve_id", "cwe_id", "severity", "cvss_score", "cvss_vector",
      "epss_score", "priority_band", "risk_score", "state", "kev_flag",
      "public_exploit_count", "patch_available", "asset_name", "owner_name",
      "sla_due_at", "overdue",
    ] as const;
    const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
    const lines = rows.map((v) =>
      cols.map((c) => esc(v[c] == null ? "" : String(v[c]))).join(","),
    );
    const csv = `${cols.join(",")}\n${lines.join("\n")}\n`;
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "vulnerabilities.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const k = kpisQuery.data;
  const cols = useColumnPrefs("verity.vulnerabilities.columns", COLUMNS, DEFAULT_HIDDEN);

  const flagValues = [
    ...(filters.kev_only ? ["kev"] : []),
    ...(filters.overdue_only ? ["overdue"] : []),
  ];
  const dirty =
    Boolean(filters.severity) ||
    Boolean(filters.asset_id) ||
    exploit !== "all" ||
    flagValues.length > 0 ||
    search !== "";

  const { thProps, sortRows } = useTableSort<VulnInstance, SortKey>(
    null,
    {
      severity: (v) => SEVERITY_RANK[v.severity] ?? 99,
      finding: (v) => v.title,
      cve: (v) => v.cve_id,
      cvss: (v) => v.cvss_score,
      epss: (v) => v.epss_score,
      vector: (v) => parseAttackVector(v.cvss_vector),
      asset: (v) => v.asset_name,
      priority_ctx: (v) => v.risk_score,
      state: (v) => STATE_META[v.state].label,
      owner: (v) => v.owner_name,
      sla: (v) => v.sla_due_at,
    },
    "desc",
  );

  const sorted = sortRows(rows);

  return (
    <div className="w-full">
      <PageHeader eyebrow="Risk" title="Vulnerabilities" />
      <TabStrip label="Vulnerability sections" items={vulnerabilityTabs(k?.open_total)} />

      {kpisQuery.isError ? (
        <p className="mb-4 text-body-sm text-status-danger-text">
          {describeError(kpisQuery.error, "summary").message}
        </p>
      ) : (
        <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Kpi label="Open" value={k?.open_total ?? 0} />
          <Kpi label="Overdue" value={k?.overdue ?? 0} tone={k?.overdue ? "text-status-danger-text" : undefined} />
          <Kpi label="Known exploited (KEV)" value={k?.kev_open ?? 0} tone={k?.kev_open ? "text-status-danger-text" : undefined} />
          <Kpi label="Accepted" value={k?.accepted ?? 0} />
        </div>
      )}

      <Toolbar
        searchLabel="Filter vulnerabilities"
        search={
          <SearchInput
            placeholder="Search by title or CVE…"
            value={search}
            onChange={setSearch}
            aria-label="Search vulnerabilities"
          />
        }
        actions={
          <>
            <Button variant="secondary" onClick={handleExport}>
              <Icon name="download" className="size-4" />
              Export
            </Button>
            <Button variant="secondary" onClick={() => downloadVulnImportTemplate()}>
              <Icon name="spreadsheet" className="size-4" />
              Template
            </Button>
            <Button variant="secondary" onClick={() => navigate("/vulnerabilities/import")}>
              <Icon name="upload" className="size-4" />
              Bulk upload
            </Button>
            <Button onClick={() => setAddOpen(true)}>
              <Icon name="plus" className="size-4" />
              Add vulnerability
            </Button>
          </>
        }
      >
        <FilterFacet
          label="Severity"
          options={SEVERITY_OPTIONS}
          values={filters.severity ? [filters.severity] : []}
          onChange={(values) =>
            set("severity", values.find((v) => v !== filters.severity) as Severity | undefined)
          }
        />
        {!assetIdParam ? (
          <FilterFacet
            label="Asset"
            options={assetOptions}
            searchable
            values={filters.asset_id ? [filters.asset_id] : []}
            onChange={(values) =>
              set("asset_id", values.find((v) => v !== filters.asset_id) ?? undefined)
            }
          />
        ) : null}
        <FilterFacet
          label="Exploit"
          options={EXPLOIT_OPTIONS}
          values={exploit !== "all" ? [exploit] : []}
          onChange={(values) => setExploit((values.find((v) => v !== exploit) as "yes" | "no") ?? "all")}
        />
        <FilterFacet
          label="Flags"
          options={FLAG_OPTIONS}
          values={flagValues}
          onChange={(values) =>
            setFilters((f) => ({
              ...f,
              kev_only: values.includes("kev"),
              overdue_only: values.includes("overdue"),
            }))
          }
        />
        {dirty ? (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch("");
              setExploit("all");
              setFilters((f) => ({ state: f.state }));
            }}
          >
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      {listQuery.isLoading ? (
        <TableSkeleton rows={8} />
      ) : listQuery.isError ? (
        <ErrorState
          title={listError.title}
          description={listError.message}
          referenceId={listError.referenceId}
          onRetry={listError.retryable ? () => void listQuery.refetch() : undefined}
        />
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No vulnerabilities"
          description="Import a scanner export or add a finding to get started."
        />
      ) : (
        <div className="mt-3">
        <Table actions={<ColumnPicker {...cols} />}>
          <THead>
            <TR>
              {cols.isVisible("id") ? <TH>ID</TH> : null}
              <TH {...thProps("finding")}>Finding</TH>
              {cols.isVisible("cve") ? <TH {...thProps("cve")}>CVE</TH> : null}
              {cols.isVisible("cwe") ? <TH>CWE</TH> : null}
              {cols.isVisible("severity") ? <TH {...thProps("severity")}>Severity</TH> : null}
              {cols.isVisible("cvss") ? <TH {...thProps("cvss")}>CVSS</TH> : null}
              {cols.isVisible("epss") ? <TH {...thProps("epss")}>EPSS</TH> : null}
              {cols.isVisible("vector") ? <TH {...thProps("vector")}>Vector</TH> : null}
              {cols.isVisible("exploit") ? <TH>Exploit</TH> : null}
              {cols.isVisible("patch") ? <TH>Patch</TH> : null}
              {cols.isVisible("kev") ? <TH>KEV</TH> : null}
              {cols.isVisible("asset") ? <TH {...thProps("asset")}>Asset</TH> : null}
              {cols.isVisible("priority_ctx") ? <TH {...thProps("priority_ctx")}>Priority · Contextual</TH> : null}
              {cols.isVisible("state") ? <TH {...thProps("state")}>State</TH> : null}
              {cols.isVisible("sla") ? <TH {...thProps("sla")}>SLA</TH> : null}
              {cols.isVisible("owner") ? <TH {...thProps("owner")}>Owner</TH> : null}
            </TR>
          </THead>
          <TBody>
            {sorted.map((v) => (
              <Row key={v.id} v={v} isVisible={cols.isVisible} onOpen={() => navigate(`/vulnerabilities/${v.id}`)} />
            ))}
          </TBody>
        </Table>
        </div>
      )}

      <AddFindingDrawer open={addOpen} onOpenChange={setAddOpen} />
    </div>
  );
}

function Row({
  v,
  isVisible,
  onOpen,
}: {
  v: VulnInstance;
  isVisible: (key: ColKey) => boolean;
  onOpen: () => void;
}) {
  const state = STATE_META[v.state];
  return (
    <TR onClick={onOpen} className="cursor-pointer">
      {isVisible("id") ? (
        <TD>
          <span className="font-mono text-caption text-text-subtle">VULN-{v.id.slice(0, 6).toUpperCase()}</span>
        </TD>
      ) : null}
      <TD>
        <span className="block max-w-[320px] truncate text-body-sm font-semibold text-text-primary" title={v.title}>
          {shortenTitle(v.title)}
        </span>
      </TD>
      {isVisible("cve") ? <TD><CveCell cve={v.cve_id} /></TD> : null}
      {isVisible("cwe") ? <TD><CweCell cwe={v.cwe_id} /></TD> : null}
      {isVisible("severity") ? <TD><SeverityBadge severity={v.severity} /></TD> : null}
      {isVisible("cvss") ? <TD><CvssCell score={v.cvss_score} /></TD> : null}
      {isVisible("epss") ? <TD><EpssCell score={v.epss_score} percentile={v.epss_percentile} /></TD> : null}
      {isVisible("vector") ? <TD><VectorCell vector={v.cvss_vector} /></TD> : null}
      {isVisible("exploit") ? <TD><ExploitCell count={v.public_exploit_count} /></TD> : null}
      {isVisible("patch") ? <TD><PatchCell available={v.patch_available} /></TD> : null}
      {isVisible("kev") ? <TD>{v.kev_flag ? <KevBadge /> : <span className="text-caption text-text-subtle">—</span>}</TD> : null}
      {isVisible("asset") ? (
        <TD>
          <Link
            to={`/assets/${v.asset_id}`}
            onClick={(e) => e.stopPropagation()}
            className="text-body-sm text-text-secondary hover:text-text-link"
            title={v.asset_host ?? undefined}
          >
            {v.asset_name}
          </Link>
        </TD>
      ) : null}
      {isVisible("priority_ctx") ? <TD><PriorityContextualCell v={v} /></TD> : null}
      {isVisible("state") ? <TD><Badge variant={state.variant}>{state.label}</Badge></TD> : null}
      {isVisible("sla") ? (
        <TD>
          <span className={cn("text-caption", v.overdue ? "font-semibold text-status-danger-text" : "text-text-subtle")}>
            {fmtDue(v.sla_due_at, v.overdue)}
          </span>
          {v.escalation_level > 0 ? (
            <span className="ml-1.5 text-caption font-semibold text-status-danger-text">· escalated</span>
          ) : null}
        </TD>
      ) : null}
      {isVisible("owner") ? <TD><OwnerCell name={v.owner_name} /></TD> : null}
    </TR>
  );
}
