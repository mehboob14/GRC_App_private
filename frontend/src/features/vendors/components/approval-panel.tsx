import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  RadioGroup,
  RadioGroupItem,
  Skeleton,
  StatusPill,
  TextArea,
  TextField,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { closeCondition, decideGate, listApprovers } from "../api";
import type { Approval, Approver, ConditionInput, VendorDetail } from "../types";
import { CONDITION_STATUS_META, DECISION_META, fmtDate } from "../tokens";
import { Panel } from "./panel";

const DECISIONS = ["approve", "approve_with_conditions", "defer", "reject"] as const;

/**
 * The approval gate: the decision, its rationale, and the conditions it carries.
 *
 * Two rules the screen has to make visible rather than merely enforce:
 *
 *  - **Segregation of duties is shown before the fact.** Whoever cannot decide
 *    this is greyed out with the reason attached, so a reviewer learns they are
 *    disqualified before they write a rationale, not after they submit one.
 *  - **A rationale is not optional.** Four decisions, all of them consequential,
 *    and the one thing an auditor will ask six months later is why.
 */
export function ApprovalPanel({
  vendor,
  engagementId,
  canApprove,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  engagementId: string | null;
  canApprove: boolean;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deciding, setDeciding] = useState(false);

  const approvals = vendor.approvals.filter(
    (a) => engagementId === null || a.engagement_id === engagementId,
  );
  const latest = approvals.length > 0 ? approvals.reduce((a, b) => (b.cycle >= a.cycle ? b : a)) : null;

  const gate = vendor.stages.find(
    (s) => s.is_gate && (engagementId === null || s.engagement_id === engagementId),
  );
  const gateReached = gate?.status === "in_progress" || gate?.status === "complete";
  // `approval.decided` is the blocker this very button clears, so it must not
  // disable it — that would be a gate nobody could ever pass. Everything else
  // genuinely has to be settled before a decision means anything.
  const blockers = (gate?.blockers ?? []).filter((b) => b.code !== "approval.decided");

  if (!gate) {
    return (
      <Panel title="Approval">
        <p className="text-body-md text-text-secondary">
          The gate appears once the engagement is tiered.
        </p>
      </Panel>
    );
  }

  return (
    <>
      <Panel
        title="Approval"
        description="A gate is never skipped, whatever the tier."
        action={
          canApprove && gateReached && latest === null ? (
            <Button size="sm" onClick={() => setDeciding(true)} disabled={blockers.length > 0}>
              Record the decision
            </Button>
          ) : null
        }
      >
        {latest ? (
          <DecisionRecord
            approval={latest}
            vendorId={vendor.id}
            canManage={canManage}
            onSettled={() => {
              void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
            }}
          />
        ) : !gateReached ? (
          <p className="text-body-md text-text-secondary">
            The review has not reached the gate yet. A decision recorded early is a decision made
            without the evidence, so it is not offered until the earlier stages are done.
          </p>
        ) : blockers.length > 0 ? (
          <div className="rounded-md border border-status-warning-border bg-status-warning-bg p-3.5">
            <p className="flex items-center gap-1.5 text-label-sm text-status-warning-text">
              <Icon name="alert" className="size-4 shrink-0" />
              {blockers.length} {blockers.length === 1 ? "thing has" : "things have"} to be
              settled first
            </p>
            <ul className="mt-2 space-y-1">
              {blockers.map((b) => (
                <li key={b.code} className="text-body-sm text-text-secondary">
                  {b.label}
                  {b.detail ? <span className="text-text-subtle"> — {b.detail}</span> : null}
                </li>
              ))}
            </ul>
          </div>
        ) : !canApprove ? (
          <p className="text-body-md text-text-secondary">
            Nothing is blocking the gate. Deciding it needs the Approve vendors permission — whoever
            ran the assessment is deliberately not the person who signs it off.
          </p>
        ) : (
          <p className="text-body-md text-text-secondary">
            Nothing is blocking the gate. Record the decision when you are ready.
          </p>
        )}
      </Panel>

      {deciding && engagementId ? (
        <DecisionDialog
          vendorId={vendor.id}
          engagementId={engagementId}
          onClose={() => setDeciding(false)}
          onDecided={(next) => {
            onApply(next);
            void queryClient.invalidateQueries({ queryKey: ["vendors"] });
            setDeciding(false);
            toast({ title: "Decision recorded", tone: "success" });
          }}
        />
      ) : null}
    </>
  );
}

function DecisionRecord({
  approval,
  vendorId,
  canManage,
  onSettled,
}: {
  approval: Approval;
  vendorId: string;
  canManage: boolean;
  onSettled: () => void;
}) {
  const { toast } = useToast();
  const meta = DECISION_META[approval.decision] ?? {
    label: approval.decision,
    family: "neutral" as const,
    blurb: "",
  };

  const settle = useMutation({
    mutationFn: (input: { conditionId: string; status: string; reason?: string }) =>
      closeCondition(vendorId, input.conditionId, input.status, input.reason ?? null),
    onSuccess: () => {
      onSettled();
      toast({ title: "Condition updated", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "condition"), tone: "danger" }),
  });

  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={meta.family} label={meta.label} />
        <span className="text-caption text-text-subtle">
          {approval.decided_by_name ?? "Unattributed"} · {fmtDate(approval.decided_at)} · cycle{" "}
          {approval.cycle}
        </span>
      </div>
      <p className="mt-1 text-body-sm text-text-subtle">{meta.blurb}</p>
      <p className="mt-3 whitespace-pre-line text-body-md text-text-secondary">
        {approval.rationale}
      </p>

      {approval.excluded_membership_ids.length > 0 ? (
        <p className="mt-2 text-caption text-text-subtle">
          {approval.excluded_membership_ids.length}{" "}
          {approval.excluded_membership_ids.length === 1 ? "person was" : "people were"} excluded
          from deciding this, recorded at the time.
        </p>
      ) : null}

      {approval.conditions.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          <p className="type-overline">Conditions</p>
          <ul className="mt-2 divide-y divide-border">
            {approval.conditions.map((c) => {
              const status = CONDITION_STATUS_META[c.status] ?? {
                label: c.status,
                family: "neutral" as const,
              };
              const settled = c.status === "met" || c.status === "waived";
              return (
                <li key={c.id} className="flex flex-wrap items-start justify-between gap-3 py-2.5">
                  <div className="min-w-0 flex-1">
                    <p className={cn("text-body-md", settled ? "text-text-subtle" : "text-text-primary")}>
                      {c.description}
                    </p>
                    <p className="mt-0.5 text-caption text-text-subtle">
                      {c.owner_name ?? "Unassigned"}
                      {c.due_date ? ` · due ${fmtDate(c.due_date)}` : ""}
                      {c.waived_reason ? ` · waived: ${c.waived_reason}` : ""}
                    </p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    <StatusPill status={status.family} label={status.label} kind="inline" />
                    {!settled && canManage ? (
                      <Button
                        variant="secondary"
                        size="sm"
                        loading={settle.isPending}
                        onClick={() => settle.mutate({ conditionId: c.id, status: "met" })}
                      >
                        Mark met
                      </Button>
                    ) : null}
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

function DecisionDialog({
  vendorId,
  engagementId,
  onClose,
  onDecided,
}: {
  vendorId: string;
  engagementId: string;
  onClose: () => void;
  onDecided: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const [decision, setDecision] = useState<string>("approve");
  const [rationale, setRationale] = useState("");
  const [conditions, setConditions] = useState<ConditionInput[]>([]);

  const approversQuery = useQuery({
    queryKey: ["vendor-approvers", vendorId, engagementId],
    queryFn: () => listApprovers(vendorId, engagementId),
  });

  const decide = useMutation({
    mutationFn: () =>
      decideGate(vendorId, engagementId, {
        decision,
        rationale: rationale.trim(),
        conditions: conditions.filter((c) => c.description.trim()),
      }),
    onSuccess: onDecided,
    onError: (e: unknown) => toast({ title: errorToast(e, "decision"), tone: "danger" }),
  });

  const withConditions = decision === "approve_with_conditions";
  const usable = rationale.trim() && (!withConditions || conditions.some((c) => c.description.trim()));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="lg" scrollBody>
        <DialogHeader>
          <DialogTitle>Record the approval decision</DialogTitle>
          <DialogDescription>
            This is the gate. Whatever you choose, the rationale is what an auditor reads back to
            you later.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (usable) decide.mutate();
          }}
        >
          <DialogBody className="space-y-4">
            <ApproverList
              approvers={approversQuery.data ?? []}
              loading={approversQuery.isLoading}
              error={
                approversQuery.isError
                  ? describeError(approversQuery.error, "approvers").message
                  : null
              }
            />

            <div>
              <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Decision</p>
              <RadioGroup value={decision} onValueChange={setDecision} className="space-y-2">
                {DECISIONS.map((d) => (
                  <RadioGroupItem
                    key={d}
                    value={d}
                    label={DECISION_META[d].label}
                    description={DECISION_META[d].blurb}
                  />
                ))}
              </RadioGroup>
            </div>

            <TextArea
              label="Rationale"
              hint="What you relied on, and what you decided to live with."
              value={rationale}
              onChange={(e) => setRationale(e.target.value)}
              rows={4}
              maxLength={8000}
              showCount
            />

            {withConditions ? (
              <div className="rounded-md border border-border bg-surface-sunken p-3.5">
                <div className="flex items-center justify-between gap-3">
                  <p className="type-overline">Conditions</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() =>
                      setConditions((c) => [...c, { description: "", due_date: null }])
                    }
                  >
                    <Icon name="plus" className="size-4" />
                    Add a condition
                  </Button>
                </div>
                <p className="mt-1 text-body-sm text-text-subtle">
                  Each one becomes a tracked item. An approval with conditions nobody wrote down is
                  an unconditional approval.
                </p>
                <div className="mt-3 space-y-3">
                  {conditions.map((c, index) => (
                    <div key={index} className="grid gap-2 sm:grid-cols-[1fr_10rem_auto]">
                      <TextField
                        label={`Condition ${index + 1}`}
                        value={c.description}
                        onChange={(e) =>
                          setConditions((all) =>
                            all.map((x, i) =>
                              i === index ? { ...x, description: e.target.value } : x,
                            ),
                          )
                        }
                        placeholder="Ship MFA on the admin console"
                      />
                      <TextField
                        label="Due"
                        optional
                        type="date"
                        value={c.due_date ?? ""}
                        onChange={(e) =>
                          setConditions((all) =>
                            all.map((x, i) =>
                              i === index ? { ...x, due_date: e.target.value || null } : x,
                            ),
                          )
                        }
                      />
                      <Button
                        variant="ghost"
                        size="icon"
                        className="self-end"
                        aria-label={`Remove condition ${index + 1}`}
                        onClick={() => setConditions((all) => all.filter((_, i) => i !== index))}
                      >
                        <Icon name="trash" className="size-4" />
                      </Button>
                    </div>
                  ))}
                  {conditions.length === 0 ? (
                    <p className="text-body-sm text-text-subtle">
                      Add at least one, or choose a plain approval instead.
                    </p>
                  ) : null}
                </div>
              </div>
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant={decision === "reject" ? "destructive" : "primary"}
              loading={decide.isPending}
              disabled={!usable}
            >
              {DECISION_META[decision]?.label ?? "Record"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Who may decide, and who may not.
 *
 * The disqualified are shown, greyed, with the reason — not hidden. Hiding them
 * turns a rule into a mystery: the assessor who ran the questionnaire needs to
 * see that they are excluded and why, or they will assume the list is broken.
 */
function ApproverList({
  approvers,
  loading,
  error,
}: {
  approvers: Approver[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <Skeleton className="h-20 w-full" />;
  if (error) return <p className="text-body-sm text-status-danger-text">{error}</p>;

  const eligible = approvers.filter((a) => a.disqualified_reason === null);
  const excluded = approvers.filter((a) => a.disqualified_reason !== null);

  return (
    <div className="rounded-md border border-border bg-surface-sunken p-3.5">
      <p className="type-overline">Who can decide this</p>
      {eligible.length === 0 ? (
        <p className="mt-2 text-body-sm text-status-warning-text">
          Nobody on the roster is eligible. Assign an approver who was not involved in the
          assessment, or this gate cannot be decided.
        </p>
      ) : (
        <ul className="mt-2 space-y-1.5">
          {eligible.map((a) => (
            <li key={a.membership_id} className="flex items-center gap-2 text-body-sm">
              <Icon name="check" className="size-4 shrink-0 text-status-success-base" />
              <span className="text-text-primary">{a.name}</span>
              {a.is_designated_approver ? <Badge variant="role">Designated</Badge> : null}
            </li>
          ))}
        </ul>
      )}

      {excluded.length > 0 ? (
        <ul className="mt-2.5 space-y-1.5 border-t border-border pt-2.5">
          {excluded.map((a) => (
            <li key={a.membership_id} className="flex items-start gap-2 text-body-sm">
              <Icon name="x" className="mt-0.5 size-4 shrink-0 text-text-faint" />
              <span className="min-w-0">
                <Tooltip content={a.disqualified_reason ?? ""}>
                  <span className="text-text-faint line-through">{a.name}</span>
                </Tooltip>
                <span className="ml-1.5 text-caption text-text-subtle">
                  {a.disqualified_reason}
                </span>
              </span>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
