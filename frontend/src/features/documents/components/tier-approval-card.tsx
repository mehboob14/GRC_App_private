import { useState } from "react";
import { Button, Icon, StatusPill } from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { cn } from "@/lib/cn";
import type { ApprovalDecisionValue, ApprovalTier, Document } from "../types";
import { AssignTierDialog } from "./assign-tier-dialog";

const TIER_ROLE: Record<number, string> = { 1: "Reviewers", 2: "Approvers" };

const TIER_FAMILY: Record<ApprovalTier["status"], StatusFamily> = {
  approved: "success",
  pending: "pending",
  rejected: "danger",
  not_started: "neutral",
};
const TIER_LABEL: Record<ApprovalTier["status"], string> = {
  approved: "Approved",
  pending: "In review",
  rejected: "Rejected",
  not_started: "Not assigned",
};

const DECISION_FAMILY: Record<ApprovalDecisionValue, StatusFamily> = {
  approved: "success",
  pending: "pending",
  rejected: "danger",
};
const DECISION_LABEL: Record<ApprovalDecisionValue, string> = {
  approved: "Approved",
  pending: "Waiting",
  rejected: "Rejected",
};

const TARGET_ICON: Record<string, "users" | "shield" | "layers"> = {
  user: "users",
  role: "shield",
  group: "layers",
};

/**
 * One tier's card: who is on it, what each of them decided, and an Assign
 * button that opens the picker. This IS how a review starts — assigning tier 1
 * moves the document to needs_approval and notifies everyone on it; there is
 * no separate "send for review" step. A person's own decision happens on the
 * dedicated review page they reach from their notification, not here.
 */
export function TierApprovalCard({
  documentId,
  tier,
  canManage,
  blockedReason,
  onAssigned,
}: {
  documentId: string;
  tier: ApprovalTier;
  canManage: boolean;
  /** Why this tier cannot be assigned yet (an earlier tier has no targets). */
  blockedReason?: string;
  onAssigned: (doc: Document) => void;
}) {
  const [assigning, setAssigning] = useState(false);
  const label = `Tier ${tier.tier}: ${TIER_ROLE[tier.tier] ?? "Sign-off"}`;
  const locked = tier.status === "approved" || tier.status === "rejected";

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span
            className={cn(
              "flex size-7 shrink-0 items-center justify-center rounded-full text-caption font-bold",
              tier.status === "approved"
                ? "bg-status-success-tint text-status-success-text"
                : "bg-surface-sunken text-text-subtle",
            )}
          >
            {tier.status === "approved" ? (
              <Icon name="check" className="size-3.5" />
            ) : (
              tier.tier
            )}
          </span>
          <div>
            <p className="text-body-md font-semibold text-text-primary">{label}</p>
            <StatusPill status={TIER_FAMILY[tier.status]} label={TIER_LABEL[tier.status]} />
          </div>
        </div>
        {canManage && !locked ? (
          <Button
            variant="secondary"
            size="sm"
            disabled={Boolean(blockedReason)}
            title={blockedReason}
            onClick={() => setAssigning(true)}
          >
            {tier.targets.length ? "Reassign" : "Assign"}
          </Button>
        ) : null}
      </div>

      {tier.targets.length === 0 ? (
        <p className="mt-3 text-body-sm text-text-subtle">
          Not assigned yet. {canManage ? "Assign to start this step." : ""}
        </p>
      ) : (
        <div className="mt-3 space-y-2.5">
          <div className="flex flex-wrap gap-1.5">
            {tier.targets.map((t) => (
              <span
                key={`${t.target_type}:${t.target_id}`}
                className="inline-flex items-center gap-1 rounded-full bg-surface-hover px-2 py-0.5 text-caption text-text-secondary"
              >
                <Icon name={TARGET_ICON[t.target_type] ?? "users"} className="size-3" />
                {t.target_name}
              </span>
            ))}
          </div>
          <ul className="divide-y divide-border">
            {tier.assignees.map((a) => (
              <li key={a.membership_id} className="flex items-center justify-between gap-2 py-1.5">
                <span className="min-w-0 truncate text-body-sm text-text-primary">{a.name}</span>
                <StatusPill
                  status={DECISION_FAMILY[a.decision]}
                  label={DECISION_LABEL[a.decision]}
                />
              </li>
            ))}
          </ul>
        </div>
      )}

      {assigning ? (
        <AssignTierDialog
          documentId={documentId}
          tier={tier.tier}
          tierLabel={label}
          currentTargets={tier.targets}
          onOpenChange={setAssigning}
          onAssigned={onAssigned}
        />
      ) : null}
    </div>
  );
}
