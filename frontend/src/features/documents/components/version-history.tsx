import { Fragment, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  ConfirmDialog,
  Icon,
  StatusPill,
  Table,
  TBody,
  TD,
  TH,
  THead,
  TR,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { getVersionDiff, restoreVersion } from "../api";
import type { DiffBlock, DocumentDetail, DocumentVersion, VersionDiff } from "../types";

/**
 * Version history: what changed, who changed it, when — and putting it back.
 *
 * Restoring is the only undo that can survive a reload. TipTap's history lives
 * in memory and is gone the moment the editor unmounts, and `document_versions`
 * is append-only behind a database trigger, so a restore can only ever write a
 * NEW version carrying the old text. That turns out to be the useful shape:
 * nothing is destroyed, the version you left is still in the list, and
 * restoring it again is the redo. The list *is* the undo stack, and it lives in
 * Postgres — so it holds across a reload, a new session, and a different person.
 */

const HEADING = /^h[1-6]$/;

function fmtWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/** A one-line "what changed" for the row, before anyone opens the diff. */
function statLine(diff: VersionDiff): string {
  if (!diff.comparable) return diff.reason ?? "Not comparable";
  const { stats } = diff;
  const parts: string[] = [];
  if (stats.blocks_changed) parts.push(`${stats.blocks_changed} edited`);
  if (stats.blocks_added) parts.push(`${stats.blocks_added} added`);
  if (stats.blocks_removed) parts.push(`${stats.blocks_removed} removed`);
  const words =
    stats.words_added || stats.words_removed
      ? ` · +${stats.words_added}/-${stats.words_removed} words`
      : "";
  if (!parts.length) return diff.compared_with ? "No text changed" : "First version";
  return `${parts.join(", ")} ${parts.length === 1 ? "paragraph" : "paragraphs"}${words}`;
}

export function VersionHistory({
  documentId,
  versions,
  canManage,
  lifecycle,
}: {
  documentId: string;
  versions: DocumentVersion[];
  canManage: boolean;
  lifecycle: string;
}) {
  const [open, setOpen] = useState<string | null>(null);
  const [restoring, setRestoring] = useState<DocumentVersion | null>(null);

  if (versions.length === 0) {
    return <p className="text-body-sm text-text-subtle">No versions yet.</p>;
  }

  return (
    <>
      <Table>
        <THead>
          <TR>
            <TH numeric>Version</TH>
            <TH>Change</TH>
            <TH>When</TH>
            <TH>By</TH>
            <TH>Summary</TH>
            <TH>Status</TH>
            <TH />
          </TR>
        </THead>
        <TBody>
          {versions.map((v) => (
            <Fragment key={v.id}>
              <TR>
                <TD numeric>
                  <span className="font-medium text-text-primary">{v.version}</span>
                </TD>
                <TD>
                  <Badge variant="neutral">{v.change_type}</Badge>
                </TD>
                <TD>{fmtWhen(v.created_at)}</TD>
                <TD>{v.created_by}</TD>
                <TD>
                  <span className="text-body-sm text-text-secondary">{v.summary}</span>
                </TD>
                <TD>
                  <StatusPill
                    status={v.status === "current" ? "success" : "neutral"}
                    label={v.status === "current" ? "Current" : "Superseded"}
                  />
                </TD>
                <TD className="text-right">
                  <div className="flex justify-end gap-1.5">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setOpen(open === v.id ? null : v.id)}
                      aria-expanded={open === v.id}
                    >
                      <Icon
                        name="chev"
                        className={cn("size-4 transition-transform", open === v.id && "rotate-180")}
                      />
                      {open === v.id ? "Hide changes" : "What changed"}
                    </Button>
                    {canManage && v.status !== "current" ? (
                      <Button size="sm" variant="secondary" onClick={() => setRestoring(v)}>
                        Restore
                      </Button>
                    ) : null}
                  </div>
                </TD>
              </TR>
              {open === v.id ? (
                <TR>
                  <TD colSpan={7} className="bg-surface-sunken p-0">
                    <VersionDiffView documentId={documentId} version={v} />
                  </TD>
                </TR>
              ) : null}
            </Fragment>
          ))}
        </TBody>
      </Table>

      {restoring ? (
        <RestoreDialog
          documentId={documentId}
          version={restoring}
          lifecycle={lifecycle}
          onClose={() => setRestoring(null)}
        />
      ) : null}
    </>
  );
}

function VersionDiffView({
  documentId,
  version,
}: {
  documentId: string;
  version: DocumentVersion;
}) {
  const query = useQuery({
    queryKey: ["document-version-diff", documentId, version.id],
    queryFn: () => getVersionDiff(documentId, version.id),
  });

  if (query.isLoading) {
    return <p className="px-4 py-6 text-body-sm text-text-subtle">Working out what changed…</p>;
  }
  if (query.isError) {
    const failure = describeError(query.error, "version");
    return <p className="px-4 py-6 text-body-sm text-status-danger-text">{failure.message}</p>;
  }

  const diff = query.data!;
  const changed = diff.blocks.filter((b) => b.kind !== "equal");

  return (
    <div className="px-4 py-4">
      <p className="mb-3 text-caption text-text-subtle">
        <span className="font-semibold text-text-secondary">v{diff.version_no}</span>
        {diff.compared_with ? ` compared with v${diff.compared_with}` : " · first version"}
        {" · "}
        {statLine(diff)}
      </p>

      {!diff.comparable ? (
        <p className="text-body-sm text-text-subtle">{diff.reason}</p>
      ) : changed.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          The text is identical to the previous version. Only formatting or metadata changed.
        </p>
      ) : (
        <div className="space-y-2">
          {/* Only the blocks that actually changed. An unchanged 40-paragraph
              policy rendered in full buries the two lines someone edited. */}
          {changed.map((block, i) => (
            <DiffBlockRow key={i} block={block} />
          ))}
        </div>
      )}
    </div>
  );
}

function DiffBlockRow({ block }: { block: DiffBlock }) {
  const label =
    block.kind === "added" ? "Added" : block.kind === "removed" ? "Removed" : "Edited";
  const tone =
    block.kind === "added"
      ? "border-status-success-border bg-status-success-bg"
      : block.kind === "removed"
        ? "border-status-danger-border bg-status-danger-bg"
        : "border-border bg-surface-primary";

  return (
    <div className={cn("rounded-md border px-3 py-2", tone)}>
      <p className="mb-1 flex items-center gap-2 text-caption text-text-subtle">
        <span className="font-semibold uppercase tracking-wider">{label}</span>
        {HEADING.test(block.tag) ? <Badge variant="neutral">heading</Badge> : null}
        {block.tag === "li" ? <Badge variant="neutral">list item</Badge> : null}
      </p>
      <p
        className={cn(
          "whitespace-pre-wrap text-body-sm text-text-primary",
          HEADING.test(block.tag) && "font-display font-semibold",
        )}
      >
        {/* Text nodes, never markup: the backend sends tagged text precisely so
            this never has to be dangerouslySetInnerHTML. */}
        {block.segments.map((seg, i) => (
          <span
            key={i}
            className={cn(
              seg.kind === "added" && "rounded-xs bg-status-success-bg text-status-success-text underline decoration-2",
              seg.kind === "removed" && "rounded-xs bg-status-danger-bg text-status-danger-text line-through",
            )}
          >
            {seg.text}
            {i < block.segments.length - 1 ? " " : null}
          </span>
        ))}
      </p>
    </div>
  );
}

function RestoreDialog({
  documentId,
  version,
  lifecycle,
  onClose,
}: {
  documentId: string;
  version: DocumentVersion;
  lifecycle: string;
  onClose: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const willDemote = lifecycle === "approved" || lifecycle === "published";

  const restore = useMutation({
    mutationFn: () => restoreVersion(documentId, version.id),
    onSuccess: (next: DocumentDetail) => {
      queryClient.setQueryData(["documents", documentId], next);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      onClose();
      toast({ title: `Restored v${version.version}`, tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "version"), tone: "danger" }),
  });

  return (
    <ConfirmDialog
      open
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title={`Restore v${version.version}?`}
      confirmLabel="Restore this version"
      loading={restore.isPending}
      onConfirm={() => restore.mutate()}
      consequence={
        <>
          <p className="text-body-sm text-text-secondary">
            This writes the text of v{version.version} as a new version. Nothing is deleted — the
            current version stays in the history, and you can restore it back at any time.
          </p>
          {willDemote ? (
            <p className="mt-2 rounded-md border border-status-warning-border bg-status-warning-bg px-3 py-2 text-caption text-status-warning-text">
              This document is {lifecycle}. Changing its text returns it to draft and clears the
              approvals, because they were given against wording that will no longer be current.
              It has to go through approval again before it is published.
            </p>
          ) : null}
        </>
      }
    />
  );
}
