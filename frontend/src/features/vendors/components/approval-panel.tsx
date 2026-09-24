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
import { useAuth } from "@/lib/auth/auth-context";
import { closeCondition, decideGate, listApprovers } from "../api";
import type { Approval, Approver, ConditionInput, VendorDetail } from "../types";
import { CONDITION_STATUS_META, DECISION_META, fmtDate } from "../tokens";

const DECISIONS = ["approve", "approve_with_conditions", "defer", "reject"] as const;

/**
 * The approval decision, shown inside the Approval stage of the lifecycle.
 *
 * Two rules the screen has to make visible rather than merely enforce:
 *
 *  - **Segregation of duties is shown before the fact.** Whoever cannot decide
 *    this is greyed out with the reason attached, so a reviewer learns they are
 *    disqualified before they write a rationale, not after they submit one.
 *  - **A rationale is not optional.** Four decisions, all of them consequential,
 *    and the one thing an auditor will ask six months later is why.
 */
export function ApprovalSection({
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
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [deciding, setDeciding] = useState(false);

  const gate = vendor.stages.find(
    (s) => s.is_gate && (engagementId === null || s.engagement_id === engagementId),
  );
  // Newest first from the server, and only this cycle's decisions bear on this
  // gate. The latest one is what counts: a later defer or reject withdraws an
  // earlier approval.
  const decisions = vendor.approvals.filter(
    (a) =>
      (engagementId === null || a.engagement_id === engagementId) &&
      (gate === undefined || a.cycle === gate.cycle),
  );
  const latest = decisions[0] ?? null;
  const earlier = decisions.slice(1);
  const gateOpen = gate?.status === "in_progress";
  // `approval.decided` is the blocker a decision clears. Any other blocker holds
  // back an approval only: deferring or rejecting is always allowed.
  const approveBlocked = (gate?.blockers ?? []).some((b) => b.code !== "approval.decided");

  return (
    <section>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h4 className="font-sans text-label-md text-text-primary">Decision</h4>
        {canApprove && gateOpen ? (
          <Button
            size="sm"
            variant={latest ? "secondary" : "primary"}
            onClick={() => setDeciding(true)}
          >
            {latest ? "Record a new decision" : "Record decision"}
          </Button>
        ) : null}
      </div>

      {latest ? (
        <DecisionRecord
          approval={latest}
          vendorId={vendor.id}
          canManage={canManage}
          onSettled={() => {
            void queryClient.invalidateQueries({ queryKey: ["vendor", vendor.id] });
          }}
        />
      ) : (
        <p className="text-body-sm text-text-subtle">
          {gate?.status === "complete"
            ? "Passed."
            : !gateOpen
              ? "Opens when the earlier stages are done."
              : approveBlocked
                ? "Approving waits on the checks above. Deferring or rejecting does not."
                : canApprove
                  ? "Ready for a decision."
                  : "Needs the Approve vendors permission."}
        </p>
      )}

      {earlier.length > 0 ? (
        <div className="mt-4 border-t border-border pt-3">
          <p className="type-overline">Earlier in this review</p>
          <ul className="mt-2 space-y-1.5">
            {earlier.map((a) => {
              const meta = DECISION_META[a.decision] ?? {
                label: a.decision,
                family: "neutral" as const,
              };
              return (
                <li
                  key={a.id}
                  className="flex flex-wrap items-center gap-2 text-caption text-text-subtle"
                >
                  <StatusPill status={meta.family} label={meta.label} kind="inline" />
                  {a.decided_by_name ?? "Unattributed"} · {fmtDate(a.decided_at)}
                </li>
              );
            })}
          </ul>
        </div>
      ) : null}

      {deciding && engagementId ? (
        <DecisionDialog
          vendorId={vendor.id}
          engagementId={engagementId}
          approveBlocked={approveBlocked}
          onClose={() => setDeciding(false)}
          onDecided={(next) => {
            onApply(next);
            void queryClient.invalidateQueries({ queryKey: ["vendors"] });
            setDeciding(false);
            toast({ title: "Decision recorded", tone: "success" });
          }}
        />
      ) : null}
    </section>
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
      <p className="mt-3 whitespace-pre-line text-body-md text-text-secondary">
        {approval.rationale}
      </p>

      {approval.excluded_membership_ids.length > 0 ? (
        <p className="mt-2 text-caption text-text-subtle">
          {approval.excluded_membership_ids.length}{" "}
          {approval.excluded_membership_ids.length === 1 ? "person" : "people"} excluded from
          deciding
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
  approveBlocked,
  onClose,
  onDecided,
}: {
  vendorId: string;
  engagementId: string;
  approveBlocked: boolean;
  onClose: () => void;
  onDecided: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const { principal } = useAuth();
  const [decision, setDecision] = useState<string>(approveBlocked ? "defer" : "approve");
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
  // Segregation of duties, shown before the rationale is written.
  const me = (approversQuery.data ?? []).find((a) => a.membership_id === principal?.membership_id);
  const barred = me?.disqualified_reason ?? null;
  const usable =
    !barred &&
    rationale.trim() &&
    (!withConditions || conditions.some((c) => c.description.trim()));

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent size="lg" scrollBody>
        <DialogHeader>
          <DialogTitle>Record decision</DialogTitle>
          <DialogDescription>The rationale is what an auditor reads later.</DialogDescription>
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

            {barred ? (
              <p className="rounded-md border border-status-warning-border bg-status-warning-bg px-3 py-2 text-body-sm text-status-warning-text">
                You cannot decide this one ({barred}). Ask one of the people listed above.
              </p>
            ) : null}

            <div>
              <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Decision</p>
              <RadioGroup value={decision} onValueChange={setDecision} className="space-y-2">
                {DECISIONS.map((d) => {
                  const held =
                    approveBlocked && (d === "approve" || d === "approve_with_conditions");
                  return (
                    <RadioGroupItem
                      key={d}
                      value={d}
                      disabled={held}
                      label={DECISION_META[d].label}
                      description={
                        held ? "Unavailable until the stage checks clear." : DECISION_META[d].blurb
                      }
                    />
                  );
                })}
              </RadioGroup>
            </div>

            <TextArea
              label="Rationale"
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
                    Add condition
                  </Button>
                </div>
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
                      Add at least one condition.
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
      <p className="type-overline">Who can decide</p>
      {eligible.length === 0 ? (
        <p className="mt-2 text-body-sm text-status-warning-text">
          Nobody eligible. Assign an approver who did not run the assessment.
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
                  <span className="text-text-faint">{a.name}</span>
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
