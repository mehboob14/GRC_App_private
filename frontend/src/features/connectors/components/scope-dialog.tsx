import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Checkbox,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  ErrorState,
  Icon,
  SearchInput,
  Skeleton,
  TextArea,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { cn } from "@/lib/cn";
import {
  connectorKeys,
  listConnectionResources,
  runConnection,
  setConnectionScope,
  type Connection,
  type ConnectionResource,
} from "../api";
import { refreshAutomation } from "../hooks";

/**
 * Choose which repositories the checks look at (AU-9).
 *
 * A SOC 2 engagement covers named systems, not everything a token can reach. This
 * is where a workspace says which: tick what is in scope, untick what is not, and
 * give one reason for what is left out. The reason is kept on each repository,
 * audited, and printed on the evidence, so an auditor reading a clean result knows
 * what it was clean over.
 */
export function ScopeDialog({
  connection,
  onClose,
}: {
  connection: Connection | null;
  onClose: () => void;
}) {
  const open = connection !== null;
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [checked, setChecked] = useState<Record<string, boolean>>({});
  const [reason, setReason] = useState("");

  const resources = useQuery({
    queryKey: connectorKeys.resources(connection?.id ?? ""),
    queryFn: () => listConnectionResources(connection!.id),
    enabled: open,
  });
  const rows = useMemo(() => resources.data ?? [], [resources.data]);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setReason("");
  }, [open]);

  // What each row is now, so the dialog only ever sends what actually changed.
  useEffect(() => {
    setChecked(Object.fromEntries(rows.map((r) => [r.external_id, r.scope === "in_scope"])));
  }, [rows]);

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return rows.filter((r) => !needle || r.name.toLowerCase().includes(needle));
  }, [rows, query]);

  const changes = rows.filter(
    (r) => !r.archived && checked[r.external_id] !== (r.scope === "in_scope"),
  );
  const leftOut = changes.filter((r) => checked[r.external_id] === false);
  const needsReason = leftOut.length > 0;
  const included = rows.filter((r) => checked[r.external_id]).length;

  const save = useMutation({
    mutationFn: async (andRun: boolean) => {
      await setConnectionScope(
        connection!.id,
        changes.map((r) => ({
          external_id: r.external_id,
          scope: checked[r.external_id] ? ("in_scope" as const) : ("excluded" as const),
        })),
        needsReason ? reason.trim() : null,
      );
      if (andRun) await runConnection(connection!.id);
      return andRun;
    },
    onSuccess: (andRun) => {
      void queryClient.invalidateQueries({ queryKey: connectorKeys.resources(connection!.id) });
      refreshAutomation(queryClient);
      void queryClient.invalidateQueries({ queryKey: ["compliance-dashboard"] });
      toast({
        title: andRun ? "Scope saved. Checking now" : "Scope saved",
        tone: "success",
      });
      onClose();
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "scope"), tone: "danger" }),
  });

  const setShown = (value: boolean) =>
    setChecked((current) => ({
      ...current,
      ...Object.fromEntries(shown.filter((r) => !r.archived).map((r) => [r.external_id, value])),
    }));

  return (
    <Dialog open={open} onOpenChange={(next) => (next ? undefined : onClose())}>
      <DialogContent size="xl" scrollBody className="max-h-[90vh] p-0">
        <DialogHeader className="border-b border-border px-6 pb-4 pt-5">
          <DialogTitle>Choose repositories</DialogTitle>
          <DialogDescription>
            Only ticked repositories are checked. {connection?.account_login} has{" "}
            {rows.length || connection?.scope?.listed || 0}.
          </DialogDescription>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex flex-wrap items-center gap-2 border-b border-border px-6 py-3">
            <div className="min-w-[14rem] flex-1">
              <SearchInput
                value={query}
                onChange={setQuery}
                placeholder="Search repositories"
                aria-label="Search repositories"
              />
            </div>
            <Button variant="secondary" size="sm" type="button" onClick={() => setShown(true)}>
              Tick all shown
            </Button>
            <Button variant="secondary" size="sm" type="button" onClick={() => setShown(false)}>
              Untick all shown
            </Button>
          </div>

          <DialogBody className="mx-0 min-h-[16rem] px-6 py-2">
            {resources.isPending ? (
              <div className="space-y-2 py-3">
                {Array.from({ length: 6 }, (_, i) => (
                  <Skeleton key={i} className="h-10 w-full rounded-md" />
                ))}
              </div>
            ) : resources.isError ? (
              <div className="py-6">
                <ErrorState
                  title={describeError(resources.error, "repositories").title}
                  description={describeError(resources.error, "repositories").message}
                  onRetry={() => void resources.refetch()}
                />
              </div>
            ) : shown.length === 0 ? (
              <div className="py-6">
                <EmptyState
                  icon="search"
                  title={rows.length === 0 ? "Nothing discovered yet" : "No match"}
                  description={
                    rows.length === 0
                      ? "Run the checks once and the repositories this token can see will be listed here."
                      : "Try a different search."
                  }
                />
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {shown.map((r) => (
                  <ResourceRow
                    key={r.external_id}
                    resource={r}
                    checked={checked[r.external_id] ?? false}
                    onChange={(value) => setChecked((c) => ({ ...c, [r.external_id]: value }))}
                  />
                ))}
              </ul>
            )}
          </DialogBody>

          <div className="space-y-3 border-t border-border bg-surface-sunken px-6 py-4">
            <p className="text-body-sm text-text-secondary">
              <span className="font-semibold text-text-primary">{included}</span> of {rows.length}{" "}
              checked
              {changes.length > 0 ? `, ${changes.length} changed` : ""}.
            </p>
            {needsReason ? (
              <TextArea
                label={`Why ${leftOut.length === 1 ? "is this repository" : `are these ${leftOut.length} repositories`} left out of the audit?`}
                rows={2}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Personal projects, not part of the audited system"
                hint="Kept on each repository, audited, and printed on the evidence."
              />
            ) : null}
          </div>
        </div>

        <DialogFooter className="mt-0 border-t border-border px-6 py-4">
          <Button variant="secondary" type="button" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="secondary"
            type="button"
            disabled={changes.length === 0 || (needsReason && !reason.trim())}
            loading={save.isPending && save.variables === false}
            onClick={() => save.mutate(false)}
          >
            Save
          </Button>
          <Button
            type="button"
            disabled={changes.length === 0 || (needsReason && !reason.trim())}
            loading={save.isPending && save.variables === true}
            onClick={() => save.mutate(true)}
          >
            <Icon name="activity" className="size-4" />
            Save and check now
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function ResourceRow({
  resource: r,
  checked,
  onChange,
}: {
  resource: ConnectionResource;
  checked: boolean;
  onChange: (value: boolean) => void;
}) {
  const note = r.archived
    ? "Archived, so nothing in it can change."
    : !checked && r.reason
      ? `${r.reason}${r.decided_by === "person" && r.decided_by_name ? ` Left out by ${r.decided_by_name}.` : ""}`
      : null;
  return (
    <li className="flex items-center gap-3 py-2.5">
      <Checkbox
        checked={checked}
        disabled={r.archived}
        onCheckedChange={(v) => onChange(v === true)}
        aria-label={r.name}
      />
      <div className="min-w-0 flex-1">
        <p
          className={cn(
            "truncate text-body-md",
            checked ? "font-semibold text-text-primary" : "text-text-secondary",
          )}
        >
          {r.name}
        </p>
        {note ? <p className="truncate text-caption text-text-subtle">{note}</p> : null}
      </div>
      <div className="hidden shrink-0 items-center gap-1.5 sm:flex">
        <Badge variant="neutral">{r.private ? "Private" : "Public"}</Badge>
        {r.fork ? <Badge variant="neutral">Fork</Badge> : null}
        {r.empty ? <Badge variant="neutral">Empty</Badge> : null}
        {r.archived ? <Badge variant="neutral">Archived</Badge> : null}
      </div>
      {r.url ? (
        <a
          href={r.url}
          target="_blank"
          rel="noreferrer"
          aria-label={`Open ${r.name}`}
          className="shrink-0 rounded-sm p-1 text-text-subtle hover:text-action-accent"
        >
          <Icon name="export" className="size-4" />
        </a>
      ) : null}
    </li>
  );
}
