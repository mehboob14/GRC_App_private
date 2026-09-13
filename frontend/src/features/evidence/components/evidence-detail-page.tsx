import { useMemo, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  CodeChip,
  DetailHeader,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  Icon,
  StatusPill,
  TabStrip,
  useToast,
} from "@/components/ui";
import { auditApi, controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { useAuth } from "@/lib/auth/auth-context";
import type { Evidence } from "@/lib/api/types";
import { LinkControlsDialog } from "./link-controls-dialog";
import { EvidenceViewer, fetchEvidenceBlob } from "./evidence-viewer";
import { LinkedRecordsSection } from "./linked-records-section";
import { SuggestedMappings } from "@/features/compliance/components/suggested-mappings-teaser";
import { FRESHNESS, REVIEW_META, formatBytes, formatDate, formatDateTime } from "../tokens";

type TabId = "overview" | "controls" | "links" | "activity";

export function EvidenceDetailPage() {
  const { evidenceId = "" } = useParams();
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("evidence:manage"));
  const canReview = Boolean(principal?.permissions.includes("evidence:review"));

  const [tab, setTab] = useState<TabId>("overview");
  const [linking, setLinking] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [rejectNote, setRejectNote] = useState("");

  const itemQuery = useQuery({
    queryKey: ["evidence", evidenceId],
    queryFn: () => evidenceApi.get(evidenceId),
    enabled: evidenceId.length > 0,
  });
  const controlsQuery = useQuery({
    queryKey: ["controls"],
    queryFn: () => controlsApi.list(),
    enabled: linking,
  });
  // Counts on the tabs, so the reader knows what is behind one before opening
  // it. Shares its key with the section itself, so React Query fetches once.
  const linksQuery = useQuery({
    queryKey: ["evidence-links", evidenceId],
    queryFn: () => evidenceApi.links(evidenceId),
    enabled: evidenceId.length > 0,
  });

  const item = itemQuery.data;

  const reviewMutation = useMutation({
    mutationFn: (body: { decision: "approved" | "rejected"; note?: string }) =>
      evidenceApi.review(evidenceId, body),
    onSuccess: async (_data, body) => {
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      setRejecting(false);
      setRejectNote("");
      toast({
        title: body.decision === "approved" ? "Evidence approved" : "Evidence rejected",
        tone: body.decision === "approved" ? "success" : "neutral",
      });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "review"), tone: "danger" }),
  });

  const tabs = useMemo(
    () => [
      { id: "overview", label: "Overview" },
      { id: "controls", label: "Controls", count: item?.control_links.length ?? 0 },
      { id: "links", label: "Linked records", count: linksQuery.data?.length ?? 0 },
      { id: "activity", label: "Activity" },
    ],
    [item?.control_links.length, linksQuery.data?.length],
  );

  async function download(target: Evidence) {
    try {
      const blob = await fetchEvidenceBlob(target.id)();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = target.filename ?? target.title;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast({ title: errorToast(error, "file"), tone: "danger" });
    }
  }

  if (itemQuery.isError) {
    const failure = describeError(itemQuery.error, "evidence item");
    return (
      <div className="w-full">
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          // A 403 or a 404 will not change on a second try, so no retry offered.
          onRetry={failure.retryable ? () => void itemQuery.refetch() : undefined}
        />
      </div>
    );
  }

  if (itemQuery.isLoading) {
    return <p className="w-full text-body-md text-text-subtle">Loading…</p>;
  }

  if (!item) {
    return (
      <div className="w-full">
        <DetailHeader backTo="/evidence" backLabel="Back to evidence" title="Evidence not found" />
        <p className="text-body-md text-text-subtle">
          This item may have been removed, or it belongs to another workspace.
        </p>
      </div>
    );
  }

  const freshness = FRESHNESS[item.freshness];
  const review = REVIEW_META[item.review_status];

  return (
    <div className="w-full">
      <DetailHeader
        icon="doc"
        backTo="/evidence"
        backLabel="Back to evidence"
        title={item.title}
        chips={
          <>
            <StatusPill status={freshness.family} label={freshness.label} />
            {/* Only once a control is linked is a verdict actually due. */}
            {item.review_required ? (
              <StatusPill status={review.family} label={review.label} />
            ) : null}
            <Badge variant="neutral">{item.kind === "file" ? "File" : "Link"}</Badge>
            <Badge variant="neutral">{item.evidence_type.replace(/_/g, " ")}</Badge>
          </>
        }
        meta={item.description ? <span className="block max-w-2xl">{item.description}</span> : null}
        actions={
          <>
            {item.kind === "file" ? (
              <Button onClick={() => setPreviewing(true)}>
                <Icon name="search" className="size-4" />
                Open full screen
              </Button>
            ) : item.link_url ? (
              <Button asChild>
                <a href={item.link_url} target="_blank" rel="noopener noreferrer">
                  <Icon name="globe" className="size-4" />
                  Open link
                </a>
              </Button>
            ) : null}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="secondary">
                  Actions
                  <Icon name="chev" className="size-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {item.kind === "file" ? (
                  <DropdownMenuItem onSelect={() => void download(item)}>
                    <Icon name="download" className="size-4" />
                    Download original
                  </DropdownMenuItem>
                ) : null}
                {canManage ? (
                  <DropdownMenuItem onSelect={() => setLinking(true)}>
                    <Icon name="link" className="size-4" />
                    Link controls
                  </DropdownMenuItem>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </>
        }
      />

      {/* The facts a reader scans before deciding to read anything else. */}
      <div className="flex flex-wrap items-center gap-x-8 gap-y-2">
        <Field label="Owner">{item.owner_name ?? "Unassigned"}</Field>
        <Field label="Collected">{formatDate(item.collected_at)}</Field>
        <Field label="Valid until">{formatDate(item.renewal_date)}</Field>
        <Field label="Controls">{item.control_links.length || "None"}</Field>
        {item.kind === "file" ? (
          <Field label="File">
            {item.filename ?? "Unnamed file"}
            <span className="ml-1.5 font-normal text-text-subtle">
              {formatBytes(item.size_bytes)}
            </span>
          </Field>
        ) : null}
      </div>

      <TabStrip
        label="Evidence sections"
        items={tabs}
        value={tab}
        onSelect={(id) => setTab(id as TabId)}
        className="mt-6"
        inline
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-4">
          {tab === "overview" ? (
            <Panel
              title={item.kind === "file" ? "The file" : "The link"}
              action={
                item.kind === "file" ? (
                  <Button size="sm" variant="secondary" onClick={() => setPreviewing(true)}>
                    Full screen
                  </Button>
                ) : undefined
              }
            >
              {/* Inline, not behind a click: the artefact is the record. */}
              <EvidenceViewer item={item} heightClass="h-[34rem]" />
            </Panel>
          ) : null}

          {tab === "controls" ? (
            <>
              <ControlsPanel item={item} canManage={canManage} onLink={() => setLinking(true)} />
              <SuggestedMappings
                evidenceId={evidenceId}
                onApproved={async () => {
                  await queryClient.invalidateQueries({ queryKey: ["evidence"] });
                  await queryClient.invalidateQueries({ queryKey: ["audit"] });
                }}
              />
            </>
          ) : null}

          {tab === "links" ? (
            <LinkedRecordsSection evidenceId={evidenceId} canManage={canManage} />
          ) : null}

          {tab === "activity" ? <ActivityPanel evidenceId={evidenceId} /> : null}
        </div>

        <aside className="space-y-4">
          {/* Review — the four-eyes step. Evidence is a claim until someone with
              evidence:review signs off. */}
          <Panel
            title="Review"
            action={
              item.review_required ? (
                <StatusPill status={review.family} label={review.label} />
              ) : (
                <span className="text-caption text-text-subtle">Not required yet</span>
              )
            }
          >
            {!item.review_required ? (
              <p className="text-body-sm text-text-subtle">
                Review starts once this evidence is linked to a control. The control's owner
                approves it, rejects it, or asks for a change. A verdict on evidence that
                supports no control would be a verdict on nothing.
              </p>
            ) : item.reviewed_by_name ? (
              <p className="text-body-sm text-text-secondary">
                {item.review_status === "approved" ? "Approved" : "Rejected"} by{" "}
                <span className="font-semibold text-text-primary">{item.reviewed_by_name}</span>
                {item.reviewed_at ? (
                  <span className="text-text-subtle"> · {formatDateTime(item.reviewed_at)}</span>
                ) : null}
              </p>
            ) : (
              <p className="text-body-sm text-text-subtle">Not yet reviewed.</p>
            )}
            {item.review_note ? (
              <p className="mt-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-body-sm text-text-secondary">
                “{item.review_note}”
              </p>
            ) : null}
            {canReview && item.review_required ? (
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  disabled={reviewMutation.isPending || item.review_status === "approved"}
                  onClick={() => reviewMutation.mutate({ decision: "approved" })}
                >
                  <Icon name="check" className="size-4" />
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={reviewMutation.isPending}
                  onClick={() => setRejecting(true)}
                >
                  Reject
                </Button>
              </div>
            ) : null}
          </Panel>

          <Panel title="Details">
            <dl>
              <Meta label="Type">{item.evidence_type.replace(/_/g, " ")}</Meta>
              <Meta label="Owner">{item.owner_name ?? "Unassigned"}</Meta>
              <Meta label="Source label">{item.source_label ?? "Not set"}</Meta>
              <Meta label="Origin">
                {item.source ? (
                  item.source
                ) : (
                  <span className="font-normal text-text-subtle">Uploaded by hand</span>
                )}
              </Meta>
              <Meta label="Collected">{formatDate(item.collected_at)}</Meta>
              <Meta label="Valid until">{formatDate(item.renewal_date)}</Meta>
              {item.kind === "file" ? (
                <>
                  <Meta label="File">{item.filename ?? "Unnamed file"}</Meta>
                  <Meta label="Format">
                    {item.content_type ?? "file"} · {formatBytes(item.size_bytes)}
                  </Meta>
                  {/* The integrity hash: what proves the bytes an auditor sees
                      are the bytes that were uploaded. */}
                  <Meta label="SHA-256">
                    {item.sha256 ? (
                      <span className="break-all font-mono text-caption">{item.sha256}</span>
                    ) : (
                      "Not recorded"
                    )}
                  </Meta>
                </>
              ) : (
                <Meta label="Link">
                  {item.link_url ? (
                    <a
                      href={item.link_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="break-all text-text-link hover:underline"
                    >
                      {item.link_url}
                    </a>
                  ) : (
                    "No link"
                  )}
                </Meta>
              )}
            </dl>
          </Panel>
        </aside>
      </div>

      {/* Wide by design: a document needs room, and Radix gives Esc, focus
          trapping and focus restore for free. Unmounting on close revokes the
          viewer's blob URL, so nothing is held after the dialog goes away. */}
      <Dialog open={previewing} onOpenChange={setPreviewing}>
        <DialogContent className="w-[min(96vw,72rem)] max-w-none">
          <DialogHeader>
            <DialogTitle className="truncate">{item.title}</DialogTitle>
            <DialogDescription className="truncate">
              {item.kind === "file"
                ? `${item.filename ?? ""} · ${item.content_type ?? ""} · ${formatBytes(item.size_bytes)}`
                : item.link_url}
            </DialogDescription>
          </DialogHeader>

          <EvidenceViewer item={item} heightClass="h-[70vh]" />

          <DialogFooter>
            <Button variant="secondary" onClick={() => setPreviewing(false)}>
              Close
            </Button>
            {item.kind === "file" ? (
              <Button onClick={() => void download(item)}>
                <Icon name="download" className="size-4" />
                Download
              </Button>
            ) : null}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <LinkControlsDialog
        open={linking}
        onOpenChange={setLinking}
        controls={controlsQuery.data ?? []}
        loadError={
          controlsQuery.isError ? describeError(controlsQuery.error, "control list").message : null
        }
        linkedIds={item.control_ids}
        onSave={async (ids) => {
          await evidenceApi.update(evidenceId, { control_ids: ids });
          await queryClient.invalidateQueries({ queryKey: ["evidence"] });
          await queryClient.invalidateQueries({ queryKey: ["audit"] });
          toast({ title: "Controls updated", tone: "success" });
        }}
      />

      <Dialog open={rejecting} onOpenChange={setRejecting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject this evidence</DialogTitle>
            <DialogDescription>
              Say what needs fixing. The owner sees this reason, and it is recorded on the audit
              trail.
            </DialogDescription>
          </DialogHeader>
          <div className="px-6">
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              rows={3}
              autoFocus
              placeholder="e.g. This screenshot is from staging, attach the production console."
              className="w-full rounded-sm border border-border bg-surface-primary px-3 py-2 text-body-md text-text-primary placeholder:text-text-faint focus:border-action-accent focus:outline-none"
            />
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setRejecting(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={reviewMutation.isPending || rejectNote.trim() === ""}
              onClick={() =>
                reviewMutation.mutate({ decision: "rejected", note: rejectNote.trim() })
              }
            >
              Reject evidence
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

/** The controls this evidence supports — the point of the record. Reads
 *  `control_links`, so each chip can carry the criteria it satisfies. */
function ControlsPanel({
  item,
  canManage,
  onLink,
}: {
  item: Evidence;
  canManage: boolean;
  onLink: () => void;
}) {
  return (
    <Panel
      title="Controls"
      count={item.control_links.length}
      action={
        canManage ? (
          <Button size="sm" variant="secondary" onClick={onLink}>
            <Icon name="plus" className="size-4" />
            Link controls
          </Button>
        ) : undefined
      }
    >
      {item.control_links.length === 0 ? (
        <EmptyState
          icon="shield"
          title="Not linked to any control"
          description="Evidence that supports no control proves nothing. Link it to the controls it evidences."
          action={canManage ? <Button onClick={onLink}>Link controls</Button> : undefined}
        />
      ) : (
        <ul className="space-y-1.5">
          {item.control_links.map((link, index) => (
            <li
              key={link.code}
              className="flex flex-wrap items-center gap-2 rounded-sm border border-border px-3 py-2"
            >
              <Link to={`/controls/${item.control_ids[index] ?? ""}`}>
                <CodeChip code={link.code} />
              </Link>
              {link.criteria.length > 0 ? (
                <span className="text-caption text-text-subtle">{link.criteria.join(" · ")}</span>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

/** The audit trail for this record, scoped server-side so the client never
 *  pulls the whole log to filter it. */
function ActivityPanel({ evidenceId }: { evidenceId: string }) {
  const query = useQuery({
    queryKey: ["audit", "evidence", evidenceId],
    queryFn: () => auditApi.list(undefined, false, { type: "evidence", id: evidenceId }),
  });

  const failure = query.isError ? describeError(query.error, "activity") : null;
  const events = query.data?.items ?? [];

  return (
    <Panel title="Activity">
      {failure ? (
        <p className="text-body-sm text-status-danger-text">{failure.message}</p>
      ) : query.isLoading ? (
        <p className="text-body-sm text-text-subtle">Loading…</p>
      ) : events.length === 0 ? (
        <p className="text-body-sm text-text-subtle">Nothing recorded yet.</p>
      ) : (
        <ol className="space-y-2.5">
          {events.map((event) => (
            <li key={event.id} className="flex gap-3">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-border" aria-hidden />
              <span className="min-w-0">
                <span className="block text-body-sm text-text-primary">
                  <span className="font-semibold">
                    {event.actor_label || event.actor_type.replace(/_/g, " ")}
                  </span>{" "}
                  {event.action.replace(/_/g, " ")}d this evidence
                </span>
                <span className="block text-caption text-text-subtle">
                  {formatDateTime(event.occurred_at)}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </Panel>
  );
}

// -- primitives ---------------------------------------------------------------

function Panel({
  title,
  count,
  action,
  children,
}: {
  title: string;
  count?: number;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          {title}
          {count !== undefined ? (
            <span className="ml-2 tabular text-body-sm text-text-subtle">{count}</span>
          ) : null}
        </h2>
        {action}
      </div>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="block">
      <span className="block text-caption text-text-subtle">{label}</span>
      <span className="block text-body-sm font-semibold text-text-primary">{children}</span>
    </span>
  );
}

function Meta({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 last:border-0">
      <dt className="shrink-0 text-body-sm text-text-subtle">{label}</dt>
      <dd className="min-w-0 break-words text-right text-body-sm font-semibold text-text-primary">
        {children}
      </dd>
    </div>
  );
}
