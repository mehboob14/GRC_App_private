import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  ErrorState,
  Icon,
  RadioGroup,
  RadioGroupItem,
  Skeleton,
  TextField,
  useToast,
} from "@/components/ui";
import { complianceApi, engagementApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
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
      toast({ title: errorToast(error, "engagement"), tone: "danger" }),
  });


  const windowIncomplete =
    auditType === "type_2" && (!windowStart || !windowEnd);

  if (frameworksQuery.isError || engagementQuery.isError) {
    const failure = describeError(
      engagementQuery.error ?? frameworksQuery.error,
      "engagement",
    );
    return (
      <div>
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          onRetry={
            failure.retryable
              ? () => {
                  void frameworksQuery.refetch();
                  void engagementQuery.refetch();
                }
              : undefined
          }
        />
      </div>
    );
  }

  return (
    <div>
      {/* Instructional, not decorative: this form is filled in once and the
          election decides what the whole platform measures. */}
      <p className="mb-4 max-w-2xl text-body-md text-text-secondary">
        Choose the audit you are preparing for and which Trust Services
        Categories it covers. Only criteria in scope are measured.
      </p>

      {engagementQuery.isLoading || frameworksQuery.isLoading ? (
        <Skeleton className="h-64 w-full rounded-lg" />
      ) : (
        <div className="rounded-lg border border-border bg-surface-primary p-5">
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


      {/* Coverage moved to its own tab. Scope is a form you complete once;
          coverage is a report you return to, and pairing them meant the
          gap lists were buried under a settings form. */}
      <p className="mt-8 text-body-sm text-text-subtle">
        Gaps against this scope are listed in{" "}
        <Link className="font-semibold text-text-link" to="/frameworks/coverage">
          Coverage
        </Link>
        .
      </p>
    </div>
  );
}
