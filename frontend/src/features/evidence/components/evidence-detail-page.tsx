import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
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
import type { Evidence, EvidenceFreshness } from "@/lib/api/types";
import { LinkControlsDialog } from "./link-controls-dialog";
import { EvidenceViewer } from "./evidence-viewer";

const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
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
    <div className="space-y-3">
      <div className="rounded-lg border border-border bg-surface-primary p-5">
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

      {soon.map((row) => (
        <Tooltip key={row.label} content={row.note}>
          <div className="flex items-center gap-3 rounded-lg border border-dashed border-border bg-surface-sunken px-5 py-4">
            <span className="flex size-8 shrink-0 items-center justify-center rounded-md bg-surface-hover text-text-faint">
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
  const [linking, setLinking] = useState(false);

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
          ) : item.link_url ? (
            <Button variant="secondary" asChild>
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
          <section className="rounded-lg border border-border bg-surface-primary p-5">
            <h2 className="mb-3 font-display text-title-md text-text-primary">
              Preview
            </h2>
            <EvidenceViewer item={item} />
          </section>

          <LinkageSection
            item={item}
            canManage={canManage}
            onLink={() => setLinking(true)}
          />
        </div>

        <aside className="space-y-4">
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
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="flex items-baseline justify-between gap-3 border-b border-border py-2.5 last:border-0"
                >
                  <dt className="shrink-0 text-body-sm text-text-subtle">{label}</dt>
                  <dd className="min-w-0 text-right text-body-sm font-semibold text-text-primary">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          </section>

          {item.kind === "file" ? (
            <section className="rounded-lg border border-border bg-surface-primary p-5">
              <h2 className="mb-3 font-display text-title-md text-text-primary">
                File
              </h2>
              <dl className="space-y-2 text-body-sm">
                <div>
                  <dt className="text-text-subtle">Filename</dt>
                  <dd className="break-all text-text-primary">{item.filename}</dd>
                </div>
                <div>
                  <dt className="text-text-subtle">Type · size</dt>
                  <dd className="text-text-primary">
                    {item.content_type} · {formatBytes(item.size_bytes)}
                  </dd>
                </div>
              </dl>
              <p className="mt-3 flex items-start gap-2 border-t border-border pt-3 text-caption text-text-subtle">
                <Icon name="check" className="mt-0.5 size-3.5 shrink-0 text-status-success-text" />
                Integrity hash recorded at upload, so a later copy can be proven
                identical to this one.
              </p>
            </section>
          ) : null}
        </aside>
      </div>

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
    </div>
  );
}
