import { useState, type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  statusFamilyFor,
  Tooltip,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { invalidateOtherEnds, useLinkedRecords } from "../hooks";
import {
  addLink,
  linksKey,
  removeLink,
  type AnchorType,
  type LinkedRecord,
  type LinkedRecords,
  type LinkType,
} from "../api";
import { humanize, LINK_META, relationLabel } from "../meta";
import { LinkPickerDialog } from "./link-picker-dialog";

const CONTEXT: Record<AnchorType, string> = {
  asset: "this asset",
  vulnerability: "this finding",
  control: "this control",
  document: "this document",
};

/**
 * The records this one is linked to, across modules, grouped by type.
 *
 * Filter chips give the shape at a glance; each group links in place or opens
 * the picker on its type; removing a link asks once, inline, on the row.
 * `groupActions` adds a page specific button to a group (Raise risk).
 */
export function LinkedRecordsPanel({
  anchorType,
  anchorId,
  title = "Linked records",
  groupActions,
  className,
}: {
  anchorType: AnchorType;
  anchorId: string;
  title?: string;
  groupActions?: Partial<Record<LinkType, ReactNode>>;
  className?: string;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = linksKey(anchorType, anchorId);
  const query = useLinkedRecords(anchorType, anchorId);
  const [filter, setFilter] = useState<LinkType | "all">("all");
  const [picker, setPicker] = useState<LinkType | null>(null);
  const [pendingId, setPendingId] = useState<string | null>(null);

  const apply = (next: LinkedRecords) => {
    queryClient.setQueryData(key, next);
    invalidateOtherEnds(queryClient);
  };

  const link = useMutation({
    mutationFn: ({ type, id }: { type: LinkType; id: string }) =>
      addLink(anchorType, anchorId, type, id),
    onMutate: ({ id }) => setPendingId(id),
    onSuccess: (next, { type }) => {
      apply(next);
      toast({ title: `${LINK_META[type].label} linked`, tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "link"), tone: "danger" }),
    onSettled: () => setPendingId(null),
  });

  const unlink = useMutation({
    mutationFn: (record: LinkedRecord) =>
      removeLink(anchorType, anchorId, record.link_id),
    onSuccess: (next, record) => {
      apply(next);
      toast({
        title: `${LINK_META[record.target_type].label} unlinked`,
        tone: "success",
      });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "link"), tone: "danger" }),
  });

  const data = query.data;
  const records = data?.records ?? [];
  const byType = (type: LinkType) =>
    records.filter((r) => r.target_type === type);
  const groups = (data?.offered ?? []).filter(
    (t) => filter === "all" || t === filter,
  );
  // Under "All", empty groups fold into one row so the panel stays short.
  const shown =
    filter === "all" ? groups.filter((t) => byType(t).length > 0) : groups;
  const folded =
    filter === "all" ? groups.filter((t) => byType(t).length === 0) : [];
  const canLink = data?.can_link ?? [];

  return (
    <section
      className={cn(
        "rounded-lg border border-border bg-surface-primary",
        className,
      )}
    >
      <header className="flex flex-wrap items-center gap-3 border-b border-border px-5 py-4">
        <span className="grid size-9 place-items-center rounded-lg bg-action-accent-tint text-action-accent">
          <Icon name="link" className="size-4" />
        </span>
        <div className="min-w-0 flex-1">
          <h2 className="font-display text-title-md text-text-primary">
            {title}
          </h2>
          <p className="text-caption text-text-subtle">
            {data
              ? records.length === 0
                ? "Nothing linked yet"
                : `${records.length} linked across ${new Set(records.map((r) => r.target_type)).size} ${new Set(records.map((r) => r.target_type)).size === 1 ? "module" : "modules"}`
              : "Loading"}
          </p>
        </div>
        {canLink.length > 0 ? (
          <Button onClick={() => setPicker(canLink[0])}>
            <Icon name="plus" className="size-4" />
            Link record
          </Button>
        ) : null}
      </header>

      {query.isLoading ? (
        <div className="space-y-3 p-5">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      ) : query.isError ? (
        <div className="p-5">
          <ErrorState
            title={describeError(query.error, "linked records").title}
            description={describeError(query.error, "linked records").message}
            onRetry={() => void query.refetch()}
          />
        </div>
      ) : data ? (
        <div className="px-5 pb-5">
          <div
            className="flex flex-wrap gap-1.5 py-4"
            role="tablist"
            aria-label="Filter linked records"
          >
            <FilterChip
              active={filter === "all"}
              onClick={() => setFilter("all")}
              label="All"
              count={records.length}
            />
            {data.offered.map((t) => (
              <FilterChip
                key={t}
                active={filter === t}
                onClick={() => setFilter(t)}
                label={LINK_META[t].plural}
                icon={LINK_META[t].icon}
                count={byType(t).length}
              />
            ))}
          </div>

          <div className="space-y-5">
            {shown.map((type) => {
              const rows = byType(type);
              const meta = LINK_META[type];
              const mayLink = canLink.includes(type);
              return (
                <div key={type}>
                  <div className="mb-2 flex items-center gap-2">
                    <Icon
                      name={meta.icon}
                      className="size-4 text-text-subtle"
                    />
                    <h3 className="text-label-md text-text-primary">
                      {meta.plural}
                    </h3>
                    <span className="tabular rounded-full bg-surface-sunken px-1.5 text-caption font-semibold text-text-secondary">
                      {rows.length}
                    </span>
                    <span className="ml-auto flex items-center gap-1">
                      {groupActions?.[type]}
                      {mayLink ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setPicker(type)}
                        >
                          <Icon name="plus" className="size-3.5" />
                          Link
                        </Button>
                      ) : null}
                    </span>
                  </div>
                  {rows.length === 0 ? (
                    <p className="rounded-md bg-surface-sunken px-3 py-3 text-body-sm text-text-subtle">
                      No {meta.plural.toLowerCase()} linked.
                    </p>
                  ) : (
                    <ul className="divide-y divide-border overflow-hidden rounded-md border border-border">
                      {rows.map((record) => (
                        <LinkedRow
                          key={record.link_id}
                          record={record}
                          removing={
                            unlink.isPending &&
                            unlink.variables?.link_id === record.link_id
                          }
                          onRemove={() => unlink.mutate(record)}
                        />
                      ))}
                    </ul>
                  )}
                </div>
              );
            })}
            {folded.length > 0 ? (
              <div className="flex flex-wrap items-center gap-2 rounded-md bg-surface-sunken px-3 py-2.5">
                <span className="mr-1 text-body-sm text-text-subtle">
                  Not linked yet
                </span>
                {folded.map((type) =>
                  canLink.includes(type) ? (
                    <button
                      key={type}
                      type="button"
                      onClick={() => setPicker(type)}
                      className="inline-flex h-7 items-center gap-1.5 rounded-full border border-border bg-surface-primary px-2.5 text-label-sm text-text-secondary transition-colors hover:border-action-accent hover:text-action-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
                    >
                      <Icon name="plus" className="size-3" />
                      {LINK_META[type].plural}
                    </button>
                  ) : (
                    <span
                      key={type}
                      className="inline-flex h-7 items-center gap-1.5 rounded-full px-2.5 text-label-sm text-text-subtle"
                    >
                      <Icon name={LINK_META[type].icon} className="size-3" />
                      {LINK_META[type].plural}
                    </span>
                  ),
                )}
                {folded.map((type) =>
                  groupActions?.[type] ? (
                    <span key={`action-${type}`}>{groupActions[type]}</span>
                  ) : null,
                )}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}

      {data && picker ? (
        <LinkPickerDialog
          open
          onOpenChange={(open) => {
            if (!open) setPicker(null);
          }}
          types={canLink}
          initialType={picker}
          linkedIds={(type) => new Set(byType(type).map((r) => r.target_id))}
          pendingId={pendingId}
          onLink={(type, id) => link.mutate({ type, id })}
          context={CONTEXT[anchorType]}
        />
      ) : null}
    </section>
  );
}

function FilterChip({
  active,
  onClick,
  label,
  count,
  icon,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  count: number;
  icon?: (typeof LINK_META)[LinkType]["icon"];
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        "inline-flex h-8 items-center gap-1.5 rounded-full border px-3 text-label-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        active
          ? "border-action-primary bg-action-primary text-white"
          : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
      )}
    >
      {icon ? <Icon name={icon} className="size-3.5" /> : null}
      {label}
      <span
        className={cn(
          "tabular rounded-full px-1.5 text-caption font-bold",
          active
            ? "bg-white/20 text-white"
            : "bg-surface-sunken text-text-secondary",
        )}
      >
        {count}
      </span>
    </button>
  );
}

function LinkedRow({
  record,
  removing,
  onRemove,
}: {
  record: LinkedRecord;
  removing: boolean;
  onRemove: () => void;
}) {
  const [confirming, setConfirming] = useState(false);
  const meta = LINK_META[record.target_type];
  const relation = relationLabel(record);
  const family = statusFamilyFor(record.status) ?? "neutral";

  return (
    <li className="group flex items-center gap-3 bg-surface-primary px-3 py-2.5 transition-colors hover:bg-surface-hover">
      <span className="grid size-8 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-subtle">
        <Icon name={meta.icon} className="size-4" />
      </span>
      <Link
        to={meta.href(record.target_id)}
        className="min-w-0 flex-1 rounded-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent"
      >
        <span className="block truncate text-body-sm font-medium text-text-primary group-hover:text-text-link">
          {record.code ? (
            <span className="mr-1.5 font-mono text-caption font-semibold text-text-subtle">
              {record.code}
            </span>
          ) : null}
          {record.title}
        </span>
        {record.detail ? (
          <span className="block truncate text-caption text-text-subtle">
            {humanize(record.detail)}
          </span>
        ) : null}
      </Link>
      {relation ? (
        <span className="hidden shrink-0 rounded-full bg-action-accent-tint px-2 py-0.5 text-caption font-semibold text-action-primary sm:inline">
          {relation}
        </span>
      ) : null}
      <StatusPill
        status={family}
        label={humanize(record.status)}
        kind="inline"
      />
      {record.can_unlink ? (
        confirming ? (
          <span className="flex shrink-0 items-center gap-1">
            <Button
              size="sm"
              variant="destructive-2"
              loading={removing}
              onClick={onRemove}
            >
              Remove
            </Button>
            <Button
              size="sm"
              variant="ghost"
              disabled={removing}
              onClick={() => setConfirming(false)}
            >
              Keep
            </Button>
          </span>
        ) : (
          <Tooltip content="Remove link">
            <Button
              size="icon-sm"
              variant="ghost"
              aria-label={`Remove link to ${record.title}`}
              onClick={() => setConfirming(true)}
              className="opacity-60 group-hover:opacity-100 focus-visible:opacity-100"
            >
              <Icon name="x" className="size-3.5" />
            </Button>
          </Tooltip>
        )
      ) : null}
    </li>
  );
}
