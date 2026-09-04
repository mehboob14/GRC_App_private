import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  DetailHeader,
  ErrorState,
  Icon,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import { decideApproval, getDocumentDetail, mergeIntoDocumentDetail } from "../api";
import type { ApprovalAssignee, Document } from "../types";
import { DocumentContentViewer } from "./document-content-viewer";
import { PENDING_APPROVALS_KEY } from "./acknowledgements-bell";

const TIER_ROLE: Record<number, string> = { 1: "Reviewer", 2: "Approver" };

/** "needs_approval" -> "Needs approval". The enums are already plain words. */
const humanize = (v: string) => {
  const t = v.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

function relativeTime(iso: string): string {
  const seconds = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.round(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString();
}

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-caption text-text-subtle">{label}</dt>
      <dd className="min-w-0 truncate text-right text-body-sm text-text-primary">{value}</dd>
    </div>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-4">
      <h2 className="mb-2.5 font-display text-title-sm text-text-primary">{title}</h2>
      {children}
    </div>
  );
}

function AssigneeRow({ a }: { a: ApprovalAssignee }) {
  const done = a.decision !== "pending";
  const icon = a.decision === "approved" ? "check" : a.decision === "rejected" ? "x" : "clock";
  const tone =
    a.decision === "approved"
      ? "text-status-success-text"
      : a.decision === "rejected"
        ? "text-status-danger-text"
        : "text-text-subtle";
  return (
    <li className="flex items-start gap-2.5 py-2">
      <Avatar name={a.name} size="sm" />
      <div className="min-w-0 flex-1">
        <span className="truncate text-body-sm font-semibold text-text-primary">{a.name}</span>
        <p className={`mt-0.5 text-caption ${tone}`}>
          {a.decision === "approved"
            ? `Approved${a.decided_at ? ` · ${relativeTime(a.decided_at)}` : ""}`
            : a.decision === "rejected"
              ? `Rejected${a.decided_at ? ` · ${relativeTime(a.decided_at)}` : ""}`
              : "Waiting"}
        </p>
        {a.note ? (
          <p className="mt-1 rounded-sm bg-surface-hover px-2 py-1 text-caption text-text-secondary">
            “{a.note}”
          </p>
        ) : null}
      </div>
      <Icon name={done ? icon : "clock"} className={`size-4 shrink-0 ${tone}`} />
    </li>
  );
}

/**
 * One tier's review, on its own page: read the document, see who else is on
 * this step and what they decided, and — if it is waiting on you — decide.
 * Reached from a "please review" notification, the same way an
 * acknowledgement campaign is.
 */
export function DocumentApprovalPage() {
  const { documentId = "", tier: tierParam = "" } = useParams();
  const tierNumber = Number(tierParam);
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const me = principal?.membership_id ?? null;

  const [note, setNote] = useState("");
  const [confirmText, setConfirmText] = useState("");

  const key = ["documents", documentId];
  const query = useQuery({
    queryKey: key,
    queryFn: () => getDocumentDetail(documentId),
    enabled: Boolean(documentId),
  });
  const doc = query.data ?? null;
  const tier = doc?.approvals.find((a) => a.tier === tierNumber) ?? null;

  const decide = useMutation({
    mutationFn: (decision: "approved" | "rejected") =>
      decideApproval(documentId, tierNumber, decision, note.trim() || undefined),
    onSuccess: (next: Document, decision) => {
      mergeIntoDocumentDetail(queryClient, documentId, next);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: PENDING_APPROVALS_KEY });
      setConfirmText("");
      toast({
        title:
          decision === "approved"
            ? next.lifecycle === "published"
              ? "Approved — the document is now published"
              : "Approved"
            : "Sent back to draft",
        tone: decision === "approved" ? "success" : "neutral",
      });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "review"), tone: "danger" }),
  });

  if (query.isLoading) {
    return <p className="w-full text-body-md text-text-subtle">Loading…</p>;
  }
  if (query.isError) {
    const e = describeError(query.error, "document");
    return (
      <div className="w-full">
        <DetailHeader backTo="/documents" backLabel="Back to documents" title="Review" />
        <ErrorState
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void query.refetch() : undefined}
        />
      </div>
    );
  }
  if (!doc || !tier) {
    return (
      <div className="w-full">
        <DetailHeader backTo="/documents" backLabel="Back to documents" title="Review not found" />
        <p className="text-body-md text-text-subtle">
          This review step no longer exists. It may have been reassigned or the document may
          have moved on.
        </p>
      </div>
    );
  }

  const canDecide = tier.status === "pending" && tier.my_decision === "pending";
  const myAssignee = me ? tier.assignees.find((a) => a.membership_id === me) ?? null : null;
  const wantsApprove = confirmText.trim().toLowerCase() === "approve";
  const wantsReject = confirmText.trim().toLowerCase() === "reject";
  const roleLabel = TIER_ROLE[tier.tier] ?? "Reviewer";

  return (
    <div className="w-full">
      <DetailHeader
        backTo={`/documents/${doc.id}`}
        backLabel={`Back to ${doc.code}`}
        title={doc.title}
        chips={
          <>
            <Badge variant="role">{`Tier ${tier.tier} · ${roleLabel}`}</Badge>
            <Badge variant={tier.status === "approved" ? "statusPass" : "statusReview"}>
              {humanize(tier.status)}
            </Badge>
          </>
        }
        meta={<>Asked by {doc.owner?.name ?? "the document owner"}</>}
      />

      <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
        <div className="rounded-lg border border-border bg-surface-primary p-1">
          <DocumentContentViewer
            doc={doc}
            onEdit={() =>
              window.open(`/documents/${doc.id}/edit`, "_blank", "noopener,noreferrer")
            }
          />
        </div>

        <div className="space-y-4">
          <Card title="Document">
            <dl className="space-y-2">
              <Fact label="Owner" value={doc.owner?.name ?? "Unassigned"} />
              <Fact label="Reference" value={<span className="font-mono">{doc.code}</span>} />
              <Fact label="Version" value={doc.version} />
              <Fact label="Type" value={humanize(doc.doc_type)} />
              <Fact label="Classification" value={humanize(doc.classification)} />
              {doc.frameworks.length > 0 ? (
                <Fact label="Frameworks" value={doc.frameworks.join(", ")} />
              ) : null}
            </dl>
          </Card>

          <Card title="Your decision">
            {!myAssignee ? (
              <p className="text-body-sm text-text-subtle">
                You were not asked to review this step.
              </p>
            ) : myAssignee.decision !== "pending" ? (
              <div
                className={`flex items-start gap-2 text-body-sm ${
                  myAssignee.decision === "approved"
                    ? "text-status-success-text"
                    : "text-status-danger-text"
                }`}
              >
                <Icon
                  name={myAssignee.decision === "approved" ? "check" : "x"}
                  className="mt-0.5 size-4 shrink-0"
                />
                <span>
                  You {myAssignee.decision === "approved" ? "approved" : "rejected"} this
                  {myAssignee.decided_at ? ` ${relativeTime(myAssignee.decided_at)}` : ""}.
                </span>
              </div>
            ) : canDecide ? (
              <div className="space-y-3">
                <p className="text-body-sm text-text-secondary">
                  Read the document, then approve or send it back. Your name, the time, and
                  anything you write here are recorded on the audit trail.
                </p>
                <div>
                  <label
                    htmlFor="decision-note"
                    className="mb-1 block text-label-md font-semibold text-text-primary"
                  >
                    Comment <span className="font-normal text-text-subtle">(optional)</span>
                  </label>
                  <textarea
                    id="decision-note"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="A note for the record, or why you're sending it back…"
                    rows={2}
                    className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                  />
                </div>
                <div>
                  <label
                    htmlFor="decision-confirm"
                    className="mb-1 block text-label-md font-semibold text-text-primary"
                  >
                    Type <span className="font-mono text-text-link">approve</span> or{" "}
                    <span className="font-mono text-text-link">reject</span> to confirm
                  </label>
                  <input
                    id="decision-confirm"
                    value={confirmText}
                    onChange={(e) => setConfirmText(e.target.value)}
                    autoComplete="off"
                    spellCheck={false}
                    aria-describedby="decision-confirm-help"
                    placeholder="approve"
                    className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                  />
                  <p id="decision-confirm-help" className="mt-1 text-caption text-text-subtle">
                    Typing it deliberately is what makes this a decision, not a stray click.
                  </p>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={!wantsReject || decide.isPending}
                    onClick={() => decide.mutate("rejected")}
                    className="flex-1 rounded-sm border border-status-danger-border bg-status-danger-bg px-3 py-2 text-body-sm font-semibold text-status-danger-text transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Send back
                  </button>
                  <button
                    type="button"
                    disabled={!wantsApprove || decide.isPending}
                    onClick={() => decide.mutate("approved")}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-sm bg-action-accent px-3 py-2 text-body-sm font-semibold text-text-inverse transition-colors disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <Icon name="check" className="size-4" />
                    Approve
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-body-sm text-text-subtle">
                This step is not open for a decision right now.
              </p>
            )}
          </Card>

          <Card title={`${roleLabel}s (${tier.assignees.length})`}>
            {tier.assignees.length === 0 ? (
              <p className="text-body-sm text-text-subtle">Nobody assigned.</p>
            ) : (
              <ul className="divide-y divide-border">
                {tier.assignees.map((a) => (
                  <AssigneeRow key={a.membership_id} a={a} />
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
