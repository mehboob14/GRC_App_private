import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ErrorState,
  Icon,
  Skeleton,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TextField,
  TR,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { getPolicy, updatePolicy } from "../api";
import { FINDING_SEVERITIES, type Policy, type PolicyInput } from "../types";
import { ROSTER_ROLE_META, STAGE_LABEL, TIER_META } from "../tokens";
import { AlertRulesPanel } from "./alert-rules-panel";
import { TierBadge } from "./tier-badge";

const TIERS = ["critical", "high", "medium", "low"] as const;

/** A bare number cell: the table row is the label, so a second one would repeat it. */
const NUMBER_INPUT =
  "tabular w-24 rounded-md border border-border bg-surface-primary px-2 py-1 text-right text-body-sm " +
  "text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 " +
  "focus-visible:outline-action-accent disabled:opacity-60";

/**
 * What a tier is worth in work, as a workspace setting.
 *
 * Everything here was a constant in the code until now, which meant a customer
 * whose policy says quarterly reviews of critical vendors had to be told to live
 * with ours. The gate and tiering are missing from the skip table on purpose:
 * they run for every vendor, and the server refuses to write them away.
 */
export function VendorPolicyPage() {
  const { principal } = useAuth();
  const canManage = hasPermission(principal, "vendors:manage");
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const query = useQuery({ queryKey: ["vendor-policy"], queryFn: getPolicy });
  const [draft, setDraft] = useState<PolicyInput | null>(null);

  // The form starts from what is in force, and stays put while it is edited.
  useEffect(() => {
    if (!query.data || draft !== null) return;
    const { tier_thresholds, cadence_days_by_tier, finding_sla_days_by_severity } = query.data;
    setDraft({
      tier_thresholds,
      cadence_days_by_tier,
      finding_sla_days_by_severity,
      stage_skip_matrix_by_tier: query.data.stage_skip_matrix_by_tier,
      required_reviewer_roles_by_tier: query.data.required_reviewer_roles_by_tier,
    });
  }, [query.data, draft]);

  const save = useMutation({
    mutationFn: (body: PolicyInput) => updatePolicy(body),
    onSuccess: (next) => {
      queryClient.setQueryData(["vendor-policy"], next);
      void queryClient.invalidateQueries({ queryKey: ["vendor-facets"] });
      toast({ title: "Policy saved", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "policy"), tone: "danger" }),
  });

  if (query.isError) {
    const error = describeError(query.error, "policy");
    return (
      <ErrorState
        title={error.title}
        description={error.message}
        referenceId={error.referenceId}
        onRetry={error.retryable ? () => void query.refetch() : undefined}
      />
    );
  }

  if (query.isLoading || !query.data || !draft) {
    return <Skeleton className="mt-4 h-96 w-full" />;
  }

  const policy: Policy = query.data;
  const set = (patch: Partial<PolicyInput>) => setDraft((d) => (d ? { ...d, ...patch } : d));
  const toggleSkip = (tier: string, stage: string) => {
    const current = draft.stage_skip_matrix_by_tier[tier] ?? [];
    set({
      stage_skip_matrix_by_tier: {
        ...draft.stage_skip_matrix_by_tier,
        [tier]: current.includes(stage)
          ? current.filter((s) => s !== stage)
          : [...current, stage],
      },
    });
  };
  const toggleRole = (tier: string, role: string) => {
    const current = draft.required_reviewer_roles_by_tier[tier] ?? [];
    set({
      required_reviewer_roles_by_tier: {
        ...draft.required_reviewer_roles_by_tier,
        [tier]: current.includes(role) ? current.filter((r) => r !== role) : [...current, role],
      },
    });
  };

  return (
    <div className="mt-4 max-w-4xl space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-body-md text-text-secondary">
          What each tier is worth in review work.{" "}
          {policy.is_customised ? "Tuned for this workspace." : "On the shipped defaults."}
        </p>
        {canManage ? (
          <Button loading={save.isPending} onClick={() => save.mutate(draft)}>
            Save policy
          </Button>
        ) : (
          <span className="text-body-sm text-text-subtle">
            View only. Changing it needs the Manage vendors permission.
          </span>
        )}
      </div>

      <section className="rounded-lg border border-border bg-surface-primary p-4">
        <h2 className="font-display text-title-sm text-text-primary">Bands and cadence</h2>
        <p className="mt-0.5 text-caption text-text-subtle">
          The score a tier starts at, and how often a vendor at that tier is reviewed.
        </p>
        <div className="mt-3 overflow-x-auto">
          <Table density="compact">
            <THead>
              <TR>
                <TH>Tier</TH>
                <TH numeric>Score from</TH>
                <TH numeric>Reviewed every (days)</TH>
              </TR>
            </THead>
            <TBody>
              {TIERS.map((tier) => (
                <TR key={tier}>
                  <TD>
                    <TierBadge tier={tier} label={TIER_META[tier]?.label ?? tier} />
                  </TD>
                  <TD numeric>
                    {tier === "low" ? (
                      <span className="text-body-sm text-text-subtle">Below medium</span>
                    ) : (
                      <input
                        aria-label={`${tier} band starts at`}
                        className={NUMBER_INPUT}
                        type="number"
                        min={0}
                        max={100}
                        disabled={!canManage}
                        value={String(draft.tier_thresholds[tier] ?? "")}
                        onChange={(e) =>
                          set({
                            tier_thresholds: {
                              ...draft.tier_thresholds,
                              [tier]: Number(e.target.value),
                            },
                          })
                        }
                      />
                    )}
                  </TD>
                  <TD numeric>
                    <input
                      aria-label={`${tier} tier reviewed every`}
                      className={NUMBER_INPUT}
                      type="number"
                      min={30}
                      max={1825}
                      disabled={!canManage}
                      value={String(draft.cadence_days_by_tier[tier] ?? "")}
                      onChange={(e) =>
                        set({
                          cadence_days_by_tier: {
                            ...draft.cadence_days_by_tier,
                            [tier]: Number(e.target.value),
                          },
                        })
                      }
                    />
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface-primary p-4">
        <h2 className="font-display text-title-sm text-text-primary">Remediation windows</h2>
        <p className="mt-0.5 text-caption text-text-subtle">
          How long a finding of each severity has before it is overdue.
        </p>
        <div className="mt-3 grid gap-3 sm:grid-cols-4">
          {FINDING_SEVERITIES.map((severity) => (
            <TextField
              key={severity}
              label={`${severity.charAt(0).toUpperCase() + severity.slice(1)} (days)`}
              type="number"
              min={1}
              max={365}
              disabled={!canManage}
              value={String(draft.finding_sla_days_by_severity[severity] ?? "")}
              onChange={(e) =>
                set({
                  finding_sla_days_by_severity: {
                    ...draft.finding_sla_days_by_severity,
                    [severity]: Number(e.target.value),
                  },
                })
              }
            />
          ))}
        </div>
      </section>

      <section className="rounded-lg border border-border bg-surface-primary p-4">
        <h2 className="font-display text-title-sm text-text-primary">Stages each tier skips</h2>
        <p className="mt-0.5 text-caption text-text-subtle">
          Intake, tiering and approval run for every vendor and are not listed.
        </p>
        <div className="mt-3 space-y-3">
          {TIERS.map((tier) => (
            <div key={tier} className="flex flex-wrap items-center gap-2">
              <span className="w-24 shrink-0">
                <TierBadge tier={tier} label={TIER_META[tier]?.label ?? tier} />
              </span>
              {policy.skippable_stages.map((stage) => {
                const on = (draft.stage_skip_matrix_by_tier[tier] ?? []).includes(stage);
                return (
                  <button
                    key={stage}
                    type="button"
                    disabled={!canManage}
                    onClick={() => toggleSkip(tier, stage)}
                    className={
                      on
                        ? "rounded-full border border-action-accent-border bg-action-accent-tint px-3 py-1 text-label-sm text-text-link"
                        : "rounded-full border border-border px-3 py-1 text-label-sm text-text-secondary hover:bg-surface-hover"
                    }
                  >
                    {on ? <Icon name="check" className="mr-1 inline size-3.5" /> : null}
                    {STAGE_LABEL[stage] ?? stage}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </section>

      <AlertRulesPanel canManage={canManage} />

      <section className="rounded-lg border border-border bg-surface-primary p-4">
        <h2 className="font-display text-title-sm text-text-primary">Reviewers each tier needs</h2>
        <p className="mt-0.5 text-caption text-text-subtle">
          Roles, filled from the roster. Diligence waits until they are.
        </p>
        <div className="mt-3 space-y-3">
          {TIERS.map((tier) => (
            <div key={tier} className="flex flex-wrap items-center gap-2">
              <span className="w-24 shrink-0">
                <TierBadge tier={tier} label={TIER_META[tier]?.label ?? tier} />
              </span>
              {policy.roster_roles.map((role) => {
                const on = (draft.required_reviewer_roles_by_tier[tier] ?? []).includes(role);
                return (
                  <button
                    key={role}
                    type="button"
                    disabled={!canManage}
                    onClick={() => toggleRole(tier, role)}
                    className={
                      on
                        ? "rounded-full border border-action-accent-border bg-action-accent-tint px-3 py-1 text-label-sm text-text-link"
                        : "rounded-full border border-border px-3 py-1 text-label-sm text-text-secondary hover:bg-surface-hover"
                    }
                  >
                    {on ? <Icon name="check" className="mr-1 inline size-3.5" /> : null}
                    {ROSTER_ROLE_META[role]?.label ?? role}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
        <p className="mt-3 flex items-start gap-1.5 text-caption text-text-subtle">
          <Icon name="info" className="mt-px size-3.5 shrink-0" />
          Changes apply to reviews from here on. Every tiering keeps a copy of the policy it was
          scored under, so past tiers never move.
          <Badge variant="neutral">Audited</Badge>
        </p>
      </section>
    </div>
  );
}
