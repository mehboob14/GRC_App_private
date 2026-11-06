import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ErrorState,
  RadioGroup,
  RadioGroupItem,
  Skeleton,
  TextArea,
  TextField,
  useToast,
} from "@/components/ui";
import { engagementApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { AuditType } from "@/lib/api/types";
import { getStatement, type WorkspaceFramework } from "../frameworks-api";
import { frameworkSearch } from "../use-frameworks";

const AUDITS: { value: AuditType; label: string; description: string }[] = [
  {
    value: "initial_certification",
    label: "Initial certification",
    description: "The first audit, in two stages, that leads to the certificate.",
  },
  {
    value: "surveillance",
    label: "Surveillance audit",
    description: "The yearly check between certification and recertification.",
  },
  {
    value: "recertification",
    label: "Recertification",
    description: "The full audit at the end of the three year cycle.",
  },
];

/**
 * Scope for a framework that works by applicability. The scope is a written
 * statement of what the management system covers, plus the Statement of
 * Applicability, where every requirement is in unless it is excluded with a reason.
 * Nothing here elects categories: that is how SOC 2 chooses scope, not this.
 */
export function ManagementSystemScope({ framework }: { framework: WorkspaceFramework }) {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));

  const engagementQuery = useQuery({
    queryKey: ["engagement", framework.code],
    queryFn: () => engagementApi.get(framework.code),
  });
  const statementQuery = useQuery({
    queryKey: ["statement", framework.framework_id],
    queryFn: () => getStatement(framework.framework_id),
  });

  const engagement = engagementQuery.data ?? null;
  const [name, setName] = useState("");
  const [auditType, setAuditType] = useState<AuditType>("initial_certification");
  const [auditOn, setAuditOn] = useState("");
  const [body, setBody] = useState("");
  const [scope, setScope] = useState("");

  useEffect(() => {
    if (!engagement) return;
    setName(engagement.name);
    setAuditType(engagement.audit_type);
    setAuditOn(engagement.audit_on ?? "");
    setBody(engagement.certification_body ?? "");
    setScope(engagement.scope_statement ?? "");
  }, [engagement]);

  const save = useMutation({
    mutationFn: () =>
      engagementApi.put({
        name: name.trim() || `${framework.name} certification`,
        framework_version_id: framework.version_id!,
        audit_type: auditType,
        categories_in_scope: [],
        audit_on: auditOn || null,
        certification_body: body.trim() || null,
        scope_statement: scope.trim() || null,
        status: "active",
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["engagement"] }),
        queryClient.invalidateQueries({ queryKey: ["statement"] }),
        queryClient.invalidateQueries({ queryKey: ["compliance-dashboard"] }),
      ]);
      toast({ title: "Scope saved", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "engagement"), tone: "danger" }),
  });

  if (engagementQuery.isError) {
    const failure = describeError(engagementQuery.error, "engagement");
    return (
      <ErrorState
        title={failure.title}
        description={failure.message}
        referenceId={failure.referenceId}
        onRetry={failure.retryable ? () => void engagementQuery.refetch() : undefined}
      />
    );
  }
  if (engagementQuery.isLoading) return <Skeleton className="h-64 w-full rounded-lg" />;

  const summary = statementQuery.data?.summary;

  return (
    <div className="space-y-4">
      <p className="max-w-2xl text-body-md text-text-secondary">
        Describe what {framework.name} covers: the boundary of the management system, the audit you are
        preparing for, and who runs it. Then decide, requirement by requirement, what applies.
      </p>

      <div className="rounded-lg border border-border bg-surface-primary p-5">
        <h2 className="font-display text-title-md text-text-primary">Management system scope</h2>
        <div className="mt-4 grid gap-5 lg:grid-cols-2">
          <div className="space-y-4">
            <TextArea
              label="Scope statement"
              rows={8}
              value={scope}
              onChange={(e) => setScope(e.target.value)}
              placeholder="The products and services, locations, systems, people and suppliers the management system covers, and anything left out with the reason."
              disabled={!canManage}
            />
          </div>
          <div className="space-y-4">
            <TextField
              label="Audit name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={`${framework.name} certification 2026`}
              disabled={!canManage}
            />
            <fieldset>
              <legend className="mb-1.5 font-sans text-label-sm text-text-secondary">Audit</legend>
              <RadioGroup value={auditType} onValueChange={(value) => setAuditType(value as AuditType)}>
                {AUDITS.map((audit) => (
                  <RadioGroupItem
                    key={audit.value}
                    value={audit.value}
                    label={audit.label}
                    description={audit.description}
                  />
                ))}
              </RadioGroup>
            </fieldset>
            <div className="grid grid-cols-2 gap-3">
              <TextField
                label="Audit date"
                type="date"
                value={auditOn}
                onChange={(e) => setAuditOn(e.target.value)}
                disabled={!canManage}
              />
              <TextField
                label="Certification body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                disabled={!canManage}
              />
            </div>
          </div>
        </div>
        {canManage ? (
          <div className="mt-5 flex items-center gap-3 border-t border-border pt-4">
            <Button loading={save.isPending} disabled={!framework.version_id} onClick={() => save.mutate()}>
              Save scope
            </Button>
          </div>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-border bg-surface-primary p-5">
        <div>
          <h2 className="font-display text-title-md text-text-primary">Statement of Applicability</h2>
          {summary ? (
            <p className="mt-1 text-body-sm text-text-secondary">
              <span className="tabular font-semibold text-text-primary">{summary.applicable}</span> of{" "}
              <span className="tabular font-semibold text-text-primary">{summary.total}</span> requirements
              apply, <span className="tabular">{summary.excluded}</span> excluded,{" "}
              <span className="tabular">{summary.reviewed}</span> reviewed.
            </p>
          ) : (
            <p className="mt-1 text-body-sm text-text-secondary">Every requirement applies until you decide otherwise.</p>
          )}
        </div>
        <Link
          to={`/frameworks/soa${frameworkSearch(framework.code)}`}
          className="text-body-md font-semibold text-text-link"
        >
          Open the statement
        </Link>
      </div>
    </div>
  );
}
