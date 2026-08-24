import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  Tooltip,
  useToast,
} from "@/components/ui";
import { controlsApi, evidenceApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { getAccessToken } from "@/lib/auth/session";
import type { Evidence, EvidenceFreshness, ReviewStatus } from "@/lib/api/types";
import { LinkControlsDialog } from "./link-controls-dialog";
import { EvidenceViewer } from "./evidence-viewer";
import { SuggestedMappingsTeaser } from "@/features/compliance/components/suggested-mappings-teaser";

const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
};

const REVIEW_META: Record<
  ReviewStatus,
  { label: string; family: "success" | "danger" | "pending" }
> = {
  pending: { label: "Pending review", family: "pending" },
  approved: { label: "Approved", family: "success" },
  rejected: { label: "Rejected", family: "danger" },
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
      new Date(`${iso}T00:00:00`),
    );
  } catch {
    return iso;
  }
}

function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

async function downloadEvidence(item: Evidence): Promise<void> {
  const response = await fetch(evidenceApi.downloadUrl(item.id), {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = item.filename ?? item.title;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/** Linkage to the other objects evidence can support. Controls work today; the
 *  rest are listed so the shape is visible, each explicit about arriving with
 *  its module rather than rendering an empty list that reads as "none". */
function LinkageSection({
  item,
  canManage,
  onLink,
}: {
  item: Evidence;
  canManage: boolean;
  onLink: () => void;
}) {
  const soon = [
    { icon: "risk", label: "Risks", note: "Arrives with the risk module" },
    { icon: "box", label: "Assets", note: "Arrives with the asset inventory" },
    { icon: "book", label: "Policies", note: "Arrives with policies & documents" },
  ] as const;

  return (
    <div className="rounded-lg border border-border bg-surface-primary">
      {/* Controls — the one linkage that works today */}
      <div className="p-5">
        <div className="mb-3 flex items-center justify-between gap-3">
          <h2 className="font-display text-title-md text-text-primary">
            Controls
            <span className="ml-2 tabular text-body-sm text-text-subtle">
              {item.control_codes.length}
            </span>
          </h2>
          {canManage ? (
            <Button size="sm" variant="secondary" onClick={onLink}>
              <Icon name="plus" className="size-4" />
              Link controls
            </Button>
          ) : null}
        </div>
        {item.control_ids.length === 0 ? (
          <EmptyState
            icon="shield"
            title="Not linked to any control"
            description="Evidence that supports no control proves nothing. Link it to the controls it evidences."
            action={
              canManage ? <Button onClick={onLink}>Link controls</Button> : undefined
            }
          />
        ) : (
          <ul className="flex flex-wrap gap-1.5">
            {item.control_ids.map((id, index) => (
              <li key={id}>
                <Link
                  to={`/controls/${id}`}
                  className="inline-flex rounded-xs bg-action-accent-tint px-2 py-1 font-display text-caption font-bold text-text-link transition-colors duration-80 ease-state hover:bg-action-accent hover:text-text-inverse"
                >
                  {item.control_codes[index] ?? "control"}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* The other objects evidence will support, in the same card so the shape
          is visible — each explicit about arriving with its module rather than
          rendering an empty list that reads as "none". */}
      {soon.map((row) => (
        <Tooltip key={row.label} content={row.note}>
          <div className="flex items-center gap-3 border-t border-border px-5 py-3.5">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-surface-sunken text-text-faint">
              <Icon name={row.icon} className="size-4" aria-hidden />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-body-md font-semibold text-text-secondary">
                {row.label}
              </span>
              <span className="block text-caption text-text-subtle">{row.note}</span>
            </span>
            <span className="font-sans text-overline uppercase text-text-subtle">
              Soon
            </span>
          </div>
        </Tooltip>
      ))}
    </div>
  );
}

export function EvidenceDetailPage() {
  const { evidenceId = "" } = useParams();
  const { principal } = useAuth();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const canManage = Boolean(principal?.permissions.includes("evidence:manage"));
  const canReview = Boolean(principal?.permissions.includes("evidence:review"));
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

  const item = itemQuery.data;

  const unlinkMutation = useMutation({
    mutationFn: (controlId: string) =>
      evidenceApi.update(evidenceId, {
        control_ids: (item?.control_ids ?? []).filter((id) => id !== controlId),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["evidence"] });
      await queryClient.invalidateQueries({ queryKey: ["audit"] });
      toast({ title: "Control unlinked", tone: "neutral" });
    },
  });

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
    onError: (error: unknown) =>
      toast({
        title: error instanceof ApiError ? error.message : "Couldn't record the review.",
        tone: "danger",
      }),
  });

  const meta = useMemo(
    () => (item ? FRESHNESS[item.freshness] : null),
    [item],
  );

  if (itemQuery.isError) {
    return (
      <div className="mx-auto max-w-[1200px]">
        <ErrorState
          title="Couldn’t load this evidence"
          description={
            itemQuery.error instanceof ApiError
              ? itemQuery.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          onRetry={() => void itemQuery.refetch()}
        />
      </div>
    );
  }

  if (itemQuery.isLoading || !item || !meta) {
    return (
      <div className="mx-auto max-w-[1200px] space-y-4">
        <Skeleton className="h-6 w-56" />
        <Skeleton className="h-10 w-[26rem]" />
        <Skeleton className="h-20 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1200px]">
      <nav aria-label="Breadcrumb" className="mb-3 flex items-center gap-1.5 text-body-sm">
        <Link className="text-text-subtle hover:text-text-primary" to="/evidence">
          Evidence
        </Link>
        <Icon name="chevr" className="size-3.5 text-text-faint" aria-hidden />
        <span className="truncate font-semibold text-text-primary">{item.title}</span>
      </nav>

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <StatusPill status={meta.family} label={meta.label} />
            <Badge variant="neutral">{item.kind === "file" ? "File" : "Link"}</Badge>
            <Badge variant="neutral">{item.evidence_type.replace(/_/g, " ")}</Badge>
          </div>
          <h1 className="font-display text-heading-lg text-text-primary">
            {item.title}
          </h1>
          {item.description ? (
            <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
              {item.description}
            </p>
          ) : null}
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {item.kind === "file" ? (
            <>
              <Button onClick={() => setPreviewing(true)}>
                <Icon name="search" className="size-4" />
                View evidence
              </Button>
              <Button
                variant="secondary"
                onClick={() =>
                  void downloadEvidence(item).catch(() =>
                    toast({ title: "Couldn't download the file.", tone: "danger" }),
                  )
                }
              >
                <Icon name="doc" className="size-4" />
                Download
              </Button>
            </>
          ) : item.link_url ? (
            <Button asChild>
              <a href={item.link_url} target="_blank" rel="noopener noreferrer">
                <Icon name="globe" className="size-4" />
                Open link
              </a>
            </Button>
          ) : null}
        </div>
      </div>

      <div className="mt-5 grid gap-4 lg:grid-cols-[1fr_20rem]">
        <div className="min-w-0 space-y-4">
          {/* Controls lead: what this item actually supports is the point of the
              record. The artefact itself opens from the header, on request. */}
          <LinkageSection
            item={item}
            canManage={canManage}
            onLink={() => setLinking(true)}
          />

          <SuggestedMappingsTeaser />
        </div>

        <aside className="space-y-4">
          {/* Review — the four-eyes step. Evidence is a claim until someone with
              evidence:review signs off. */}
          <section className="rounded-lg border border-border bg-surface-primary p-5">
            <div className="mb-3 flex items-center justify-between gap-2">
              <h2 className="font-display text-title-md text-text-primary">
                Review
              </h2>
              <StatusPill
                status={REVIEW_META[item.review_status].family}
                label={REVIEW_META[item.review_status].label}
              />
            </div>
            {item.reviewed_by_name ? (
              <p className="text-body-sm text-text-secondary">
                {item.review_status === "approved" ? "Approved" : "Rejected"} by{" "}
                <span className="font-semibold text-text-primary">
                  {item.reviewed_by_name}
                </span>
                {item.reviewed_at ? (
                  <span className="text-text-subtle">
                    {" "}
                    · {formatDate(item.reviewed_at.slice(0, 10))}
                  </span>
                ) : null}
              </p>
            ) : (
              <p className="text-body-sm text-text-subtle">
                Not yet reviewed.
              </p>
            )}
            {item.review_note ? (
              <p className="mt-2 rounded-md border border-border bg-surface-sunken px-3 py-2 text-body-sm text-text-secondary">
                “{item.review_note}”
              </p>
            ) : null}
            {canReview ? (
              <div className="mt-3 flex gap-2">
                <Button
                  size="sm"
                  disabled={
                    reviewMutation.isPending || item.review_status === "approved"
                  }
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
          </section>

          <section className="rounded-lg border border-border bg-surface-primary p-5">
            <h2 className="mb-1 font-display text-title-md text-text-primary">
              Details
            </h2>
            <dl>
              {[
                ["Owner", item.owner_name ?? "Unassigned"],
                ["Source", item.source_label ?? "—"],
                ["Collected", formatDate(item.collected_at)],
                ["Renewal", formatDate(item.renewal_date)],
                ["Type", item.evidence_type.replace(/_/g, " ")],
                ...(item.kind === "file"
                  ? ([
                      ["File", item.filename ?? "—"],
                      [
                        "Size",
                        `${item.content_type ?? "file"} · ${formatBytes(item.size_bytes)}`,
                      ],
                    ] as [string, string][])
                  : ([["Link", item.link_url ?? "—"]] as [string, string][])),
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 last:border-0"
                >
                  <dt className="shrink-0 text-body-sm text-text-subtle">{label}</dt>
                  <dd className="min-w-0 break-all text-right text-body-sm font-semibold text-text-primary">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>
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

          <EvidenceViewer item={item} />

          <DialogFooter>
            <Button variant="secondary" onClick={() => setPreviewing(false)}>
              Close
            </Button>
            {item.kind === "file" ? (
              <Button
                onClick={() =>
                  void downloadEvidence(item).catch(() =>
                    toast({ title: "Couldn't download the file.", tone: "danger" }),
                  )
                }
              >
                <Icon name="doc" className="size-4" />
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
        linkedIds={item.control_ids}
        onSave={async (ids) => {
          await evidenceApi.update(evidenceId, { control_ids: ids });
          await queryClient.invalidateQueries({ queryKey: ["evidence"] });
          await queryClient.invalidateQueries({ queryKey: ["audit"] });
          toast({ title: "Controls updated", tone: "success" });
        }}
        onUnlink={(id) => unlinkMutation.mutate(id)}
      />

      <Dialog open={rejecting} onOpenChange={setRejecting}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Reject this evidence</DialogTitle>
            <DialogDescription>
              Say what needs fixing. The owner sees this reason, and it is
              recorded on the audit trail.
            </DialogDescription>
          </DialogHeader>
          <div className="px-6">
            <textarea
              value={rejectNote}
              onChange={(e) => setRejectNote(e.target.value)}
              rows={3}
              autoFocus
              placeholder="e.g. This screenshot is from staging — attach the production console."
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
                reviewMutation.mutate({
                  decision: "rejected",
                  note: rejectNote.trim(),
                })
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
