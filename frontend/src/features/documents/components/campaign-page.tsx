import { useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  DetailHeader,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  ErrorState,
  Icon,
  PeopleSelect,
  type Person,
  StatusPill,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import {
  acknowledgeCampaign,
  closeCampaign,
  commentOnCampaign,
  downloadCampaignExport,
  getCampaign,
  getDocumentDetail,
} from "../api";
import { formatDay } from "../review";
import type { Campaign, CampaignRecipient, ExportFormat } from "../types";
import { DocumentContentViewer } from "./document-content-viewer";
import { PENDING_CAMPAIGNS_KEY } from "./acknowledgements-bell";
import { RemindDialog } from "./remind-dialog";

/** Typed in full to sign off. Deliberate beats one-click for a legal attestation. */
const ACK_WORD = "acknowledge";

/** "needs_approval" -> "Needs approval". The enums are already plain words. */
const humanize = (v: string) => {
  const t = v.replace(/_/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
};

function Fact({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-caption text-text-subtle">{label}</dt>
      <dd className="min-w-0 truncate text-right text-body-sm text-text-primary">{value}</dd>
    </div>
  );
}

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
          <>
            <p className="mt-0.5 text-caption text-text-subtle">Pending</p>
            {r.last_reminded_at ? (
              <p className="text-caption text-text-subtle">
                Reminded {fmtDate(r.last_reminded_at)} · {r.reminder_count}{" "}
                {r.reminder_count === 1 ? "time" : "times"}
              </p>
            ) : null}
          </>
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
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { principal } = useAuth();
  const me = principal?.membership_id ?? null;

  const [ackComment, setAckComment] = useState("");
  const [ackConfirm, setAckConfirm] = useState("");
  const [commentBody, setCommentBody] = useState("");
  const [mentioned, setMentioned] = useState<string[]>([]);
  const [reminding, setReminding] = useState(false);

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
      setAckConfirm("");
      toast({ title: "Acknowledged", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "campaign"), tone: "danger" }),
  });

  const comment = useMutation({
    mutationFn: () => commentOnCampaign(campaignId, commentBody.trim(), mentioned),
    onSuccess: (next) => {
      applyCampaign(next);
      setCommentBody("");
      setMentioned([]);
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "comment"), tone: "danger" }),
  });

  const close = useMutation({
    mutationFn: () => closeCampaign(campaignId),
    onSuccess: (next) => {
      applyCampaign(next);
      toast({ title: "Campaign closed", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "campaign"), tone: "danger" }),
  });

  if (campaignQuery.isLoading) {
    return <p className="w-full text-body-md text-text-subtle">Loading…</p>;
  }
  if (campaignQuery.isError) {
    const e = describeError(campaignQuery.error, "campaign");
    return (
      <div className="w-full">
        <DetailHeader backTo="/documents" backLabel="Back to documents" title="Campaign" />
        <ErrorState
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void campaignQuery.refetch() : undefined}
        />
      </div>
    );
  }
  if (!campaign) {
    return (
      <div className="w-full">
        <DetailHeader
          backTo="/documents"
          backLabel="Back to documents"
          title="Campaign not found"
        />
        <p className="text-body-md text-text-subtle">This campaign no longer exists.</p>
      </div>
    );
  }

  const exportAs = (format: ExportFormat) => {
    downloadCampaignExport(campaign.id, format).catch((error: unknown) =>
      toast({ title: errorToast(error, "export"), tone: "danger" }),
    );
  };

  const myRecipient = me ? campaign.recipients.find((r) => r.membership_id === me) ?? null : null;
  const isOwner = Boolean(me && campaign.created_by_membership_id === me);
  // The sender, or anyone who manages documents, may chase people who have not signed.
  const canRemind = isOwner || Boolean(principal?.permissions.includes("documents:manage"));
  const canAcknowledge = Boolean(myRecipient && myRecipient.status === "pending" && campaign.status === "active");
  // Case and stray whitespace should not stand between a reader and signing off.
  const ackConfirmed = ackConfirm.trim().toLowerCase() === ACK_WORD;
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
    <div className="w-full">
      <DetailHeader
        icon="users"
        backTo={`/documents/${campaign.document_id}`}
        backLabel={`Back to ${campaign.document_code}`}
        title={campaign.title}
        chips={
          <>
            <Badge variant={active ? "statusReview" : "neutral"}>
              {active ? "Active" : "Closed"}
            </Badge>
            <span className="tabular text-body-sm text-text-secondary">
              {campaign.acknowledged}/{campaign.total} acknowledged
            </span>
            {campaign.overdue ? <StatusPill status="danger" label="Overdue" /> : null}
          </>
        }
        meta={
          <>
            Started by {campaign.created_by_name}
            {campaign.due_at ? ` · due ${formatDay(campaign.due_at)}` : ""}
          </>
        }
        actions={
          <>
            {active && campaign.pending > 0 && canRemind ? (
              <Button variant="secondary" onClick={() => setReminding(true)}>
                <Icon name="mail" className="size-4" />
                Remind
              </Button>
            ) : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary">
                  <Icon name="export" className="size-4" />
                  Export
                  <Icon name="chev" className="size-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-44">
                <DropdownMenuItem onSelect={() => exportAs("xlsx")}>
                  <Icon name="spreadsheet" className="size-4 text-text-subtle" />
                  Excel
                </DropdownMenuItem>
                <DropdownMenuItem onSelect={() => exportAs("csv")}>
                  <Icon name="doc" className="size-4 text-text-subtle" />
                  CSV
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
            {isOwner && active ? (
              <Button variant="secondary" loading={close.isPending} onClick={() => close.mutate()}>
                Close campaign
              </Button>
            ) : null}
          </>
        }
      />

      {campaign.message ? (
        <p className="mb-5 rounded-md border border-border bg-surface-hover px-4 py-3 text-body-sm text-text-secondary">
          {campaign.message}
        </p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[1.7fr_1fr]">
        <div className="rounded-lg border border-border bg-surface-primary p-1">
          {doc ? (
            <DocumentContentViewer
              doc={doc}
              // A new tab, like document-detail does it. The editor's only exit
              // is window.close(), which silently does nothing unless the tab
              // was opened by script, so navigating here in-place traps the
              // reader in the editor with a dead Close button.
              onEdit={() =>
                window.open(
                  `/documents/${campaign.document_id}/edit`,
                  "_blank",
                  "noopener,noreferrer",
                )
              }
            />
          ) : docQuery.isError ? (
            <p className="p-6 text-body-sm text-status-danger-text">
              {describeError(docQuery.error, "document").message}
            </p>
          ) : (
            <p className="p-6 text-body-sm text-text-subtle">
              {docQuery.isLoading ? "Loading the document…" : "The document is unavailable."}
            </p>
          )}
        </div>

        <div className="space-y-4">
          {/* What you are being asked to sign, before the box that signs it. */}
          {doc ? (
            <Card title="Document">
              <dl className="space-y-2">
                <Fact label="Owner" value={doc.owner?.name ?? "Unassigned"} />
                <Fact label="Reference" value={<span className="font-mono">{doc.code}</span>} />
                <Fact label="Version" value={doc.version} />
                <Fact label="Type" value={humanize(doc.doc_type)} />
                <Fact label="Classification" value={humanize(doc.classification)} />
                <Fact label="Status" value={humanize(doc.lifecycle)} />
                {doc.published_on ? (
                  <Fact label="Published" value={fmtDate(doc.published_on)} />
                ) : null}
                {doc.renewal_date ? (
                  <Fact label="Next review" value={formatDay(doc.renewal_date)} />
                ) : null}
                {doc.frameworks.length > 0 ? (
                  <Fact label="Frameworks" value={doc.frameworks.join(", ")} />
                ) : null}
              </dl>
            </Card>
          ) : null}

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
                <div className="space-y-3">
                  <p className="text-body-sm text-text-secondary">
                    Confirm you have read this document. Your name, the time, and anything you
                    write here are recorded on the audit trail.
                  </p>
                  <div>
                    <label
                      htmlFor="ack-comment"
                      className="mb-1 block text-label-md font-semibold text-text-primary"
                    >
                      Comment <span className="font-normal text-text-subtle">(optional)</span>
                    </label>
                    <textarea
                      id="ack-comment"
                      value={ackComment}
                      onChange={(e) => setAckComment(e.target.value)}
                      placeholder="A question or a note for the owner…"
                      rows={2}
                      className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="ack-confirm"
                      className="mb-1 block text-label-md font-semibold text-text-primary"
                    >
                      Type <span className="font-mono text-text-link">{ACK_WORD}</span> to sign off
                    </label>
                    <input
                      id="ack-confirm"
                      value={ackConfirm}
                      onChange={(e) => setAckConfirm(e.target.value)}
                      autoComplete="off"
                      spellCheck={false}
                      aria-describedby="ack-confirm-help"
                      placeholder={ACK_WORD}
                      className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-sm text-text-primary"
                    />
                    <p id="ack-confirm-help" className="mt-1 text-caption text-text-subtle">
                      Typing it deliberately is what makes this a signature, not a stray click.
                    </p>
                  </div>
                  <Button
                    className="w-full"
                    disabled={!ackConfirmed}
                    loading={acknowledge.isPending}
                    onClick={() => acknowledge.mutate()}
                  >
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

      <RemindDialog campaign={campaign} open={reminding} onOpenChange={setReminding} />
    </div>
  );
}
