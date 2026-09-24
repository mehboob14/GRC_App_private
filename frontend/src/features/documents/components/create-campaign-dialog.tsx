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
  Icon,
  TextField,
  useToast,
  EMPTY_RECIPIENTS as EMPTY,
  isEmptyRecipients as isEmpty,
  RecipientPicker,
  useRecipientOptions,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { createCampaign } from "../api";
import type { Campaign, RecipientSelectionInput } from "../types";

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

  const { people, roles, groups, error: recipientsError } = useRecipientOptions();

  const reviewerCount =
    reviewers.user_ids.length + reviewers.role_ids.length + reviewers.group_ids.length;
  const approverCount =
    approvers.user_ids.length + approvers.role_ids.length + approvers.group_ids.length;

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
      toast({ title: errorToast(error, "campaign"), tone: "danger" }),
  });

  const nobody = isEmpty(reviewers) && isEmpty(approvers);

  return (
    <Dialog open onOpenChange={onOpenChange}>
      {/* Wide, and scrolling the body rather than the whole dialog: the recipient
          lists grow with the workspace, and the title and the Start button have
          to stay put while somebody scrolls through fifty names. */}
      <DialogContent size="xl" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Start an acknowledgement campaign</DialogTitle>
          <p className="text-body-md text-text-secondary">
            Ask a chosen set of people to read {documentTitle} and sign that they have.
          </p>
        </DialogHeader>
        <DialogBody className="space-y-5">
          {recipientsError ? (
            <ErrorBanner title="Recipients could not be loaded">{recipientsError}</ErrorBanner>
          ) : null}
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
          <div>
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="text-label-md font-semibold text-text-primary">Recipients</span>
              {reviewerCount + approverCount > 0 ? (
                <span className="text-caption text-text-subtle">
                  {reviewerCount} reviewer{reviewerCount === 1 ? "" : "s"} ·{" "}
                  {approverCount} approver{approverCount === 1 ? "" : "s"} selected
                </span>
              ) : null}
            </div>
            <div className="grid gap-4 md:grid-cols-2">
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
          </div>
          <div className="max-w-[220px]">
            <span className="mb-1 flex items-center gap-1.5 text-label-md font-semibold text-text-primary">
              <Icon name="clock" className="size-3.5" />
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
