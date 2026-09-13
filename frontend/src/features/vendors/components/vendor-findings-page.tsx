import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Badge,
  EmptyState,
  ErrorState,
  Icon,
  SegmentedControl,
  SeverityChip,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  Tooltip,
  useTableSort,
  type Severity,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { listFindings } from "../api";
import type { Finding } from "../types";
import { daysUntil, fmtCountdown, FINDING_SOURCE_LABEL, FINDING_STATUS_META } from "../tokens";

type Scope = "open" | "accepted" | "closed" | "all";

const SCOPES = [
  { id: "open" as const, label: "Open" },
  { id: "accepted" as const, label: "Accepted" },
  { id: "closed" as const, label: "Closed" },
  { id: "all" as const, label: "All" },
];

/** Open means still work: raised, or being worked. Accepted is a decision. */
const SCOPE_STATUSES: Record<Scope, string[]> = {
  open: ["open", "in_remediation"],
  accepted: ["accepted"],
  closed: ["closed"],
  all: [],
};

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

/**
 * Every open third-party finding, across every vendor.
 *
 * The server already ranks these by severity then SLA date, so the initial sort
 * key is null and that ranking survives until someone asks for another column.
 */
export function VendorFindingsPage() {
  const [scope, setScope] = useState<Scope>("open");

  const query = useQuery({
    queryKey: ["vendor-findings", { statuses: SCOPE_STATUSES[scope] }],
    queryFn: () => listFindings({ statuses: SCOPE_STATUSES[scope] }),
  });

  const { thProps, sortRows } = useTableSort<Finding, "severity" | "vendor" | "due" | "owner">(
    null,
    {
      severity: (f) => SEVERITY_ORDER[f.severity] ?? 9,
      vendor: (f) => f.vendor_name,
      due: (f) => (f.sla_due ? new Date(f.sla_due) : null),
      owner: (f) => f.owner_name,
    },
  );

  const listError = query.isError ? describeError(query.error, "findings") : null;
  const items = query.data?.items ?? [];
  const blocking = items.filter((f) => f.is_blocking).length;

  return (
    <div>
      <Toolbar>
        <SegmentedControl items={SCOPES} value={scope} onChange={setScope} label="Finding scope" />
        {blocking > 0 ? (
          <span className="inline-flex items-center gap-1.5 text-body-sm text-status-danger-text">
            <Icon name="alert" className="size-4 shrink-0" />
            {blocking} {blocking === 1 ? "finding" : "findings"} blocking approval
          </span>
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
        ) : items.length === 0 ? (
          <EmptyState
            icon="check"
            variant={scope === "open" ? "no-data" : "no-match"}
            title={scope === "open" ? "No open findings" : "Nothing in this state"}
            description={
              scope === "open"
                ? "Raised from questionnaire scoring and document reviews."
                : "Try another filter."
            }
          />
        ) : (
          <Table density="standard">
            <THead>
              <TR>
                <TH {...thProps("severity")}>Severity</TH>
                <TH>Finding</TH>
                <TH {...thProps("vendor")}>Vendor</TH>
                <TH>Status</TH>
                <TH {...thProps("due")}>Remediation due</TH>
                <TH {...thProps("owner")}>Owner</TH>
                <TH>Raised by</TH>
              </TR>
            </THead>
            <TBody>
              {sortRows(items).map((f) => (
                <FindingRow key={f.id} finding={f} />
              ))}
            </TBody>
          </Table>
        )}
      </div>
    </div>
  );
}

function FindingRow({ finding: f }: { finding: Finding }) {
  const status = FINDING_STATUS_META[f.status] ?? { label: f.status, family: "neutral" as const };
  const due = daysUntil(f.sla_due);
  const overdue = due !== null && due < 0 && (f.status === "open" || f.status === "in_remediation");

  return (
    <TR>
      <TD>
        <SeverityChip
          severity={f.severity as Severity}
          label={f.severity.charAt(0).toUpperCase() + f.severity.slice(1)}
        />
      </TD>
      <TD>
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-body-md text-text-primary">
            <span className="truncate font-semibold">{f.title}</span>
            {f.is_blocking ? (
              <Tooltip content="Blocks approval until closed or accepted">
                <span className="shrink-0">
                  <Badge variant="statusFail">Blocking</Badge>
                </span>
              </Tooltip>
            ) : null}
          </p>
          {f.detail ? <p className="truncate text-caption text-text-subtle">{f.detail}</p> : null}
        </div>
      </TD>
      <TD>
        <Link
          to={`/vendors/${f.vendor_id}?tab=findings`}
          className="text-body-sm text-text-link underline-offset-2 hover:underline"
        >
          {f.vendor_name ?? "Open vendor"}
        </Link>
      </TD>
      <TD>
        <StatusPill status={status.family} label={status.label} kind="inline" />
        {f.status === "accepted" && f.accepted_until ? (
          <p className="mt-0.5 text-caption text-text-subtle">until {f.accepted_until}</p>
        ) : null}
      </TD>
      <TD>
        {f.sla_due ? (
          <span
            className={cn(
              "tabular text-body-sm",
              overdue ? "text-status-danger-text" : "text-text-secondary",
            )}
          >
            {fmtCountdown(due)}
          </span>
        ) : (
          <span className="text-caption text-text-subtle">No date</span>
        )}
      </TD>
      <TD>
        <span className="text-body-sm text-text-secondary">{f.owner_name ?? "Unassigned"}</span>
      </TD>
      <TD>
        <span className="text-body-sm text-text-secondary">
          {FINDING_SOURCE_LABEL[f.finding_source] ?? f.finding_source}
        </span>
      </TD>
    </TR>
  );
}
