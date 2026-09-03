import { useMemo, useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import {
  Avatar,
  Button,
  Checkbox,
  ColumnPicker,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PageHeader,
  StatusPill,
  Table,
  TableIconButton,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
  type ColumnDef,
  type FilterFacetOption,
  type StatusFamily,
} from "@/components/ui";
import { auditApi } from "@/lib/api/endpoints";
import { describeError } from "@/lib/api/describe-error";
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

function humanizeType(type: string): string {
  const spaced = type.replace(/_/g, " ").trim();
  if (!spaced) return "Object";
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

// The backend resolves the actor's and object's real names; these only fill in
// a clean humanised kind (never an id) when a lookup comes back empty.
function actorLabelOf(event: AuditEvent): string {
  return (
    event.actor_label?.trim() ||
    (event.actor_type === "system"
      ? "System"
      : ACTOR_TYPE_LABEL[event.actor_type])
  );
}

/** A name carried in the event's own snapshot — works even for objects since
 *  deleted, and reflects the name as it was at the time of the event. */
function snapshotName(event: AuditEvent): string | null {
  const snap = event.after ?? event.before;
  if (!snap) return null;
  for (const key of ["name", "full_name", "title", "email"]) {
    const value = snap[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function objectLabelOf(event: AuditEvent): string {
  const label = event.object_label?.trim();
  const typeName = humanizeType(event.object_type);
  // The backend resolved a real name (differs from the plain kind) → use it.
  if (label && label !== typeName) return label;
  // Else fall back to the name the snapshot captured, then to the kind.
  return snapshotName(event) ?? label ?? typeName;
}

const ACTION_VERB: Record<AuditAction, string> = {
  create: "created",
  update: "updated",
  transition: "moved",
  approve: "approved",
  delete: "removed",
};

// Snapshot bookkeeping columns that carry no meaning in a plain-English change.
const NOISE_FIELDS = new Set([
  "id",
  "tenant_id",
  "created_at",
  "updated_at",
  "occurred_at",
]);

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/** snake_case enum values read as prose: `pending_retest` → "Pending retest". */
function prettyValue(value: unknown): string {
  if (typeof value === "string" && /^[a-z][a-z0-9_]*$/.test(value)) {
    const words = value.replace(/_/g, " ");
    return words.charAt(0).toUpperCase() + words.slice(1);
  }
  return formatValue(value);
}

type FieldChange = { field: string; from: string; to: string };

/** The fields that actually differ between before/after, ignoring bookkeeping. */
function changesOf(
  before: Record<string, unknown> | null,
  after: Record<string, unknown> | null,
): FieldChange[] {
  const keys = new Set([
    ...(before ? Object.keys(before) : []),
    ...(after ? Object.keys(after) : []),
  ]);
  const out: FieldChange[] = [];
  for (const key of keys) {
    if (NOISE_FIELDS.has(key)) continue;
    const from = before?.[key];
    const to = after?.[key];
    if (JSON.stringify(from) !== JSON.stringify(to)) {
      out.push({
        field: key.replace(/_/g, " "),
        from: prettyValue(from),
        to: prettyValue(to),
      });
    }
  }
  return out;
}

/**
 * The state field a transition moved. Modules don't agree on the key — the
 * vulnerability engine calls it `state`, assets/tasks `status`, documents
 * `lifecycle`, task sign-off `approval` — so probe them in order.
 */
const STATE_KEYS = ["state", "status", "lifecycle", "approval", "decision"] as const;

function stateChangeOf(event: AuditEvent): { field: string; from: unknown; to: unknown } | null {
  for (const key of STATE_KEYS) {
    const from = event.before?.[key];
    const to = event.after?.[key];
    if (from === undefined && to === undefined) continue;
    if (JSON.stringify(from) !== JSON.stringify(to)) return { field: key, from, to };
  }
  return null;
}

/**
 * A full plain-English sentence answering who did what, exactly — e.g.
 * `Mehboob changed state of finding "CVE-2021-44228" from Pending retest to Fixed`,
 * `Alex created role "Analyst"`, `Jordan updated name, owner on asset "api-01"`.
 */
function activityOf(event: AuditEvent): string {
  const actor = actorLabelOf(event);
  const typeName = humanizeType(event.object_type).toLowerCase();
  const objName = objectLabelOf(event);
  const named = objName.toLowerCase() !== typeName;
  const objPart = named ? `${typeName} “${objName}”` : `a ${typeName}`;

  // A state move is the headline: say which field moved, and between what.
  if (event.action === "transition" || event.action === "approve") {
    const move = stateChangeOf(event);
    if (move) {
      const field = move.field.replace(/_/g, " ");
      if (move.from === undefined || move.from === null || move.from === "") {
        return `${actor} set ${field} of ${objPart} to ${prettyValue(move.to)}`;
      }
      return `${actor} changed ${field} of ${objPart} from ${prettyValue(move.from)} to ${prettyValue(move.to)}`;
    }
  }

  const changes = changesOf(event.before, event.after);

  if (event.action === "create") return `${actor} created ${objPart}`;
  if (event.action === "delete") return `${actor} removed ${objPart}`;

  // update, or a transition/approve whose snapshot carried no state key.
  if (changes.length === 1) {
    const [c] = changes;
    return `${actor} changed ${c.field} of ${objPart} from ${c.from} to ${c.to}`;
  }
  if (changes.length > 1) {
    const names = changes.map((c) => c.field);
    const shown = names.slice(0, 3).join(", ");
    const rest = names.length > 3 ? ` and ${names.length - 3} more` : "";
    return `${actor} updated ${shown}${rest} on ${objPart}`;
  }
  return `${actor} ${ACTION_VERB[event.action]} ${objPart}`;
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

/**
 * Optional columns only. "When" identifies an audit row (a trail is read by
 * timestamp) and the trailing details button is structural, so neither hides.
 */
const AUDIT_COLUMNS = [
  { key: "user", label: "User" },
  { key: "action", label: "Action" },
  { key: "object", label: "Object" },
  { key: "activity", label: "Activity" },
] as const satisfies readonly ColumnDef<string>[];

export function AuditLogPage() {
  const { principal } = useAuth();
  const [actorTypeFilter, setActorTypeFilter] = useState<string[]>([]);
  const [actionFilter, setActionFilter] = useState<string[]>([]);
  const [typeFilter, setTypeFilter] = useState<string[]>([]);
  const [selected, setSelected] = useState<AuditEvent | null>(null);
  const [includeSystem, setIncludeSystem] = useState(false);
  const cols = useColumnPrefs("verity.audit.columns", AUDIT_COLUMNS);

  const query = useInfiniteQuery({
    queryKey: ["audit-log", principal?.tenant_id, includeSystem],
    queryFn: ({ pageParam }) => auditApi.list(pageParam, includeSystem),
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

  // Newest first is the trail's natural order and the order the endpoint
  // returns, so "when" descending is the initial sort and clicking it is a
  // no-op until you ask for something else.
  const { thProps, sortRows } = useTableSort<AuditEvent, "user" | "action" | "object" | "when">(
    null,
    {
      user: actorLabelOf,
      action: (event) => ACTION_META[event.action].label,
      object: objectLabelOf,
      when: (event) => new Date(event.occurred_at),
    },
    "desc",
  );

  const failure = query.isError ? describeError(query.error, "audit log") : null;

  return (
    <div>
      <PageHeader eyebrow="Access and audit" title="Audit log" />

      <Toolbar
        searchLabel="Filter audit log"
        actions={
          /* Auth/provisioning telemetry is hidden by default — this reveals it. */
          <label className="flex cursor-pointer items-center gap-2 text-body-sm text-text-secondary">
            <Checkbox
              checked={includeSystem}
              onCheckedChange={(value) => setIncludeSystem(value === true)}
            />
            Show system events
          </label>
        }
      >
        <FilterFacet
          label="User type"
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
      </Toolbar>

      {query.isLoading ? (
        <TableSkeleton rows={10} density="compact" />
      ) : failure && events.length === 0 ? (
        <ErrorState
          title={failure.title}
          description={failure.message}
          referenceId={failure.referenceId}
          onRetry={failure.retryable ? () => void query.refetch() : undefined}
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
          <Table density="compact" actions={<ColumnPicker {...cols} />}>
            <THead>
              <TR>
                {cols.isVisible("user") ? (
                  <TH {...thProps("user")}>User</TH>
                ) : null}
                {cols.isVisible("action") ? (
                  <TH {...thProps("action")}>Action</TH>
                ) : null}
                {/* Activity carries the meaning, so it gets the room; Object is
                    a chip plus a name and is held narrow. */}
                {cols.isVisible("object") ? (
                  <TH {...thProps("object")} className="w-[160px]">
                    Object
                  </TH>
                ) : null}
                {cols.isVisible("activity") ? <TH className="w-1/2">Activity</TH> : null}
                <TH {...thProps("when")}>When</TH>
                <TH>
                  <span className="sr-only">Details</span>
                </TH>
              </TR>
            </THead>
            <TBody>
              {sortRows(filtered).map((event) => {
                const actor = actorLabelOf(event);
                const object = objectLabelOf(event);
                // Only a real name is worth showing next to the type chip —
                // "credentials · Credentials" is just the kind said twice.
                const objectHasName =
                  object.toLowerCase() !==
                  humanizeType(event.object_type).toLowerCase();
                const action = ACTION_META[event.action];
                const activity = activityOf(event);
                return (
                  <TR
                    key={event.id}
                    className="cursor-pointer"
                    onClick={() => setSelected(event)}
                  >
                    {cols.isVisible("user") ? (
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
                    ) : null}
                    {cols.isVisible("action") ? (
                      <TD>
                        <StatusPill status={action.family} label={action.label} />
                      </TD>
                    ) : null}
                    {cols.isVisible("object") ? (
                      <TD className="w-[160px]">
                        <span className="flex min-w-0 items-center gap-2">
                          <ObjectTypeChip type={event.object_type} />
                          {objectHasName ? (
                            <span className="min-w-0 truncate text-body-md text-text-primary">
                              {object}
                            </span>
                          ) : null}
                        </span>
                      </TD>
                    ) : null}
                    {cols.isVisible("activity") ? (
                      <TD className="w-1/2">
                        <span
                          className="block truncate text-body-sm text-text-secondary"
                          title={activity}
                        >
                          {activity}
                        </span>
                      </TD>
                    ) : null}
                    <TD className="tabular whitespace-nowrap text-body-sm text-text-subtle">
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
            {/* A failed *next* page must not wipe the rows already read, so it
                reports itself here rather than replacing the table. */}
            {failure ? (
              <p className="text-body-sm text-status-danger-text">
                {failure.message}
              </p>
            ) : (
              <p className="text-caption text-text-subtle">
                Showing <span className="tabular">{filtered.length}</span> of{" "}
                <span className="tabular">{events.length}</span> loaded events
              </p>
            )}
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

      {/* Row detail — a centered, responsive modal. */}
      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent className="max-h-[85vh] w-full max-w-2xl overflow-y-auto">
          {selected ? (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <span>{ACTION_META[selected.action].label}</span>
                  <ObjectTypeChip type={selected.object_type} />
                </DialogTitle>
                <DialogDescription>
                  {objectLabelOf(selected)} · by {actorLabelOf(selected)} ·{" "}
                  <span className="tabular">
                    {formatWhen(selected.occurred_at)}
                  </span>
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                {/* Plain-English summary of what happened. */}
                <div className="rounded-md border border-action-accent-border bg-action-accent-tint px-3.5 py-2.5">
                  <p className="text-body-md text-text-primary">
                    {activityOf(selected)}
                  </p>
                </div>

                {/* What changed, field by field (updates only). */}
                {(() => {
                  const changes = changesOf(selected.before, selected.after);
                  if (changes.length === 0) return null;
                  return (
                    <div>
                      <p className="type-overline mb-1.5">Changes</p>
                      <div className="overflow-hidden rounded-md border border-border">
                        {changes.map((change) => (
                          <div
                            key={change.field}
                            className="flex items-center gap-2 border-b border-border px-3 py-2 text-body-sm last:border-0"
                          >
                            <span className="w-28 shrink-0 truncate font-medium capitalize text-text-secondary">
                              {change.field}
                            </span>
                            <span className="min-w-0 flex-1 truncate text-text-subtle line-through">
                              {change.from}
                            </span>
                            <Icon
                              name="arrowr"
                              className="size-3.5 shrink-0 text-text-subtle"
                            />
                            <span className="min-w-0 flex-1 truncate text-text-primary">
                              {change.to}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })()}

                <SnapshotBlock
                  label="Before"
                  value={selected.before}
                  emptyNote="No prior state. The object was created by this event."
                />
                <SnapshotBlock
                  label="After"
                  value={selected.after}
                  emptyNote="No resulting state. The object was removed by this event."
                />
                <div>
                  <p className="type-overline mb-1.5">Event</p>
                  <dl className="space-y-1 text-body-sm">
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">User</dt>
                      <dd className="truncate text-text-primary">
                        {actorLabelOf(selected)}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">User type</dt>
                      <dd className="text-text-secondary">
                        {ACTOR_TYPE_LABEL[selected.actor_type]}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Object</dt>
                      <dd className="truncate text-text-primary">
                        {objectLabelOf(selected)}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Status</dt>
                      <dd className="text-status-success-text">
                        Committed
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">When</dt>
                      <dd className="tabular text-text-secondary">
                        {formatWhen(selected.occurred_at)}
                      </dd>
                    </div>
                    <div className="flex justify-between gap-4">
                      <dt className="text-text-subtle">Event id</dt>
                      <dd className="tabular truncate font-mono text-text-secondary">
                        {selected.id}
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
              </div>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
