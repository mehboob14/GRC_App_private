import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button, ErrorState, Skeleton, TextField, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getSlaPolicy, setSlaPolicy } from "../api";
import type { Severity, SlaPolicy } from "../types";

const SEVERITY_ORDER: Severity[] = ["critical", "high", "medium", "low", "info"];

const SEVERITY_LABEL: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
  info: "Info",
};

/** Shipped defaults (backend `scoring.py`), shown so a blank row reads as a
 *  deliberate default rather than a missing value. */
const DEFAULT_DAYS: Record<Severity, number | null> = {
  critical: 15,
  high: 30,
  medium: 60,
  low: 90,
  info: null,
};

export function VulnerabilitiesSettingsPage() {
  const { principal } = useAuth();
  const canEdit = hasPermission(principal, "vulnerabilities:manage");
  return <SlaCard canEdit={canEdit} />;
}

function SlaCard({ canEdit }: { canEdit: boolean }) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const slaQuery = useQuery({ queryKey: ["vuln-sla"], queryFn: getSlaPolicy });

  const save = useMutation({
    mutationFn: ({ severity, days }: { severity: Severity; days: number | null }) =>
      setSlaPolicy(severity, days),
    onSuccess: (rows) => {
      queryClient.setQueryData(["vuln-sla"], rows);
      toast({ title: "Remediation window saved", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "SLA policy"), tone: "danger" }),
  });

  return (
    <div className="mt-4 max-w-[720px] rounded-lg border border-border bg-surface-primary p-5">
      <h2 className="font-display text-title-sm text-text-primary">Remediation windows</h2>
      <p className="mt-1 text-body-sm text-text-secondary">
        How long a finding of each severity may stay open before it is overdue. The clock starts
        when the finding is first detected.
      </p>
      {!canEdit ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          You can view these settings. Editing needs the Manage vulnerabilities permission.
        </p>
      ) : null}

      {slaQuery.isPending ? (
        <div className="mt-4 space-y-2">
          {SEVERITY_ORDER.map((s) => (
            <Skeleton key={s} className="h-12 w-full rounded-md" />
          ))}
        </div>
      ) : slaQuery.isError ? (
        <div className="mt-4">
          <ErrorState
            title={describeError(slaQuery.error, "SLA policy").title}
            description={describeError(slaQuery.error, "SLA policy").message}
            onRetry={() => void slaQuery.refetch()}
          />
        </div>
      ) : (
        <ul className="mt-4 divide-y divide-border">
          {SEVERITY_ORDER.map((severity) => (
            <SlaRow
              key={severity}
              severity={severity}
              rows={slaQuery.data ?? []}
              canEdit={canEdit}
              saving={save.isPending && save.variables?.severity === severity}
              onSave={(days) => save.mutate({ severity, days })}
            />
          ))}
        </ul>
      )}

      <p className="mt-4 border-t border-border pt-3 text-caption text-text-subtle">
        A change applies to findings detected from now on; it does not move the due date on
        findings that already exist. Leave a window empty to use the default. Findings are flagged
        "due soon" in their last 7 days.
      </p>
    </div>
  );
}

function SlaRow({
  severity,
  rows,
  canEdit,
  saving,
  onSave,
}: {
  severity: Severity;
  rows: SlaPolicy[];
  canEdit: boolean;
  saving: boolean;
  onSave: (days: number | null) => void;
}) {
  const current = rows.find((r) => r.severity === severity)?.days ?? null;
  const [value, setValue] = useState(current === null ? "" : String(current));

  // Keep the field honest when the mutation returns the refreshed policy.
  useEffect(() => {
    setValue(current === null ? "" : String(current));
  }, [current]);

  const parsed = value.trim() === "" ? null : Number(value);
  const invalid = parsed !== null && (!Number.isFinite(parsed) || parsed < 0 || parsed > 3650);
  const dirty = parsed !== current;
  const fallback = DEFAULT_DAYS[severity];

  return (
    <li className="flex flex-wrap items-end gap-3 py-2.5">
      <div className="w-40 shrink-0">
        <TextField
          label={SEVERITY_LABEL[severity]}
          type="number"
          min={0}
          max={3650}
          value={value}
          disabled={!canEdit}
          onChange={(e) => setValue(e.target.value)}
          placeholder={fallback === null ? "No SLA" : String(fallback)}
          error={invalid ? "Use 0 to 3650 days" : undefined}
        />
      </div>
      <span className="min-w-0 flex-1 pb-2.5 text-caption text-text-subtle">
        {parsed === null
          ? fallback === null
            ? "No SLA, these never go overdue"
            : `Using the default of ${fallback} days`
          : "days to remediate"}
      </span>
      {canEdit ? (
        <Button
          size="sm"
          variant="secondary"
          className="mb-1"
          disabled={!dirty || invalid}
          loading={saving}
          onClick={() => onSave(parsed)}
        >
          Save
        </Button>
      ) : null}
    </li>
  );
}
