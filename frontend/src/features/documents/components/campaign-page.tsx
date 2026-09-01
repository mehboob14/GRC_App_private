import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  Icon,
  PeopleSelect,
  type Person,
  useToast,
} from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import {
  acknowledgeCampaign,
  closeCampaign,
  commentOnCampaign,
  getCampaign,
  getDocumentDetail,
} from "../api";
import type { Campaign, CampaignRecipient } from "../types";
import { DocumentContentViewer } from "./document-content-viewer";
import { PENDING_CAMPAIGNS_KEY } from "./acknowledgements-bell";

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

const fmtDate = (iso: string | null) =>
  iso ? new Date(iso).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : null;

function RecipientRow({ r }: { r: CampaignRecipient }) {
  const done = r.status === "acknowledged";
  return (
    <li className="flex items-start gap-2.5 py-2">
      <Avatar name={r.name} size="sm" seed={r.email} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-body-sm font-semibold text-text-primary">{r.name}</span>
          <Badge variant="role">{r.kind}</Badge>
        </div>
        {done ? (
          <p className="mt-0.5 text-caption text-status-success-text">
            Acknowledged{r.acknowledged_at ? ` · ${relativeTime(r.acknowledged_at)}` : ""}
          </p>
        ) : (
          <p className="mt-0.5 text-caption text-text-subtle">Pending</p>
        )}
        {r.ack_comment ? (
          <p className="mt-1 rounded-sm bg-surface-hover px-2 py-1 text-caption text-text-secondary">
            “{r.ack_comment}”
          </p>
        ) : null}
      </div>
      <Icon
        name={done ? "check" : "clock"}
        className={done ? "size-4 shrink-0 text-status-success-text" : "size-4 shrink-0 text-text-subtle"}
      />
    </li>
  );
}

function Card({ title, action, children }: { title: string; action?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-4">
      <div className="mb-2.5 flex items-center justify-between gap-2">
        <h2 className="font-display text-title-sm text-text-primary">{title}</h2>
        {action}
      </div>
      {children}
    </div>
  );
}

/**
 * A campaign's own page: read the document, see who has acknowledged and who is
 * still pending, discuss it, and — if you are a recipient — sign. Owners close
 * it from here. One page serves both the recipient's sign-off and the owner's
 * tracking, since both need the same document and the same roster.
 */
export function CampaignPage() {
  const { campaignId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const me = principal?.membership_id ?? null;

  const [ackComment, setAckComment] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [mentioned, setMentioned] = useState<string[]>([]);

  const key = ["campaign", campaignId];
  const campaignQuery = useQuery({ queryKey: key, queryFn: () => getCampaign(campaignId) });
  const campaign = campaignQuery.data ?? null;

  const docQuery = useQuery({
    queryKey: ["document-detail", campaign?.document_id],
    queryFn: () => getDocumentDetail(campaign!.document_id),
    enabled: Boolean(campaign?.document_id),
  });

  const applyCampaign = (next: Campaign) => {
    queryClient.setQueryData(key, next);
    queryClient.invalidateQueries({ queryKey: ["document-campaigns", next.document_id] });
  };

  const acknowledge = useMutation({
    mutationFn: () => acknowledgeCampaign(campaignId, ackComment.trim() || undefined),
    onSuccess: (next) => {
      applyCampaign(next);
      queryClient.invalidateQueries({ queryKey: PENDING_CAMPAIGNS_KEY });
      setAckComment("");
      toast({ title: "Acknowledged", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: error instanceof ApiError ? error.message : "Couldn't acknowledge.", tone: "danger" }),
  });

  const comment = useMutation({
    mutationFn: () => commentOnCampaign(campaignId, commentBody.trim(), mentioned),
    onSuccess: (next) => {
      applyCampaign(next);
      setCommentBody("");
      setMentioned([]);
    },
    onError: (error: unknown) =>
      toast({ title: error instanceof ApiError ? error.message : "Couldn't post the comment.", tone: "danger" }),
  });

  const close = useMutation({
    mutationFn: () => closeCampaign(campaignId),
    onSuccess: (next) => {
      applyCampaign(next);
      toast({ title: "Campaign closed", tone: "success" });
    },
  });

  if (campaignQuery.isLoading) {
    return <p className="mx-auto max-w-[1100px] text-body-md text-text-subtle">Loading…</p>;
  }
  if (!campaign) {
    return (
      <div className="mx-auto max-w-[1100px]">
        <Link to="/documents" className="text-body-sm text-text-link">
          ← Documents
        </Link>
        <p className="mt-4 text-body-md text-text-subtle">This campaign no longer exists.</p>
      </div>
    );
  }

  const myRecipient = me ? campaign.recipients.find((r) => r.membership_id === me) ?? null : null;
  const isOwner = Boolean(me && campaign.created_by_membership_id === me);
  const canAcknowledge = Boolean(myRecipient && myRecipient.status === "pending" && campaign.status === "active");
  const active = campaign.status === "active";

  // Participants that can be tagged: recipients plus the owner.
  const participants: Person[] = [
    ...campaign.recipients.map((r) => ({ id: r.membership_id, name: r.name, email: r.email })),
    ...(campaign.created_by_membership_id
      ? [{ id: campaign.created_by_membership_id, name: campaign.created_by_name }]
      : []),
  ].filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i);

  const doc = docQuery.data ?? null;

  return (
    <div className="mx-auto max-w-[1200px]">
      <button
        type="button"
        onClick={() => navigate(`/documents/${campaign.document_id}`)}
        className="flex items-center gap-1.5 text-body-sm text-text-subtle transition-colors hover:text-text-primary"
      >
        <Icon name="arrowl" className="size-4" />
        {campaign.document_code} · {campaign.document_title}
      </button>

      <div className="mb-5 mt-2 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-display text-heading-md text-text-primary">{campaign.title}</h1>
          <p className="mt-1 text-body-sm text-text-subtle">
            Started by {campaign.created_by_name}
            {campaign.due_at ? ` · due ${fmtDate(campaign.due_at)}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={active ? "statusReview" : "neutral"}>{active ? "Active" : "Closed"}</Badge>
          <span className="tabular text-body-sm text-text-secondary">
            {campaign.acknowledged}/{campaign.total} acknowledged
          </span>
          {isOwner && active ? (
            <Button variant="secondary" size="sm" loading={close.isPending} onClick={() => close.mutate()}>
              Close
            </Button>
          ) : null}
        </div>
      </div>

      {campaign.message ? (
        <p className="mb-5 rounded-md border border-border bg-surface-hover px-4 py-3 text-body-sm text-text-secondary">
          {campaign.message}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
        <div className="rounded-lg border border-border bg-surface-primary p-1">
          {doc ? (
            <DocumentContentViewer doc={doc} onEdit={() => navigate(`/documents/${campaign.document_id}/edit`)} />
          ) : (
            <p className="p-6 text-body-sm text-text-subtle">
              {docQuery.isLoading ? "Loading the document…" : "The document is unavailable."}
            </p>
          )}
        </div>

        <div className="space-y-4">
          {/* My sign-off */}
          {myRecipient ? (
            <Card title="Your acknowledgement">
              {myRecipient.status === "acknowledged" ? (
                <div className="flex items-start gap-2 text-body-sm text-status-success-text">
                  <Icon name="check" className="mt-0.5 size-4 shrink-0" />
                  <span>
                    You acknowledged this
                    {myRecipient.acknowledged_at ? ` ${relativeTime(myRecipient.acknowledged_at)}` : ""}.
                  </span>
                </div>
              ) : canAcknowledge ? (
                <div className="space-y-2">
                  <p className="text-body-sm text-text-secondary">
                    Confirm you have read the document. You can add a comment.
                  </p>
                  <textarea
                    value={ackComment}
                    onChange={(e) => setAckComment(e.target.value)}
                    placeholder="Optional comment…"
                    rows={2}
                    className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                  />
                  <Button className="w-full" loading={acknowledge.isPending} onClick={() => acknowledge.mutate()}>
                    <Icon name="check" className="size-4" />
                    Acknowledge
                  </Button>
                </div>
              ) : (
                <p className="text-body-sm text-text-subtle">This campaign is closed.</p>
              )}
            </Card>
          ) : null}

          {/* Roster */}
          <Card title={`Recipients (${campaign.total})`}>
            {campaign.recipients.length === 0 ? (
              <p className="text-body-sm text-text-subtle">No recipients.</p>
            ) : (
              <ul className="divide-y divide-border">
                {campaign.recipients.map((r) => (
                  <RecipientRow key={r.membership_id} r={r} />
                ))}
              </ul>
            )}
          </Card>

          {/* Discussion */}
          <Card title={`Comments (${campaign.comments.length})`}>
            {active ? (
              <div className="mb-3 space-y-2">
                <textarea
                  value={commentBody}
                  onChange={(e) => setCommentBody(e.target.value)}
                  placeholder="Add a comment…"
                  rows={2}
                  className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                />
                <PeopleSelect
                  people={participants}
                  values={mentioned}
                  onChange={setMentioned}
                  placeholder="Tag people…"
                />
                <div className="flex justify-end">
                  <Button
                    size="sm"
                    loading={comment.isPending}
                    disabled={commentBody.trim() === ""}
                    onClick={() => comment.mutate()}
                  >
                    Comment
                  </Button>
                </div>
              </div>
            ) : null}

            {campaign.comments.length === 0 ? (
              <p className="text-body-sm text-text-subtle">No comments yet.</p>
            ) : (
              <ul className="space-y-3">
                {campaign.comments.map((c) => (
                  <li key={c.id} className="flex gap-2.5">
                    <Avatar name={c.author_name} size="sm" />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-baseline gap-2">
                        <span className="text-body-sm font-semibold text-text-primary">{c.author_name}</span>
                        <span className="text-caption text-text-subtle">{relativeTime(c.created_at)}</span>
                      </div>
                      <p className="mt-0.5 whitespace-pre-line text-body-sm text-text-secondary">{c.body}</p>
                      {c.mentioned_names.length > 0 ? (
                        <p className="mt-1 text-caption text-text-subtle">
                          Tagged: {c.mentioned_names.join(", ")}
                        </p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
