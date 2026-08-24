import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  ConfirmDialog,
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  EmptyState,
  FilterFacet,
  Icon,
  Pagination,
  SearchInput,
  StatusPill,
  Table,
  TableSkeleton,
  TBody,
  TD,
  TH,
  THead,
  TR,
  useToast,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { cn } from "@/lib/cn";
import {
  archiveDocument,
  downloadDocumentBlob,
  listDocuments,
} from "@/features/documents/api";
import {
  CLASSIFICATIONS,
  DOC_TYPES,
  type Classification,
  type Document,
  type DocType,
  type Lifecycle,
} from "@/features/documents/types";
import { DocumentFormDialog } from "./document-form-dialog";

const TYPE_LABEL: Record<DocType, string> = {
  policy: "Policy",
  standard: "Standard",
  procedure: "Procedure",
  guideline: "Guideline",
  charter: "Charter",
};

const CLASS_LABEL: Record<Classification, string> = {
  public: "Public",
  internal: "Internal",
  confidential: "Confidential",
  restricted: "Restricted",
};

/** Lifecycle → pill family + label. */
const LIFECYCLE_META: Record<Lifecycle, { label: string; family: StatusFamily }> = {
  draft: { label: "Draft", family: "neutral" },
  needs_approval: { label: "Needs approval", family: "pending" },
  approved: { label: "Approved", family: "progress" },
  published: { label: "Published", family: "success" },
  expired: { label: "Expired", family: "danger" },
  archived: { label: "Archived", family: "neutral" },
};

const LIFECYCLE_FILTERS: { value: Lifecycle; label: string }[] = [
  { value: "draft", label: "Draft" },
  { value: "needs_approval", label: "Needs approval" },
  { value: "approved", label: "Approved" },
  { value: "published", label: "Published" },
  { value: "expired", label: "Expired" },
];

const TOGGLEABLE_COLUMNS = [
  { key: "version", label: "Version" },
  { key: "owner", label: "Owner" },
  { key: "lifecycle", label: "Status" },
  { key: "renewal", label: "Next review" },
  { key: "attestation", label: "Acknowledged" },
  { key: "type", label: "Type" },
  { key: "classification", label: "Classification" },
  { key: "frameworks", label: "Frameworks" },
  { key: "description", label: "Description" },
] as const;
type ColKey = (typeof TOGGLEABLE_COLUMNS)[number]["key"];

// Default columns mirror the Figma register: Version, Owner, Status, Next
// review, Acknowledged. Type/Classification/Frameworks/Description are opt-in.
const DEFAULT_HIDDEN: ColKey[] = ["type", "classification", "frameworks", "description"];
const COLUMN_PREFS_KEY = "verity.documents.columns";

function loadColumnPrefs(): Record<ColKey, boolean> {
  const all = Object.fromEntries(
    TOGGLEABLE_COLUMNS.map((c) => [c.key, !DEFAULT_HIDDEN.includes(c.key)]),
  ) as Record<ColKey, boolean>;
  try {
    const raw = localStorage.getItem(COLUMN_PREFS_KEY);
    if (!raw) return all;
    const saved = JSON.parse(raw) as Partial<Record<ColKey, boolean>>;
    for (const { key } of TOGGLEABLE_COLUMNS) {
      if (typeof saved[key] === "boolean") all[key] = saved[key] as boolean;
    }
  } catch {
    // Corrupt/absent pref falls back to defaults — never fail the page over it.
  }
  return all;
}

const PAGE_SIZE = 12;

function isOverdue(doc: Document): boolean {
  return (
    doc.renewal_date != null &&
    doc.lifecycle !== "archived" &&
    new Date(doc.renewal_date) <= new Date()
  );
}

/** The status shown in the register — a published document past its renewal
 *  date reads as "Needs renewal" (Figma), not "Published". */
function displayStatus(doc: Document): { family: StatusFamily; label: string } {
  if (doc.lifecycle === "published" && isOverdue(doc)) {
    return { family: "danger", label: "Needs renewal" };
  }
  const meta = LIFECYCLE_META[doc.lifecycle];
  return { family: meta.family, label: meta.label };
}

function fmtDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "2-digit",
  });
}


export function DocumentsRegisterPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [scope, setScope] = useState<"active" | "archived">("active");
  const [search, setSearch] = useState("");
  const [types, setTypes] = useState<string[]>([]);
  const [statuses, setStatuses] = useState<string[]>([]);
  const [owners, setOwners] = useState<string[]>([]);
  const [classes, setClasses] = useState<string[]>([]);
  const [page, setPage] = useState(1);

  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Document | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<Document | null>(null);

  const [visibleCols, setVisibleCols] = useState<Record<ColKey, boolean>>(
    loadColumnPrefs,
  );
  useEffect(() => {
    localStorage.setItem(COLUMN_PREFS_KEY, JSON.stringify(visibleCols));
  }, [visibleCols]);
  const hiddenColCount = TOGGLEABLE_COLUMNS.filter((c) => !visibleCols[c.key]).length;

  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const documents = useMemo(() => documentsQuery.data ?? [], [documentsQuery.data]);

  const ownerOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const doc of documents) {
      if (doc.owner) seen.set(doc.owner.membership_id, doc.owner.name);
    }
    return [...seen.entries()].map(([value, label]) => ({ value, label }));
  }, [documents]);

  const scoped = useMemo(
    () =>
      documents.filter((d) =>
        scope === "archived" ? d.lifecycle === "archived" : d.lifecycle !== "archived",
      ),
    [documents, scope],
  );

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return scoped.filter(
      (d) =>
        (types.length === 0 || types.includes(d.doc_type)) &&
        (statuses.length === 0 || statuses.includes(d.lifecycle)) &&
        (classes.length === 0 || classes.includes(d.classification)) &&
        (owners.length === 0 ||
          (d.owner != null && owners.includes(d.owner.membership_id))) &&
        (q === "" ||
          d.title.toLowerCase().includes(q) ||
          d.code.toLowerCase().includes(q) ||
          (d.owner?.name ?? "").toLowerCase().includes(q) ||
          d.controls.some((c) => c.toLowerCase().includes(q))),
    );
  }, [scoped, search, types, statuses, classes, owners]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paged = visible.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => {
    if (page > pageCount) setPage(1);
  }, [page, pageCount]);

  const activeFilters =
    types.length + statuses.length + owners.length + classes.length;
  function clearFilters() {
    setTypes([]);
    setStatuses([]);
    setOwners([]);
    setClasses([]);
    setSearch("");
  }

  async function downloadRow(doc: Document) {
    if (doc.content_format === "html") {
      toast({ title: "This document is authored in-app; open it to view.", tone: "neutral" });
      return;
    }
    try {
      const blob = await downloadDocumentBlob(doc.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.filename ?? "document";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast({ title: "Download failed", tone: "danger" });
    }
  }

  const archiveMutation = useMutation({
    mutationFn: (id: string) => archiveDocument(id, "Archived from the register"),
    onSuccess: () => {
      toast({ title: "Document archived", tone: "neutral" });
      setArchiveTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
  });


  const overdue = documents.filter(isOverdue);
  const inReview = documents.filter((d) => d.lifecycle === "needs_approval").length;
  const withAck = documents.filter((d) => d.attestation_pct != null);
  const orgAck =
    withAck.length > 0
      ? Math.round(
          withAck.reduce((sum, d) => sum + (d.attestation_pct ?? 0), 0) / withAck.length,
        )
      : null;

  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="type-overline text-text-subtle">Compliance</p>
          <h1 className="mt-1 font-display text-heading-lg text-text-primary">
            Policies &amp; documents
          </h1>
          <p className="mt-1.5 text-body-lg text-text-secondary">
            <span className="tabular">{scoped.length}</span>{" "}
            {scope === "archived" ? "archived " : ""}
            {scoped.length === 1 ? "document" : "documents"}
            {overdue.length > 0 ? (
              <>
                {" · "}
                <span className="font-semibold text-status-danger-text">
                  {overdue.length} need renewal
                </span>
              </>
            ) : null}
            {inReview > 0 ? <> · {inReview} in review</> : null}
            {orgAck != null ? <> · org-wide acknowledgement {orgAck}%</> : null}
          </p>
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="secondary">
                <Icon name="layers" className="size-4" />
                Columns
                {hiddenColCount > 0 ? (
                  <span className="tabular text-caption text-text-subtle">
                    {TOGGLEABLE_COLUMNS.length - hiddenColCount}/
                    {TOGGLEABLE_COLUMNS.length}
                  </span>
                ) : null}
                <Icon name="chev" className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {TOGGLEABLE_COLUMNS.map((col) => (
                <DropdownMenuCheckboxItem
                  key={col.key}
                  checked={visibleCols[col.key]}
                  onCheckedChange={(next) =>
                    setVisibleCols((prev) => ({ ...prev, [col.key]: next }))
                  }
                >
                  {col.label}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button onClick={() => setCreating(true)}>
            <Icon name="plus" className="size-4" />
            New document
          </Button>
        </div>
      </div>

      {/* Overdue-renewal alert (Figma): surfaces the most urgent item. */}
      {scope === "active" && overdue.length > 0 ? (
        <div className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-status-warning-border bg-status-warning-bg px-4 py-3">
          <div className="flex items-center gap-3">
            <Icon name="clock" className="size-5 shrink-0 text-status-warning-text" />
            <div className="min-w-0">
              <p className="text-body-md font-medium text-text-primary">
                {overdue[0].title} renewal is overdue
              </p>
              <p className="text-caption text-text-subtle">
                Review was due {fmtDate(overdue[0].renewal_date)}
                {overdue[0].frameworks.length
                  ? ` · required for ${overdue[0].frameworks.join(", ")}`
                  : ""}
              </p>
            </div>
          </div>
          <Button
            variant="secondary"
            className="shrink-0"
            onClick={() => navigate(`/documents/${overdue[0].id}`)}
          >
            Start review
          </Button>
        </div>
      ) : null}

      {/* Active / Archived tabs */}
      <div className="mt-5 flex items-center gap-1 border-b border-border">
        {(["active", "archived"] as const).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => {
              setScope(s);
              setPage(1);
            }}
            className={cn(
              "relative px-3 py-2 text-label-sm capitalize",
              scope === s ? "text-text-primary" : "text-text-subtle hover:text-text-secondary",
            )}
          >
            {s}
            {scope === s ? (
              <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" />
            ) : null}
          </button>
        ))}
      </div>

      {/* Search · filters */}
      <div className="mt-4 flex flex-wrap items-center gap-2">
        <div className="min-w-[240px] flex-1">
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by title, code, owner or control…"
          />
        </div>
        <FilterFacet
          label="Type"
          options={DOC_TYPES.map((t) => ({ value: t, label: TYPE_LABEL[t] }))}
          values={types}
          onChange={setTypes}
        />
        <FilterFacet
          label="Status"
          options={LIFECYCLE_FILTERS}
          values={statuses}
          onChange={setStatuses}
        />
        <FilterFacet
          label="Classification"
          options={CLASSIFICATIONS.map((c) => ({ value: c, label: CLASS_LABEL[c] }))}
          values={classes}
          onChange={setClasses}
        />
        <FilterFacet label="Owner" options={ownerOptions} values={owners} onChange={setOwners} />
        {activeFilters > 0 ? (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            Clear
          </Button>
        ) : null}
      </div>

      <p aria-live="polite" className="mb-3 mt-3 text-caption text-text-subtle">
        Showing <span className="tabular">{visible.length}</span> of{" "}
        <span className="tabular">{scoped.length}</span> documents
      </p>

      {documentsQuery.isLoading ? (
        <TableSkeleton rows={8} density="comfortable" />
      ) : visible.length === 0 ? (
        <EmptyState
          icon="book"
          title={scope === "archived" ? "No archived documents" : "No documents match"}
          description={
            scope === "archived"
              ? "Archived policies and documents will appear here."
              : "Adjust the filters, or create a new document to get started."
          }
          action={
            scope === "active" ? (
              <Button onClick={() => setCreating(true)}>
                <Icon name="plus" className="size-4" />
                New document
              </Button>
            ) : undefined
          }
        />
      ) : (
        <Table>
          <THead>
            <TR>
              <TH>Policy</TH>
              {visibleCols.version ? <TH>Version</TH> : null}
              {visibleCols.owner ? <TH>Owner</TH> : null}
              {visibleCols.lifecycle ? <TH>Status</TH> : null}
              {visibleCols.renewal ? <TH>Next review</TH> : null}
              {visibleCols.attestation ? <TH>Acknowledged</TH> : null}
              {visibleCols.type ? <TH>Type</TH> : null}
              {visibleCols.classification ? <TH>Classification</TH> : null}
              {visibleCols.frameworks ? <TH>Frameworks</TH> : null}
              {visibleCols.description ? <TH>Description</TH> : null}
              <TH className="w-12 text-right">
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {paged.map((doc) => {
              const status = displayStatus(doc);
              const overdueRow = isOverdue(doc);
              const pct = doc.attestation_pct;
              const ackColor =
                pct == null
                  ? ""
                  : pct >= 90
                    ? "bg-status-success-base"
                    : pct >= 75
                      ? "bg-status-warning-base"
                      : "bg-status-danger-base";
              return (
                <TR
                  key={doc.id}
                  onClick={() => navigate(`/documents/${doc.id}`)}
                  className="cursor-pointer"
                >
                  <TD>
                    <div className="flex max-w-[340px] items-center gap-2.5">
                      <Icon name="doc" className="size-4 shrink-0 text-text-subtle" />
                      <div className="min-w-0">
                        <span className="block truncate text-body-md font-medium text-text-primary">
                          {doc.title}
                        </span>
                        <span className="font-mono text-caption text-text-subtle">
                          {doc.code}
                        </span>
                      </div>
                    </div>
                  </TD>
                  {visibleCols.version ? (
                    <TD>
                      <span className="tabular text-body-sm text-text-secondary">
                        {doc.version}
                      </span>
                    </TD>
                  ) : null}
                  {visibleCols.owner ? (
                    <TD>
                      {doc.owner ? (
                        <span className="flex items-center gap-2">
                          <Avatar name={doc.owner.name} size="sm" />
                          <span className="truncate text-body-sm text-text-secondary">
                            {doc.owner.name}
                          </span>
                        </span>
                      ) : (
                        <span className="text-body-sm text-text-subtle">Unassigned</span>
                      )}
                    </TD>
                  ) : null}
                  {visibleCols.lifecycle ? (
                    <TD>
                      <StatusPill status={status.family} label={status.label} />
                    </TD>
                  ) : null}
                  {visibleCols.renewal ? (
                    <TD>
                      {overdueRow ? (
                        <span className="text-body-sm font-medium text-status-danger-text">
                          Overdue
                        </span>
                      ) : (
                        <span className="text-body-sm text-text-secondary">
                          {fmtDate(doc.renewal_date)}
                        </span>
                      )}
                    </TD>
                  ) : null}
                  {visibleCols.attestation ? (
                    <TD>
                      {pct == null ? (
                        <span className="text-body-sm text-text-subtle">not published</span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <span className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-sunken">
                            <span
                              className={cn("block h-full rounded-full", ackColor)}
                              style={{ width: `${pct}%` }}
                            />
                          </span>
                          <span className="tabular text-body-sm text-text-secondary">{pct}%</span>
                        </span>
                      )}
                    </TD>
                  ) : null}
                  {visibleCols.type ? (
                    <TD>
                      <Badge variant="neutral">{TYPE_LABEL[doc.doc_type]}</Badge>
                    </TD>
                  ) : null}
                  {visibleCols.classification ? (
                    <TD>
                      <span className="text-body-sm text-text-secondary">
                        {CLASS_LABEL[doc.classification]}
                      </span>
                    </TD>
                  ) : null}
                  {visibleCols.frameworks ? (
                    <TD>
                      {doc.frameworks.length ? (
                        <div className="flex flex-wrap gap-1">
                          {doc.frameworks.map((f) => (
                            <span
                              key={f}
                              className="rounded-xs bg-surface-sunken px-1.5 py-0.5 text-caption font-medium text-text-secondary"
                            >
                              {f}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-text-subtle">—</span>
                      )}
                    </TD>
                  ) : null}
                  {visibleCols.description ? (
                    <TD>
                      <p
                        className="line-clamp-2 max-w-[320px] text-body-sm text-text-secondary"
                        title={doc.description}
                      >
                        {doc.description || (
                          <span className="text-text-subtle">No description</span>
                        )}
                      </p>
                    </TD>
                  ) : null}
                  <TD
                    className="text-right"
                    onClick={(event) => event.stopPropagation()}
                  >
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          aria-label={`Actions for ${doc.code}`}
                        >
                          <Icon name="more" className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onSelect={() => navigate(`/documents/${doc.id}`)}>
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => setEditing(doc)}>
                          Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem onSelect={() => void downloadRow(doc)}>
                          Download
                        </DropdownMenuItem>
                        {doc.lifecycle !== "archived" ? (
                          <DropdownMenuItem
                            variant="danger"
                            onSelect={() => setArchiveTarget(doc)}
                          >
                            Archive
                          </DropdownMenuItem>
                        ) : null}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TD>
                </TR>
              );
            })}
          </TBody>
        </Table>
      )}

      {pageCount > 1 ? (
        <div className="mt-4 flex justify-end">
          <Pagination page={page} pageCount={pageCount} onPageChange={setPage} />
        </div>
      ) : null}

      <DocumentFormDialog
        mode="create"
        open={creating}
        onOpenChange={setCreating}
      />
      <DocumentFormDialog
        mode="edit"
        document={editing}
        open={editing !== null}
        onOpenChange={(next) => {
          if (!next) setEditing(null);
        }}
      />
      <ConfirmDialog
        open={archiveTarget !== null}
        onOpenChange={(next) => {
          if (!next) setArchiveTarget(null);
        }}
        title={`Archive ${archiveTarget?.code ?? "document"}?`}
        consequence="Archived documents move out of the active register. You can still open them from the Archived tab; nothing is deleted."
        confirmLabel="Archive document"
        loading={archiveMutation.isPending}
        onConfirm={() => archiveTarget && archiveMutation.mutate(archiveTarget.id)}
      />
    </div>
  );
}
