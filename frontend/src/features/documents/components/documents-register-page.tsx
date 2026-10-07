import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Avatar,
  Badge,
  Button,
  ColumnPicker,
  ConfirmDialog,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  EmptyState,
  ErrorState,
  FilterFacet,
  Icon,
  PageHeader,
  Pagination,
  SearchInput,
  StatusPill,
  Table,
  TableSkeleton,
  TabStrip,
  TBody,
  TD,
  TH,
  THead,
  Toolbar,
  TR,
  useColumnPrefs,
  useTableSort,
  useToast,
  type ColumnDef,
} from "@/components/ui";
import type { StatusFamily } from "@/components/ui/status-pill";
import { cn } from "@/lib/cn";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  archiveDocument,
  downloadDocumentBlob,
  listDocuments,
} from "@/features/documents/api";
import {
  CLASSIFICATIONS,
  DOC_TYPES,
  type Document,
  type Lifecycle,
} from "@/features/documents/types";
import { TemplatePickerDialog } from "./template-picker-dialog";
import { DocumentFormDialog } from "./document-form-dialog";
import { ReviewDate } from "./review-date";
import { CLASS_LABEL, LIFECYCLE_META, TYPE_LABEL } from "../labels";
import { formatDay } from "../review";
import { useEntryState } from "@/lib/nav/entry-state";




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
] as const satisfies readonly ColumnDef<string>[];
type ColKey = (typeof TOGGLEABLE_COLUMNS)[number]["key"];

// Default columns mirror the Figma register: Version, Owner, Status, Next
// review, Acknowledged. Type/Classification/Frameworks/Description are opt-in.
const DEFAULT_HIDDEN: ColKey[] = ["type", "classification", "frameworks", "description"];
const COLUMN_PREFS_KEY = "verity.documents.columns";

const PAGE_SIZE = 12;

/** The server decides (and never flags a retired document), so this list, the detail
 *  page, the dashboard count and the owner's reminder agree. */
function isOverdue(doc: Document): boolean {
  return doc.review_status === "overdue";
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

type SortKey = "title" | "version" | "owner" | "lifecycle" | "renewal" | "attestation";

const SORT_ACCESSORS = {
  title: (d: Document) => d.title,
  version: (d: Document) => d.version,
  owner: (d: Document) => d.owner?.name ?? null,
  lifecycle: (d: Document) => displayStatus(d).label,
  // ISO dates sort correctly as strings, so no Date allocation per comparison.
  renewal: (d: Document) => d.renewal_date,
  attestation: (d: Document) => d.attestation_pct,
};


export function DocumentsRegisterPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [scope, setScope] = useEntryState<"active" | "archived">("documents.scope", "active");
  const [search, setSearch] = useEntryState("documents.search", "");
  const [types, setTypes] = useEntryState<string[]>("documents.types", []);
  const [statuses, setStatuses] = useEntryState<string[]>("documents.statuses", []);
  const [owners, setOwners] = useEntryState<string[]>("documents.owners", []);
  const [classes, setClasses] = useEntryState<string[]>("documents.classes", []);
  const [page, setPage] = useEntryState("documents.page", 1);

  const [creating, setCreating] = useState(false);
  const [pickingTemplate, setPickingTemplate] = useState(false);
  const [editing, setEditing] = useState<Document | null>(null);
  const [archiveTarget, setArchiveTarget] = useState<Document | null>(null);

  const cols = useColumnPrefs(COLUMN_PREFS_KEY, TOGGLEABLE_COLUMNS, DEFAULT_HIDDEN);

  const documentsQuery = useQuery({ queryKey: ["documents"], queryFn: listDocuments });
  const documents = useMemo(() => documentsQuery.data ?? [], [documentsQuery.data]);
  const loadFailure = documentsQuery.isError
    ? describeError(documentsQuery.error, "document register")
    : null;

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

  const { thProps, sortRows } = useTableSort<Document, SortKey>(null, SORT_ACCESSORS);
  const sorted = useMemo(() => sortRows(visible), [sortRows, visible]);

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paged = sorted.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  useEffect(() => {
    // Only once the list has arrived: before that there are no pages at all, and a
    // page remembered from the last visit would be thrown away.
    if (documentsQuery.isSuccess && page > pageCount) setPage(1);
  }, [documentsQuery.isSuccess, page, pageCount, setPage]);

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
    } catch (error) {
      toast({ title: errorToast(error, "document"), tone: "danger" });
    }
  }

  const archiveMutation = useMutation({
    mutationFn: (id: string) => archiveDocument(id, "Archived from the register"),
    onSuccess: () => {
      toast({ title: "Document archived", tone: "neutral" });
      setArchiveTarget(null);
      void queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });


  const overdue = documents.filter(isOverdue);
  const archivedCount = documents.filter((d) => d.lifecycle === "archived").length;
  const activeCount = documents.length - archivedCount;
  const inReview = documents.filter((d) => d.lifecycle === "needs_approval").length;
  // FilterFacet has no count prop, so the one number the deleted summary line
  // owned for this facet rides in the option label.
  const statusOptions = LIFECYCLE_FILTERS.map((option) =>
    option.value === "needs_approval" && inReview > 0
      ? { ...option, label: `${option.label} (${inReview})` }
      : option,
  );
  const withAck = documents.filter((d) => d.attestation_pct != null);
  const orgAck =
    withAck.length > 0
      ? Math.round(
          withAck.reduce((sum, d) => sum + (d.attestation_pct ?? 0), 0) / withAck.length,
        )
      : null;
  // Archived documents are out of all three counts; nothing while loading.
  const subtitle = documentsQuery.data
    ? [
        `${activeCount} ${activeCount === 1 ? "document" : "documents"}`,
        inReview ? `${inReview} awaiting approval` : null,
        overdue.length ? `${overdue.length} overdue` : null,
      ]
        .filter(Boolean)
        .join(" · ")
    : undefined;

  return (
    <div className="w-full">
      <PageHeader
        title="Policies & documents"
        icon="book"
        subtitle={subtitle}
        actions={
          <>
            {/* Templates first: starting from a written policy is the right
                default, and a blank page is the harder path. */}
            <Button variant="secondary" onClick={() => setPickingTemplate(true)}>
              <Icon name="book" className="size-4" />
              Templates
            </Button>
            <Button onClick={() => setCreating(true)}>
              <Icon name="plus" className="size-4" />
              New document
            </Button>
          </>
        }
      />

      {/* Overdue-renewal alert (Figma): leads with how many, then the worst. */}
      {scope === "active" && overdue.length > 0 ? (
        <div className="mt-5 flex items-center justify-between gap-3 rounded-lg border border-status-warning-border bg-status-warning-bg px-4 py-3">
          <div className="flex items-center gap-3">
            <Icon name="clock" className="size-5 shrink-0 text-status-warning-text" />
            <div className="min-w-0">
              <p className="text-body-md font-medium text-text-primary">
                {overdue.length === 1
                  ? "1 document needs renewal"
                  : `${overdue.length} documents need renewal`}
              </p>
              <p className="text-caption text-text-subtle">
                {overdue[0].title}, review was due{" "}
                {overdue[0].renewal_date ? formatDay(overdue[0].renewal_date) : "earlier"}
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

      <TabStrip
        label="Document scope"
        value={scope}
        onSelect={(id) => {
          setScope(id as "active" | "archived");
          setPage(1);
        }}
        items={[
          { id: "active", label: "Active", count: activeCount },
          { id: "archived", label: "Archived", count: archivedCount },
        ]}
        aside={
          orgAck != null ? (
            <>
              Org-wide acknowledgement{" "}
              <span className="tabular font-semibold text-text-secondary">{orgAck}%</span>
            </>
          ) : null
        }
      />

      <Toolbar
        searchLabel="Filter documents"
        search={
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder="Search by title, code, owner or control…"
            aria-label="Search documents"
          />
        }
        actions={
          <p aria-live="polite" className="text-caption text-text-subtle">
            Showing <span className="tabular">{visible.length}</span> of{" "}
            <span className="tabular">{scoped.length}</span> documents
          </p>
        }
      >
        <FilterFacet
          label="Type"
          options={DOC_TYPES.map((t) => ({ value: t, label: TYPE_LABEL[t] }))}
          values={types}
          onChange={setTypes}
        />
        <FilterFacet
          label="Status"
          options={statusOptions}
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
            Clear filters
          </Button>
        ) : null}
      </Toolbar>

      {documentsQuery.isLoading ? (
        <TableSkeleton rows={8} density="comfortable" />
      ) : loadFailure ? (
        <ErrorState
          title={loadFailure.title}
          description={loadFailure.message}
          referenceId={loadFailure.referenceId}
          onRetry={loadFailure.retryable ? () => void documentsQuery.refetch() : undefined}
        />
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
        <Table actions={<ColumnPicker {...cols} />}>
          <THead>
            <TR>
              <TH {...thProps("title")}>Policy</TH>
              {cols.isVisible("version") ? <TH {...thProps("version")}>Version</TH> : null}
              {cols.isVisible("owner") ? <TH {...thProps("owner")}>Owner</TH> : null}
              {cols.isVisible("lifecycle") ? <TH {...thProps("lifecycle")}>Status</TH> : null}
              {cols.isVisible("renewal") ? <TH {...thProps("renewal")}>Next review</TH> : null}
              {cols.isVisible("attestation") ? (
                <TH {...thProps("attestation")}>Acknowledged</TH>
              ) : null}
              {cols.isVisible("type") ? <TH>Type</TH> : null}
              {cols.isVisible("classification") ? <TH>Classification</TH> : null}
              {cols.isVisible("frameworks") ? <TH>Frameworks</TH> : null}
              {cols.isVisible("description") ? <TH>Description</TH> : null}
              <TH className="w-12">
                <span className="sr-only">Actions</span>
              </TH>
            </TR>
          </THead>
          <TBody>
            {paged.map((doc) => {
              const status = displayStatus(doc);
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
                      </div>
                    </div>
                  </TD>
                  {cols.isVisible("version") ? (
                    <TD>
                      <span className="tabular text-body-sm text-text-secondary">
                        {doc.version}
                      </span>
                    </TD>
                  ) : null}
                  {cols.isVisible("owner") ? (
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
                  {cols.isVisible("lifecycle") ? (
                    <TD>
                      <StatusPill status={status.family} label={status.label} />
                    </TD>
                  ) : null}
                  {cols.isVisible("renewal") ? (
                    <TD>
                      <ReviewDate doc={doc} />
                    </TD>
                  ) : null}
                  {cols.isVisible("attestation") ? (
                    <TD>
                      {pct == null ? (
                        <span className="text-body-sm text-text-subtle">No campaign</span>
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
                  {cols.isVisible("type") ? (
                    <TD>
                      <Badge variant="neutral">{TYPE_LABEL[doc.doc_type]}</Badge>
                    </TD>
                  ) : null}
                  {cols.isVisible("classification") ? (
                    <TD>
                      <span className="text-body-sm text-text-secondary">
                        {CLASS_LABEL[doc.classification]}
                      </span>
                    </TD>
                  ) : null}
                  {cols.isVisible("frameworks") ? (
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
                        <span className="text-text-subtle">None</span>
                      )}
                    </TD>
                  ) : null}
                  {cols.isVisible("description") ? (
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
                          aria-label={`Actions for ${doc.title}`}
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
      <TemplatePickerDialog open={pickingTemplate} onOpenChange={setPickingTemplate} />

    </div>
  );
}
