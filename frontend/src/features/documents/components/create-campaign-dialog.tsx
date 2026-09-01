import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  PeopleSelect,
  type Person,
  TextField,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import { iamApi } from "@/lib/api/endpoints";
import { createCampaign } from "../api";
import type { Campaign, RecipientSelectionInput } from "../types";

const EMPTY: RecipientSelectionInput = { user_ids: [], role_ids: [], group_ids: [] };

/** People, roles and groups pickers for one recipient kind (reviewers/approvers). */
function RecipientPicker({
  label,
  people,
  roles,
  groups,
  value,
  onChange,
}: {
  label: string;
  people: Person[];
  roles: Person[];
  groups: Person[];
  value: RecipientSelectionInput;
  onChange: (next: RecipientSelectionInput) => void;
}) {
  return (
    <fieldset className="rounded-md border border-border p-3">
      <legend className="px-1 text-label-md font-bold text-text-primary">{label}</legend>
      <div className="space-y-3">
        <div>
          <span className="mb-1 block text-caption text-text-subtle">People</span>
          <PeopleSelect
            people={people}
            values={value.user_ids}
            onChange={(user_ids) => onChange({ ...value, user_ids })}
            placeholder="Add people…"
          />
        </div>
        <div>
          <span className="mb-1 block text-caption text-text-subtle">Roles</span>
          <PeopleSelect
            people={roles}
            values={value.role_ids}
            onChange={(role_ids) => onChange({ ...value, role_ids })}
            placeholder="Add roles…"
          />
        </div>
        <div>
          <span className="mb-1 block text-caption text-text-subtle">Groups</span>
          <PeopleSelect
            people={groups}
            values={value.group_ids}
            onChange={(group_ids) => onChange({ ...value, group_ids })}
            placeholder="Add groups…"
          />
        </div>
      </div>
    </fieldset>
  );
}

const isEmpty = (s: RecipientSelectionInput) =>
  s.user_ids.length === 0 && s.role_ids.length === 0 && s.group_ids.length === 0;

/**
 * Start an acknowledgement campaign against a document. The owner names the
 * reviewers and approvers by any mix of individuals, roles and groups; the
 * backend expands roles/groups to their current members and fans out a
 * "please acknowledge" notice to each.
 */
export function CreateCampaignDialog({
  documentId,
  documentTitle,
  onOpenChange,
  onCreated,
}: {
  documentId: string;
  documentTitle: string;
  onOpenChange: (open: boolean) => void;
  onCreated: (campaign: Campaign) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(`Acknowledge: ${documentTitle}`);
  const [message, setMessage] = useState("");
  const [dueAt, setDueAt] = useState("");
  const [reviewers, setReviewers] = useState<RecipientSelectionInput>(EMPTY);
  const [approvers, setApprovers] = useState<RecipientSelectionInput>(EMPTY);

  const membersQuery = useQuery({ queryKey: ["members"], queryFn: () => iamApi.listMembers() });
  const rolesQuery = useQuery({ queryKey: ["roles"], queryFn: () => iamApi.listRoles() });
  const groupsQuery = useQuery({ queryKey: ["groups"], queryFn: () => iamApi.listGroups() });

  const people: Person[] = (membersQuery.data ?? []).map((m) => ({
    id: m.membership_id,
    name: m.full_name,
    email: m.email,
  }));
  const roles: Person[] = (rolesQuery.data ?? []).map((r) => ({
    id: r.id,
    name: r.name,
    email: `${r.assignment_count} assigned`,
  }));
  const groups: Person[] = (groupsQuery.data ?? []).map((g) => ({
    id: g.id,
    name: g.name,
    email: `${g.member_count} members`,
  }));

  const create = useMutation({
    mutationFn: () =>
      createCampaign(documentId, {
        title: title.trim(),
        message: message.trim() || null,
        reviewers,
        approvers,
        due_at: dueAt ? new Date(dueAt).toISOString() : null,
      }),
    onSuccess: (campaign) => {
      toast({ title: "Campaign started", tone: "success" });
      queryClient.invalidateQueries({ queryKey: ["document-campaigns", documentId] });
      onCreated(campaign);
      onOpenChange(false);
    },
    onError: (error: unknown) =>
      toast({
        title: error instanceof ApiError ? error.message : "Couldn't start the campaign.",
        tone: "danger",
      }),
  });

  const nobody = isEmpty(reviewers) && isEmpty(approvers);

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[92vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Start an acknowledgement campaign</DialogTitle>
        </DialogHeader>
        <DialogBody className="space-y-4">
          <TextField
            label="Campaign title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="What are people acknowledging?"
          />
          <div>
            <span className="mb-1 block text-label-md font-semibold text-text-primary">
              Message <span className="font-normal text-text-subtle">(optional)</span>
            </span>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="A note shown to recipients…"
              rows={2}
              className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <RecipientPicker
              label="Reviewers"
              people={people}
              roles={roles}
              groups={groups}
              value={reviewers}
              onChange={setReviewers}
            />
            <RecipientPicker
              label="Approvers"
              people={people}
              roles={roles}
              groups={groups}
              value={approvers}
              onChange={setApprovers}
            />
          </div>
          <div className="max-w-[220px]">
            <span className="mb-1 block text-label-md font-semibold text-text-primary">
              Due date <span className="font-normal text-text-subtle">(optional)</span>
            </span>
            <input
              type="date"
              value={dueAt}
              onChange={(e) => setDueAt(e.target.value)}
              className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            loading={create.isPending}
            disabled={nobody || title.trim() === ""}
            onClick={() => create.mutate()}
          >
            Start campaign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
