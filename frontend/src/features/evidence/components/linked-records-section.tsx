import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  TextField,
  useToast,
  type IconName,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import { evidenceApi } from "@/lib/api/endpoints";
import type { LinkedRecord, LinkTargetType } from "@/lib/api/types";
import { listTasks } from "@/features/tasks/api";
import { listAssets } from "@/features/assets/api";
import { listDocuments } from "@/features/documents/api";
import { listVulnerabilities } from "@/features/vulnerabilities/api";

const humanStatus = (s: string) => s.replace(/_/g, " ");

/** One option per module evidence can be linked to. `search` returns the
 *  picker's candidates; the shape is deliberately the same for all four so the
 *  dialog below stays one component rather than four near-identical ones. */
type Candidate = { id: string; code: string; title: string; status: string };

type TargetConfig = {
  type: LinkTargetType;
  label: string;
  plural: string;
  icon: IconName;
  href: (id: string) => string;
  search: (query: string) => Promise<Candidate[]>;
};

const TARGETS: TargetConfig[] = [
  {
    type: "task",
    label: "Task",
    plural: "Tasks",
    icon: "check",
    href: (id) => `/tasks/${id}`,
    search: async (q) => {
      const page = await listTasks({ search: q }, 1, 25);
      return page.items.map((t) => ({ id: t.id, code: t.code, title: t.title, status: t.status }));
    },
  },
  {
    type: "document",
    label: "Document",
    plural: "Documents",
    icon: "doc",
    href: (id) => `/documents/${id}`,
    search: async (q) => {
      const all = await listDocuments();
      const needle = q.trim().toLowerCase();
      return all
        .filter(
          (d) =>
            !needle ||
            d.title.toLowerCase().includes(needle) ||
            d.code.toLowerCase().includes(needle),
        )
        .slice(0, 25)
        .map((d) => ({ id: d.id, code: d.code, title: d.title, status: d.lifecycle }));
    },
  },
  {
    type: "asset",
    label: "Asset",
    plural: "Assets",
    icon: "server",
    href: (id) => `/assets/${id}`,
    search: async (q) => {
      const page = await listAssets({ search: q }, 1, 25);
      return page.items.map((a) => ({
        id: a.id,
        code: a.hostname ?? "",
        title: a.name,
        status: a.status,
      }));
    },
  },
  {
    type: "vulnerability",
    label: "Vulnerability",
    plural: "Vulnerabilities",
    icon: "bug",
    href: (id) => `/vulnerabilities/${id}`,
    search: async (q) => {
      const rows = await listVulnerabilities({ search: q });
      return rows.slice(0, 25).map((v) => ({
        id: v.id,
        code: v.cve_id ?? "",
        title: v.title,
        status: v.state,
      }));
    },
  },
];

const CONFIG = new Map(TARGETS.map((t) => [t.type, t]));

/**
 * Everything this evidence is linked to, across every module.
 *
 * Links are the platform's `links` primitive, so the same edge shows on the
 * other record too. Linking, not copying: each record stays owned by its own
 * module, and the row here is resolved through that module's service.
 */
export function LinkedRecordsSection({
  evidenceId,
  canManage,
}: {
  evidenceId: string;
  canManage: boolean;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const key = ["evidence-links", evidenceId];
  const [picking, setPicking] = useState<LinkTargetType | null>(null);
  const [filter, setFilter] = useState<LinkTargetType | "all">("all");

  const linksQuery = useQuery({ queryKey: key, queryFn: () => evidenceApi.links(evidenceId) });
  const unlink = useMutation({
    mutationFn: (linkId: string) => evidenceApi.unlink(evidenceId, linkId),
    onSuccess: (rows) => queryClient.setQueryData(key, rows),
    onError: (error: unknown) => toast({ title: errorToast(error, "link"), tone: "danger" }),
  });

  const rows = useMemo(() => linksQuery.data ?? [], [linksQuery.data]);
  const counts = useMemo(() => {
    const out = new Map<LinkTargetType, number>();
    for (const row of rows) out.set(row.target_type, (out.get(row.target_type) ?? 0) + 1);
    return out;
  }, [rows]);
  const shown = filter === "all" ? rows : rows.filter((r) => r.target_type === filter);

  // A panel inside a working page: one quiet line, not a full ErrorState.
  const loadFailure = linksQuery.isError ? describeError(linksQuery.error, "linked records") : null;

  return (
    <div className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          Linked records
          {loadFailure ? null : (
            <span className="ml-2 tabular text-body-sm text-text-subtle">{rows.length}</span>
          )}
        </h2>
        {canManage ? (
          <div className="flex flex-wrap gap-1.5">
            {TARGETS.map((t) => (
              <Button key={t.type} size="sm" variant="secondary" onClick={() => setPicking(t.type)}>
                <Icon name={t.icon} className="size-4" />
                Link {t.label.toLowerCase()}
              </Button>
            ))}
          </div>
        ) : null}
      </div>

      {rows.length > 0 ? (
        <div className="mb-3 flex flex-wrap gap-1.5">
          <FilterPill active={filter === "all"} onClick={() => setFilter("all")} count={rows.length}>
            All
          </FilterPill>
          {TARGETS.filter((t) => counts.get(t.type)).map((t) => (
            <FilterPill
              key={t.type}
              active={filter === t.type}
              onClick={() => setFilter(t.type)}
              count={counts.get(t.type) ?? 0}
            >
              {t.plural}
            </FilterPill>
          ))}
        </div>
      ) : null}

      {loadFailure ? (
        // A failed load is not "nothing linked": saying so would be a lie.
        <p className="text-body-sm text-status-danger-text">{loadFailure.message}</p>
      ) : rows.length === 0 ? (
        <p className="text-body-sm text-text-subtle">
          Nothing linked yet. Link the control work, policy, asset or finding this evidence supports
          and the same link shows on that record too.
        </p>
      ) : (
        <ul className="space-y-1.5">
          {shown.map((row) => (
            <LinkedRow
              key={row.link_id}
              row={row}
              canManage={canManage}
              onUnlink={() => unlink.mutate(row.link_id)}
            />
          ))}
        </ul>
      )}

      {picking ? (
        <LinkPickerDialog
          evidenceId={evidenceId}
          target={CONFIG.get(picking)!}
          linkedIds={rows.filter((r) => r.target_type === picking).map((r) => r.target_id)}
          onOpenChange={(open) => setPicking(open ? picking : null)}
          onLinked={(next) => queryClient.setQueryData(key, next)}
        />
      ) : null}
    </div>
  );
}

function FilterPill({
  active,
  count,
  onClick,
  children,
}: {
  active: boolean;
  count: number;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border px-2.5 py-1 text-caption transition-colors",
        active
          ? "border-action-primary-bg bg-action-primary-bg text-action-primary-fg"
          : "border-border text-text-secondary hover:bg-surface-hover",
      )}
    >
      {children}
      <span className="ml-1.5 tabular opacity-70">{count}</span>
    </button>
  );
}

function LinkedRow({
  row,
  canManage,
  onUnlink,
}: {
  row: LinkedRecord;
  canManage: boolean;
  onUnlink: () => void;
}) {
  const config = CONFIG.get(row.target_type);
  return (
    <li className="flex items-center gap-2.5 rounded-sm border border-border px-3 py-2">
      <Icon
        name={config?.icon ?? "link"}
        className="size-4 shrink-0 text-text-subtle"
        aria-label={config?.label ?? row.target_type}
      />
      <Link to={config ? config.href(row.target_id) : "#"} className="min-w-0 flex-1 truncate">
        {row.code ? (
          <span className="mr-2 font-mono text-caption text-text-subtle">{row.code}</span>
        ) : null}
        <span className="text-body-sm text-text-primary">{row.title}</span>
      </Link>
      {row.detail ? (
        <span className="hidden text-caption text-text-subtle sm:inline">
          {humanStatus(row.detail)}
        </span>
      ) : null}
      <Badge variant="neutral">{humanStatus(row.status)}</Badge>
      {canManage ? (
        <button
          type="button"
          aria-label={`Unlink ${row.title}`}
          onClick={onUnlink}
          className="text-text-subtle transition-colors hover:text-status-danger-text"
        >
          <Icon name="x" className="size-4" />
        </button>
      ) : null}
    </li>
  );
}

function LinkPickerDialog({
  evidenceId,
  target,
  linkedIds,
  onOpenChange,
  onLinked,
}: {
  evidenceId: string;
  target: TargetConfig;
  linkedIds: string[];
  onOpenChange: (open: boolean) => void;
  onLinked: (rows: LinkedRecord[]) => void;
}) {
  const { toast } = useToast();
  const [search, setSearch] = useState("");

  const results = useQuery({
    queryKey: ["evidence-link-picker", target.type, search],
    queryFn: () => target.search(search),
  });
  const link = useMutation({
    mutationFn: (id: string) => evidenceApi.link(evidenceId, target.type, id),
    onSuccess: (rows) => {
      onLinked(rows);
      toast({ title: `${target.label} linked`, tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, target.label.toLowerCase()), tone: "danger" }),
  });

  const items = (results.data ?? []).filter((c) => !linkedIds.includes(c.id));
  const searchFailure = results.isError
    ? describeError(results.error, `${target.label.toLowerCase()} list`)
    : null;

  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Link a {target.label.toLowerCase()}</DialogTitle>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <TextField
            label={`Search ${target.plural.toLowerCase()}`}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="By title or code…"
          />
          <div className="max-h-80 overflow-y-auto rounded-md border border-border">
            {searchFailure ? (
              // "No matches" for a failed search would send the reader looking
              // for a record that is there.
              <p className="p-4 text-body-sm text-status-danger-text">{searchFailure.message}</p>
            ) : items.length === 0 ? (
              <p className="p-4 text-body-sm text-text-subtle">
                {results.isLoading
                  ? "Loading…"
                  : "No matches — everything found may already be linked."}
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {items.map((c) => (
                  <li key={c.id}>
                    <button
                      type="button"
                      disabled={link.isPending}
                      onClick={() => link.mutate(c.id)}
                      className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-surface-hover disabled:opacity-60"
                    >
                      <span className="min-w-0 flex-1 truncate">
                        {c.code ? (
                          <span className="mr-2 font-mono text-caption text-text-subtle">
                            {c.code}
                          </span>
                        ) : null}
                        <span className="text-body-sm text-text-primary">{c.title}</span>
                      </span>
                      <Badge variant="neutral">{humanStatus(c.status)}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
