import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  Icon,
  PersonSelect,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  StatusPill,
  TextArea,
  useToast,
} from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import { addComment, assignReviewer, setReviewStatus } from "../api";
import { RISK_DOMAINS, type Assessment, type Comment, type Reviewer } from "../types";
import { fmtDate } from "../tokens";

const STATUS_META: Record<string, { label: string; family: "warning" | "progress" | "success" }> = {
  assigned: { label: "Waiting", family: "warning" },
  in_review: { label: "Reading", family: "progress" },
  done: { label: "Done", family: "success" },
};

/**
 * Who is reading which part of a review, and the conversation about it.
 *
 * Two people reviewing the same questionnaire is the normal case: security reads
 * the access-control answers while legal reads the contract ones, and each says
 * so when they are done. Without this the review has one state for ten domains,
 * and the second reviewer finds out they were needed by being asked.
 */
export function ReviewCollaboration({
  vendorId,
  assessment,
  people,
  canAssess,
  onApply,
}: {
  vendorId: string;
  assessment: Assessment;
  people: { id: string; name: string }[];
  canAssess: boolean;
  onApply: (next: Assessment) => void;
}) {
  const { toast } = useToast();
  const [domain, setDomain] = useState<string>("__all__");
  const [reviewers, setReviewers] = useState<Reviewer[]>(assessment.reviewers);
  const [comments, setComments] = useState<Comment[]>(assessment.comments);
  const [draft, setDraft] = useState("");
  const [shareWithVendor, setShareWithVendor] = useState(false);

  const assign = useMutation({
    mutationFn: (membershipId: string) =>
      assignReviewer(vendorId, assessment.id, {
        membership_id: membershipId,
        domain: domain === "__all__" ? null : domain,
      }),
    onSuccess: (items) => {
      setReviewers(items);
      onApply({ ...assessment, reviewers: items });
      toast({ title: "Reviewer assigned and notified", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "reviewer"), tone: "danger" }),
  });

  const move = useMutation({
    mutationFn: (input: { id: string; status: string }) =>
      setReviewStatus(vendorId, assessment.id, input.id, input.status),
    onSuccess: (items) => {
      setReviewers(items);
      onApply({ ...assessment, reviewers: items });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "reviewer"), tone: "danger" }),
  });

  const say = useMutation({
    mutationFn: () =>
      addComment(vendorId, assessment.id, {
        body: draft.trim(),
        visibility: shareWithVendor ? "vendor_shared" : "internal_only",
      }),
    onSuccess: (items) => {
      setComments(items);
      onApply({ ...assessment, comments: items });
      setDraft("");
      toast({
        title: shareWithVendor ? "Sent to the vendor" : "Comment added",
        tone: "success",
      });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "comment"), tone: "danger" }),
  });

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <section>
        <p className="type-overline">Who is reading what</p>
        {reviewers.length === 0 ? (
          <p className="mt-2 text-body-sm text-text-subtle">
            Nobody assigned. One person reads the lot unless you split it.
          </p>
        ) : (
          <ul className="mt-2 divide-y divide-border">
            {reviewers.map((r) => {
              const status = STATUS_META[r.status] ?? {
                label: r.status,
                family: "warning" as const,
              };
              return (
                <li key={r.id} className="flex flex-wrap items-center gap-2 py-2">
                  <Avatar name={r.reviewer_name ?? "Unnamed"} seed={r.reviewer_membership_id} size="sm" />
                  <span className="min-w-0 flex-1">
                    <span className="block text-body-sm text-text-primary">
                      {r.reviewer_name ?? "Unnamed member"}
                    </span>
                    <span className="block text-caption text-text-subtle">
                      {r.domain_label}
                      {r.decided_at ? ` · ${fmtDate(r.decided_at)}` : ""}
                      {r.note ? ` · ${r.note}` : ""}
                    </span>
                  </span>
                  <StatusPill status={status.family} label={status.label} kind="inline" />
                  {canAssess && r.status !== "done" ? (
                    <Button
                      variant="secondary"
                      size="sm"
                      loading={move.isPending && move.variables?.id === r.id}
                      onClick={() => move.mutate({ id: r.id, status: "done" })}
                    >
                      Mark done
                    </Button>
                  ) : null}
                  {canAssess ? (
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Unassign ${r.reviewer_name ?? "reviewer"}`}
                      onClick={() => move.mutate({ id: r.id, status: "removed" })}
                    >
                      <Icon name="x" className="size-4" />
                    </Button>
                  ) : null}
                </li>
              );
            })}
          </ul>
        )}

        {canAssess ? (
          <div className="mt-3 flex flex-wrap items-end gap-2">
            <div className="w-56">
              <p className="mb-1.5 font-sans text-label-sm text-text-secondary">Part of the review</p>
              <Select value={domain} onValueChange={setDomain}>
                <SelectTrigger aria-label="Domain" />
                <SelectContent>
                  <SelectItem value="__all__">The whole review</SelectItem>
                  {RISK_DOMAINS.map((d) => (
                    <SelectItem key={d.key} value={d.key}>
                      {d.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="w-56">
              <PersonSelect
                people={people}
                value={null}
                onChange={(id) => {
                  if (id) assign.mutate(id);
                }}
                placeholder="Assign to…"
                aria-label="Assign a reviewer"
                disabled={assign.isPending}
              />
            </div>
          </div>
        ) : null}
      </section>

      <section>
        <p className="type-overline">Conversation</p>
        {comments.length === 0 ? (
          <p className="mt-2 text-body-sm text-text-subtle">
            Nothing said yet. Notes stay internal unless you share them.
          </p>
        ) : (
          <ul className="mt-2 space-y-2.5">
            {comments.map((c) => (
              <li
                key={c.id}
                className="rounded-md border border-border bg-surface-sunken px-3 py-2.5"
              >
                <p className="flex flex-wrap items-center gap-2 text-caption text-text-subtle">
                  <span className="font-semibold text-text-primary">{c.author_name}</span>
                  {c.visibility === "vendor_shared" ? (
                    <StatusPill status="progress" label="Shared with the vendor" kind="inline" />
                  ) : (
                    <StatusPill status="neutral" label="Internal" kind="inline" />
                  )}
                  {fmtDate(c.created_at)}
                </p>
                <p className="mt-1 whitespace-pre-line text-body-sm text-text-secondary">
                  {c.body}
                </p>
              </li>
            ))}
          </ul>
        )}

        {canAssess ? (
          <form
            className="mt-3 space-y-2"
            onSubmit={(e) => {
              e.preventDefault();
              if (draft.trim()) say.mutate();
            }}
          >
            <TextArea
              label="Add a comment"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={2}
              maxLength={8000}
              placeholder="Their SOC report is a year old."
            />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-body-sm text-text-secondary">
                <input
                  type="checkbox"
                  className="size-4 accent-action-accent"
                  checked={shareWithVendor}
                  onChange={(e) => setShareWithVendor(e.target.checked)}
                />
                Send it to the vendor
              </label>
              <Button type="submit" size="sm" loading={say.isPending} disabled={!draft.trim()}>
                {shareWithVendor ? "Send to vendor" : "Add comment"}
              </Button>
            </div>
          </form>
        ) : null}
      </section>
    </div>
  );
}
