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
  EMPTY_RECIPIENTS,
  ErrorBanner,
  PersonSelect,
  RecipientPicker,
  useRecipientOptions,
  useToast,
  type RecipientSelection,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { assignVulnerability } from "../api";
import type { AssignmentTarget, VulnInstanceDetail } from "../types";

/** Rebuild the picker's shape from what the finding already carries. */
function seed(targets: AssignmentTarget[]): RecipientSelection {
  return {
    user_ids: targets.filter((t) => t.target_type === "user").map((t) => t.target_id),
    role_ids: targets.filter((t) => t.target_type === "role").map((t) => t.target_id),
    group_ids: targets.filter((t) => t.target_type === "group").map((t) => t.target_id),
  };
}

/**
 * Assign a finding. The owner is one accountable person — SLA escalation and
 * remediation approval both key off them — and the pickers below add anyone
 * else who should be on it, by person, role or group.
 */
export function AssignDialog({
  vuln,
  open,
  onOpenChange,
}: {
  vuln: VulnInstanceDetail;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const { people, roles, groups, error } = useRecipientOptions();

  const [owner, setOwner] = useState<string | null>(vuln.owner_membership_id);
  const [selection, setSelection] = useState<RecipientSelection>(
    vuln.assignment_targets.length ? seed(vuln.assignment_targets) : EMPTY_RECIPIENTS,
  );

  const save = useMutation({
    mutationFn: () =>
      assignVulnerability(vuln.id, owner, [
        ...selection.user_ids.map((id) => ({ target_type: "user" as const, target_id: id })),
        ...selection.role_ids.map((id) => ({ target_type: "role" as const, target_id: id })),
        ...selection.group_ids.map((id) => ({ target_type: "group" as const, target_id: id })),
      ]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["vulnerability", vuln.id] });
      queryClient.invalidateQueries({ queryKey: ["vulnerabilities"] });
      toast({ title: "Assignment saved", tone: "success" });
      onOpenChange(false);
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "assignment"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Assign finding</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          {error ? <ErrorBanner title="Couldn't load the people list">{error}</ErrorBanner> : null}

          <div>
            <span className="mb-1 block text-label-md font-semibold text-text-primary">Owner</span>
            <PersonSelect
              people={people}
              value={owner}
              onChange={setOwner}
              placeholder="Unassigned"
              aria-label="Owner"
            />
            <p className="mt-1 text-caption text-text-subtle">
              The one person accountable. SLA escalation and remediation approval need an owner.
            </p>
          </div>

          <RecipientPicker
            label="Also assigned to"
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
          <Button loading={save.isPending} onClick={() => save.mutate()}>
            Save assignment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
