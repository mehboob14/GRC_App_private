import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorBanner,
  useToast,
  EMPTY_RECIPIENTS,
  isEmptyRecipients,
  RecipientPicker,
  useRecipientOptions,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { assignApprovalTier } from "../api";
import type { ApprovalTarget, Document, RecipientSelectionInput } from "../types";

function seed(targets: ApprovalTarget[]): RecipientSelectionInput {
  return {
    user_ids: targets.filter((t) => t.target_type === "user").map((t) => t.target_id),
    role_ids: targets.filter((t) => t.target_type === "role").map((t) => t.target_id),
    group_ids: targets.filter((t) => t.target_type === "group").map((t) => t.target_id),
  };
}

/**
 * Who reviews or approves one tier: any mix of named people, roles and
 * groups. Assigning tier 1 on a draft document starts the review and notifies
 * everyone on it immediately — there is no separate "send for review" step.
 */
export function AssignTierDialog({
  documentId,
  tier,
  tierLabel,
  currentTargets,
  onOpenChange,
  onAssigned,
}: {
  documentId: string;
  tier: number;
  tierLabel: string;
  currentTargets: ApprovalTarget[];
  onOpenChange: (open: boolean) => void;
  onAssigned: (doc: Document) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selection, setSelection] = useState<RecipientSelectionInput>(
    currentTargets.length ? seed(currentTargets) : EMPTY_RECIPIENTS,
  );
  const { people, roles, groups, error: recipientsError } = useRecipientOptions();

  const assign = useMutation({
    mutationFn: () => assignApprovalTier(documentId, tier, selection),
    onSuccess: (doc) => {
      toast({ title: `${tierLabel} assigned`, tone: "success" });
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      onAssigned(doc);
      onOpenChange(false);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "tier"), tone: "danger" }),
  });

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Assign {tierLabel.toLowerCase()}</DialogTitle>
          <p className="text-body-md text-text-secondary">
            Choose who signs off on this step. A named person must sign off themselves; a role or
            group is satisfied by any one member.
          </p>
        </DialogHeader>
        <DialogBody className="space-y-4">
          {recipientsError ? (
            <ErrorBanner title="Recipients could not be loaded">{recipientsError}</ErrorBanner>
          ) : null}
          <RecipientPicker
            label={tierLabel}
            people={people}
            roles={roles}
            groups={groups}
            value={selection}
            onChange={setSelection}
          />
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={assign.isPending}
            disabled={isEmptyRecipients(selection)}
            onClick={() => assign.mutate()}
          >
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
