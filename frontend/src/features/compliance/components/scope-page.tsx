import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  EmptyState,
  ErrorState,
  Icon,
  RadioGroup,
  RadioGroupItem,
  Skeleton,
  StatusPill,
  Table,
  TBody,
  TD,
  TextField,
  TH,
  THead,
  TR,
  useToast,
} from "@/components/ui";
import { complianceApi, engagementApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { AuditType } from "@/lib/api/types";

/** The elective Trust Services Categories. Security is deliberately absent: it
 *  is the Common Criteria, always in scope, and cannot be elected away. */
const ELECTIVE_CATEGORIES = [
  "Availability",
  "Confidentiality",
  "Processing Integrity",
  "Privacy",
];

function Stat({
  value,
  label,
  tone = "neutral",
}: {
  value: number | string;
  label: string;
  tone?: "neutral" | "success" | "warning";
}) {
  const valueClass = {
    neutral: "text-text-primary",
    success: "text-status-success-text",
    warning: "text-status-warning-text",
  }[tone];
  return (
    <div className="rounded-lg border border-border bg-surface-primary px-4 py-3">
      <p className={`tabular font-display text-numeral-md ${valueClass}`}>{value}</p>
      <p className="mt-0.5 text-body-sm text-text-subtle">{label}</p>
    </div>
  );
}

/** Scope & coverage — elect what the audit covers, then see what is missing. */
export function ScopePage() {
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("controls:manage"));

  const frameworksQuery = useQuery({
    queryKey: ["frameworks"],
    queryFn: () => complianceApi.listFrameworks(),
  });
  const engagementQuery = useQuery({
    queryKey: ["engagement"],
    queryFn: () => engagementApi.get(),
  });
  const coverageQuery = useQuery({
    queryKey: ["coverage"],
    queryFn: () => engagementApi.coverage(),
  });

  const engagement = engagementQuery.data ?? null;
  const currentVersion = frameworksQuery.data?.[0]?.versions.find((v) => v.is_current);

  const [name, setName] = useState("");
  const [auditType, setAuditType] = useState<AuditType>("type_2");
  const [categories, setCategories] = useState<string[]>([]);
  const [windowStart, setWindowStart] = useState("");
  const [windowEnd, setWindowEnd] = useState("");

  // Seed the form from the saved engagement once it arrives.
  useEffect(() => {
    if (!engagement) return;
    setName(engagement.name);
    setAuditType(engagement.audit_type);
    setCategories(engagement.categories_in_scope);
    setWindowStart(engagement.window_start ?? "");
    setWindowEnd(engagement.window_end ?? "");
  }, [engagement]);

  const saveMutation = useMutation({
    mutationFn: () =>
      engagementApi.put({
        name: name.trim() || "SOC 2 engagement",
        framework_version_id: currentVersion!.id,
        audit_type: auditType,
        categories_in_scope: categories,
        // A Type I engagement is a point in time: the API refuses a window.
        window_start: auditType === "type_2" ? windowStart || null : null,
        window_end: auditType === "type_2" ? windowEnd || null : null,
        status: "active",
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["engagement"] }),
        queryClient.invalidateQueries({ queryKey: ["coverage"] }),
      ]);
      toast({ title: "Scope saved", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({
        title:
          error instanceof ApiError ? error.message : "Couldn't save the engagement.",
        tone: "danger",
      }),
  });

  const coverage = coverageQuery.data;
  const readiness = useMemo(() => {
    if (!coverage || coverage.criteria_total === 0) return null;
    return Math.round((coverage.criteria_covered / coverage.criteria_total) * 100);
  }, [coverage]);

  const windowIncomplete =
    auditType === "type_2" && (!windowStart || !windowEnd);

  if (frameworksQuery.isError || engagementQuery.isError) {
    return (
      <div>
        <ErrorState
          title="Couldn’t load the engagement"
          description="The request failed. Retry, or contact support if it keeps happening."
          onRetry={() => {
            void frameworksQuery.refetch();
            void engagementQuery.refetch();
          }}
        />
      </div>
    );
  }

  return (
    <div>
      <h1 className="font-display text-heading-lg text-text-primary">
        Scope &amp; coverage
      </h1>
      <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
        Choose the audit you are preparing for and which Trust Services
        Categories it covers. Only criteria in scope are measured.
      </p>

      {engagementQuery.isLoading || frameworksQuery.isLoading ? (
        <Skeleton className="mt-5 h-64 w-full rounded-lg" />
      ) : (
        <div className="mt-5 rounded-lg border border-border bg-surface-primary p-5">
          <h2 className="font-display text-title-md text-text-primary">
            Engagement setup
          </h2>

          <div className="mt-4 grid gap-5 lg:grid-cols-2">
            <div className="space-y-4">
              <TextField
                label="Engagement name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="SOC 2 Type II 2026"
                disabled={!canManage}
              />

              <fieldset>
                <legend className="mb-1.5 font-sans text-label-sm text-text-secondary">
                  Audit type
                </legend>
                <RadioGroup
                  value={auditType}
                  onValueChange={(value) => setAuditType(value as AuditType)}
                >
                  <RadioGroupItem
                    value="type_1"
                    label="Type I"
                    description="Design of controls at a single point in time."
                  />
                  <RadioGroupItem
                    value="type_2"
                    label="Type II"
                    description="Operating effectiveness across an observation window."
                  />
                </RadioGroup>
              </fieldset>

              {auditType === "type_2" ? (
                <div className="grid grid-cols-2 gap-3">
                  <TextField
                    label="Window starts"
                    type="date"
                    value={windowStart}
                    onChange={(e) => setWindowStart(e.target.value)}
                    disabled={!canManage}
                  />
                  <TextField
                    label="Window ends"
                    type="date"
                    value={windowEnd}
                    onChange={(e) => setWindowEnd(e.target.value)}
                    disabled={!canManage}
                  />
                </div>
              ) : (
                <p className="text-body-sm text-text-subtle">
                  A Type I engagement is assessed at a point in time, so it has
                  no observation window.
                </p>
              )}
            </div>

            <div>
              <p className="mb-1.5 font-sans text-label-sm text-text-secondary">
                Categories in scope
              </p>
              {/* Security is shown as fixed rather than hidden: a reader should
                  see that it applies, not wonder why it is missing. */}
              <div className="mb-2 flex items-center gap-2 rounded-md border border-border bg-surface-sunken px-3 py-2.5">
                <Icon name="shield" className="size-4 text-action-accent" />
                <span className="text-body-md font-semibold text-text-primary">
                  Security
                </span>
                <Badge variant="neutral" className="ml-auto">
                  Always in scope
                </Badge>
              </div>
              <div className="flex flex-col gap-1.5">
                {ELECTIVE_CATEGORIES.map((category) => {
                  const checked = categories.includes(category);
                  return (
                    <label
                      key={category}
                      className="flex cursor-pointer items-center gap-2.5 rounded-md border border-border px-3 py-2.5 text-body-md text-text-primary"
                    >
                      <Checkbox
                        checked={checked}
                        disabled={!canManage}
                        onCheckedChange={(value) =>
                          setCategories((prev) =>
                            value
                              ? [...prev, category]
                              : prev.filter((c) => c !== category),
                          )
                        }
                      />
                      {category}
                    </label>
                  );
                })}
              </div>
            </div>
          </div>

          {canManage ? (
            <div className="mt-5 flex items-center gap-3 border-t border-border pt-4">
              <Button
                loading={saveMutation.isPending}
                disabled={!currentVersion || windowIncomplete}
                onClick={() => saveMutation.mutate()}
              >
                Save scope
              </Button>
              {windowIncomplete ? (
                <p className="text-body-sm text-status-warning-text">
                  A Type II engagement needs both window dates.
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      )}

      <h2 className="mb-3 mt-8 font-display text-heading-sm text-text-primary">
        Coverage
      </h2>

      {coverageQuery.isLoading ? (
        <Skeleton className="h-24 w-full rounded-lg" />
      ) : !engagement ? (
        <EmptyState
          icon="shield"
          title="No scope set yet"
          description="Choose an audit type and the categories it covers, and coverage is measured against exactly those criteria."
        />
      ) : coverage ? (
        <>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Stat value={coverage.criteria_total} label="criteria in scope" />
            <Stat
              value={coverage.criteria_covered}
              label="with a control"
              tone="success"
            />
            <Stat
              value={coverage.criteria_uncovered.length}
              label="with no control"
              tone={coverage.criteria_uncovered.length ? "warning" : "neutral"}
            />
            <Stat value={readiness === null ? "—" : `${readiness}%`} label="criteria covered" />
          </div>

          {/* Honest about what is not yet measurable, rather than showing a
              zero that would read as a finding. */}
          {!coverage.evidence_tracking_available ? (
            <div className="mt-3 flex items-start gap-2.5 rounded-md border border-border bg-surface-sunken px-3.5 py-3">
              <Icon name="alert" className="mt-0.5 size-4 shrink-0 text-text-subtle" />
              <p className="text-body-sm text-text-secondary">
                Evidence tracking arrives with the evidence module. Until then
                “controls with no evidence” cannot be measured, so it is not
                shown as a result — all{" "}
                <span className="tabular">{coverage.controls_total}</span>{" "}
                controls are awaiting it.
              </p>
            </div>
          ) : null}

          <h3 className="mb-2 mt-6 font-display text-title-sm text-text-primary">
            Criteria with no control
          </h3>
          {coverage.criteria_uncovered.length === 0 ? (
            <div className="flex items-center gap-2 rounded-md border border-status-success-border bg-status-success-bg px-3.5 py-3">
              <Icon name="check" className="size-4 text-status-success-text" />
              <p className="text-body-md font-semibold text-status-success-text">
                Every criterion in scope has at least one control.
              </p>
            </div>
          ) : (
            <Table density="standard">
              <THead>
                <TR>
                  <TH>Criterion</TH>
                  <TH>Category</TH>
                  <TH>Status</TH>
                </TR>
              </THead>
              <TBody>
                {coverage.criteria_uncovered.map((gap) => (
                  <TR key={gap.requirement_id}>
                    <TD>
                      <span className="mr-2 rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link">
                        {gap.code}
                      </span>
                      <span className="text-body-md text-text-primary">
                        {gap.name}
                      </span>
                    </TD>
                    <TD>
                      <Badge variant="neutral">
                        {gap.trust_services_category}
                      </Badge>
                    </TD>
                    <TD>
                      <StatusPill kind="inline" status="warning" label="No control" />
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}

          {coverage.controls_unmapped.length > 0 ? (
            <>
              <h3 className="mb-2 mt-6 font-display text-title-sm text-text-primary">
                Controls mapped to no criterion
              </h3>
              <Table density="standard">
                <THead>
                  <TR>
                    <TH>Control</TH>
                    <TH>Issue</TH>
                  </TR>
                </THead>
                <TBody>
                  {coverage.controls_unmapped.map((gap) => (
                    <TR key={gap.control_id}>
                      <TD>
                        <span className="mr-2 rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-caption font-bold text-text-link">
                          {gap.code}
                        </span>
                        <span className="text-body-md text-text-primary">
                          {gap.name}
                        </span>
                      </TD>
                      <TD>
                        <StatusPill kind="inline" status="warning" label={gap.reason} />
                      </TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            </>
          ) : null}

          <p className="mt-5 text-body-sm text-text-subtle">
            Controls are managed in{" "}
            <Link className="font-semibold text-text-link" to="/controls">
              Controls
            </Link>
            .
          </p>
        </>
      ) : null}
    </div>
  );
}
