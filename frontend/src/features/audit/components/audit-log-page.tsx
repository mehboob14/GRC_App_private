import { useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerHeader,
  DrawerTitle,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  StatusPill,
  Table,
  TableIconButton,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  type FilterFacetOption,
  type StatusFamily,
} from "@/components/ui";
import { auditApi } from "@/lib/api/endpoints";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import type { AuditAction, AuditEvent } from "@/lib/api/types";

/**
 * Audit actions reuse the StatusPill anatomy (DS §6.2). This map is the single
 * source of truth for both the pill and the Action facet, so the word and its
 * colour stay in lockstep across the screen.
 */
const ACTION_META: Record<AuditAction, { label: string; family: StatusFamily }> =
  {
    create: { label: "Create", family: "success" },
    update: { label: "Update", family: "progress" },
    transition: { label: "Transition", family: "progress" },
    approve: { label: "Approve", family: "success" },
    delete: { label: "Delete", family: "danger" },
  };

const ACTION_OPTIONS: FilterFacetOption[] = (
  Object.keys(ACTION_META) as AuditAction[]
).map((value) => ({ value, label: ACTION_META[value].label }));

/** actor_type is a closed set present on every row — safe to filter on. */
const ACTOR_TYPE_LABEL: Record<AuditEvent["actor_type"], string> = {
  membership: "Membership",
  platform_admin: "Platform admin",
  system: "System",
};

const ACTOR_TYPE_OPTIONS: FilterFacetOption[] = (
  Object.keys(ACTOR_TYPE_LABEL) as AuditEvent["actor_type"][]
).map((value) => ({ value, label: ACTOR_TYPE_LABEL[value] }));

function shortId(id: string | null | undefined): string {
  return id ? id.slice(0, 8) : "";
}

function humanizeType(type: string): string {
  const spaced = type.replace(/_/g, " ").trim();
  if (!spaced) return "Object";
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * actor_label / object_label are best-effort humanised strings and may be
 * absent or empty. Compose a stable fallback from the fields that always
 * exist so the page never renders `undefined` or blanks an avatar seed.
 */
function actorLabelOf(event: AuditEvent): string {
  const label = event.actor_label?.trim();
  if (label) return label;
  if (event.actor_type === "system") return "System";
  const base = ACTOR_TYPE_LABEL[event.actor_type];
  const short = shortId(event.actor_id);
  return short ? `${base} · ${short}` : base;
}

function objectLabelOf(event: AuditEvent): string {
  const label = event.object_label?.trim();
  if (label) return label;
  const base = humanizeType(event.object_type);
  const short = shortId(event.object_id);
  return short ? `${base} · ${short}` : base;
}

function formatWhen(iso: string) {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

/** Canonical entity code-chip cell pattern (DS §6.4). */
function ObjectTypeChip({ type }: { type: string }) {
  return (
    <span className="inline-flex shrink-0 rounded-xs bg-action-accent-tint px-1.5 py-0.5 font-display text-code-chip text-text-link">
      {type}
    </span>
  );
}

function SnapshotBlock({
  label,
  value,
  emptyNote,
}: {
  label: string;
  value: Record<string, unknown> | null;
  emptyNote: string;
}) {
  return (
    <div>
      <p className="type-overline mb-1.5">{label}</p>
      {value ? (
        <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-md border border-border bg-surface-sunken p-3 font-mono text-body-sm text-text-primary">
          {JSON.stringify(value, null, 2)}
        </pre>
      ) : (
        <p className="rounded-md border border-border bg-surface-sunken p-3 text-body-sm text-text-subtle">
          {emptyNote}
        </p>
      )}
    </div>
  );
}

export function AuditLogPage() {
  const { principal } = useAuth();
  const [actorTypeFilter, setActorTypeFilter] = useState<string[]>([]);
  const [actionFilter, setActionFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [selected, setSelected] = useState<AuditEvent | null>(null);

  const query = useInfiniteQuery({
    queryKey: ["audit-log", principal?.tenant_id],
    queryFn: ({ pageParam }) => auditApi.list(pageParam),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });

  const events = useMemo(
    () => query.data?.pages.flatMap((page) => page.items) ?? [],
    [query.data],
  );

  // object_type is an open set, so its facet options come from the events
  // loaded so far; actor_type and action are closed sets with fixed options.
  const typeOptions = useMemo<FilterFacetOption[]>(
    () =>
      [...new Set(events.map((e) => e.object_type))]
        .sort()
        .map((type) => ({ value: type, label: humanizeType(type) })),
    [events],
  );

  // Week 1: facets filter client-side over the pages loaded so far — the
  // audit endpoint only takes a cursor. Server-side filter params arrive with
  // the fuller audit search in a later phase. Every predicate reads a field
  // that exists on every row (actor_type, action, object_type).
  const filtered = events.filter(
    (event) =>
      (actorTypeFilter.length === 0 ||
        actorTypeFilter.includes(event.actor_type)) &&
      (actionFilter.length === 0 || actionFilter.includes(event.action)) &&
      (typeFilter.length === 0 || typeFilter.includes(event.object_type)),
  );

  const hasFilters =
    actorTypeFilter.length > 0 ||
    actionFilter.length > 0 ||
    typeFilter.length > 0;
  const activeFilterNames = [
    ...actorTypeFilter.map(
      (value) => ACTOR_TYPE_OPTIONS.find((o) => o.value === value)?.label ?? value,
    ),
    ...actionFilter.map(
      (value) => ACTION_OPTIONS.find((o) => o.value === value)?.label ?? value,
    ),
    ...typeFilter.map(
      (value) =>
        typeOptions.find((o) => o.value === value)?.label ?? humanizeType(value),
    ),
  ];

  function clearFilters() {
    setActorTypeFilter([]);
    setActionFilter([]);
    setTypeFilter([]);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <p className="type-overline mb-2">Access &amp; Audit</p>
      <h1 className="font-display text-heading-lg text-text-primary">
        Audit log
      </h1>
      <p className="mt-1 text-body-md text-text-secondary">
        Append-only trail for this workspace. Never updated or deleted.
      </p>

      <div className="mb-3 mt-5 flex flex-wrap items-center gap-2">
        <FilterFacet
          label="Actor type"
          options={ACTOR_TYPE_OPTIONS}
          values={actorTypeFilter}
          onChange={setActorTypeFilter}
        />
        <FilterFacet
          label="Action"
          options={ACTION_OPTIONS}
          values={actionFilter}
          onChange={setActionFilter}
        />
        <FilterFacet
          label="Object type"
          options={typeOptions}
          values={typeFilter}
          onChange={setTypeFilter}
        />
        {hasFilters ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear filters
          </Button>
        ) : null}
      </div>

      {query.isLoading ? (
        <TableSkeleton rows={10} density="compact" />
      ) : query.isError ? (
        <ErrorState
          title="Couldn’t load the audit log"
          description={
            query.error instanceof ApiError
              ? query.error.message
              : "The request failed. Retry, or contact support if it keeps happening."
          }
          referenceId={
            query.error instanceof ApiError
              ? query.error.correlationId
              : undefined
          }
          onRetry={() => void query.refetch()}
        />
      ) : events.length === 0 ? (
        <EmptyState
          icon="doc"
          title="No events yet"
          description="State-changing actions land here append-only as your team works."
        />
      ) : filtered.length === 0 ? (
        <EmptyState
          variant="no-match"
          title="No events match your filters"
          description={`Try removing ${activeFilterNames
            .map((name) => `'${name}'`)
            .join(" or ")}.`}
          onClearFilters={clearFilters}
        />
      ) : (
        <>
          {/* compact density — DS §6.3 assigns 40px rows to audit trails */}
          <Table density="compact">
            <THead>
              <TR>
                <TH>Actor</TH>
                <TH>Action</TH>
                <TH>Object</TH>
                <TH className="text-right">When</TH>
                <TH>
                  <span className="sr-only">Details</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {filtered.map((event) => {
                const actor = actorLabelOf(event);
                const object = objectLabelOf(event);
                const action = ACTION_META[event.action];
                return (
                  <TR
                    key={event.id}
                    className="cursor-pointer"
                    onClick={() => setSelected(event)}
                  >
                    <TD>
                      <span className="flex items-center gap-2">
                        <Avatar
                          name={actor}
                          seed={event.actor_id ?? actor}
                          size="sm"
                        />
                        <span className="text-body-sm text-text-secondary">
                          {actor}
                        </span>
                      </span>
                    </TD>
                    <TD>
                      <StatusPill status={action.family} label={action.label} />
                    </TD>
                    <TD>
                      <span className="flex items-center gap-2">
                        <ObjectTypeChip type={event.object_type} />
                        <span className="truncate text-body-md text-text-primary">
                          {object}
                        </span>
                      </span>
                    </TD>
                    <TD className="tabular whitespace-nowrap text-right text-body-sm text-text-subtle">
                      {formatWhen(event.occurred_at)}
                    </TD>
                    <TD className="w-10">
                      <TableIconButton
                        aria-label={`View details of ${action.label} on ${object}`}
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelected(event);
                        }}
                      >
                        <Icon name="chevr" className="size-4" />
                      </TableIconButton>
                    </TD>
                  </TR>
                );
              })}
            </TBody>
          </Table>

          <div className="mt-3 flex items-center justify-between gap-3">
            <p className="text-caption text-text-subtle">
              Showing <span className="tabular">{filtered.length}</span> of{" "}
              <span className="tabular">{events.length}</span> loaded events
            </p>
            {query.hasNextPage ? (
              <Button
                variant="secondary"
                size="sm"
                loading={query.isFetchingNextPage}
                onClick={() => void query.fetchNextPage()}
              >
                Load older events
              </Button>
            ) : null}
          </div>
        </>
      )}

      {/* Row detail is a peek → drawer per the overlay decision matrix (§7.1). */}
      <Drawer
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DrawerContent size="md">
          {selected ? (
            <>
              <DrawerHeader>
                <DrawerTitle className="flex items-center gap-2">
                  <span>{ACTION_META[selected.action].label}</span>
                  <ObjectTypeChip type={selected.object_type} />
                </DrawerTitle>
                <DrawerDescription>
                  {objectLabelOf(selected)} · by {actorLabelOf(selected)} ·{" "}
                  <span className="tabular">
                    {formatWhen(selected.occurred_at)}
                  </span>
                </DrawerDescription>
              </DrawerHeader>
              <DrawerBody className="space-y-4">
                <SnapshotBlock
                  label="Before"
                  value={selected.before}
                  emptyNote="No prior state — the object was created by this event."
                />
                <SnapshotBlock
                  label="After"
                  value={selected.after}
                  emptyNote="No resulting state — the object was removed by this event."
                />
                <div>
                  <p className="type-overline mb-1.5">Event</p>
                  <dl className="space-y-1 text-body-sm">
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Event id</dt>
                      <dd className="tabular truncate font-mono text-text-secondary">
                        {selected.id}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Actor type</dt>
                      <dd className="text-text-secondary">
                        {ACTOR_TYPE_LABEL[selected.actor_type]}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Object id</dt>
                      <dd className="tabular truncate font-mono text-text-secondary">
                        {selected.object_id}
                      </dd>
                    </div>
                  </dl>
                </div>
              </DrawerBody>
            </>
          ) : null}
        </DrawerContent>
      </Drawer>
    </div>
  );
}
