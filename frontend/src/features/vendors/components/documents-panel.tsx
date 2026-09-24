import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  Select,
  SelectContent,
  SelectField,
  SelectItem,
  SelectTrigger,
  TextArea,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { errorToast } from "@/lib/api/describe-error";
import { addDocument, attachDocumentFile, updateDocument } from "../api";
import { DOC_TYPES, type VendorDetail, type VendorDocument } from "../types";
import { COLLECTION_STATUS_META, DOC_TYPE_LABEL, fmtCountdown, fmtDate } from "../tokens";
import { Panel } from "./panel";

/**
 * The paperwork a vendor owes, with the window each piece actually covers.
 *
 * A document row that shows only a title says nothing useful: an ISO
 * certificate that expired last month and one that runs another year look
 * identical. So every row leads with its coverage window and a countdown, and
 * the countdown is what decides the row's colour.
 */
export function DocumentsPanel({
  vendor,
  canManage,
  onApply,
}: {
  vendor: VendorDetail;
  canManage: boolean;
  onApply: (next: VendorDetail) => void;
}) {
  const [adding, setAdding] = useState(false);
  const [editing, setEditing] = useState<VendorDocument | null>(null);
  const documents = vendor.documents;
  const expiring = documents.filter(
    (d) => d.is_expired || (d.expires_in_days !== null && d.expires_in_days <= 60),
  );

  return (
    <>
      <Panel
        title="Documents"
        count={documents.length || undefined}
        description={
          expiring.length > 0
            ? `${expiring.length} ${expiring.length === 1 ? "document needs" : "documents need"} renewing.`
            : undefined
        }
        action={
          canManage ? (
            <Button variant="secondary" size="sm" onClick={() => setAdding(true)}>
              <Icon name="plus" className="size-4" />
              Add document
            </Button>
          ) : null
        }
      >
        {documents.length === 0 ? (
          <p className="text-body-sm text-text-subtle">
            No documents yet. Add each one as soon as you request it.
          </p>
        ) : (
          <ul className="divide-y divide-border">
            {documents.map((d) => (
              <DocumentRow
                key={d.id}
                document={d}
                canManage={canManage}
                vendorId={vendor.id}
                onApply={onApply}
                onEdit={() => setEditing(d)}
                sendTo={
                  (
                    vendor.contacts.find((c) => c.contact_type === "security" && c.email) ??
                    vendor.contacts.find((c) => c.email)
                  )?.email ?? ""
                }
              />
            ))}
          </ul>
        )}
      </Panel>

      <AddDocumentDialog
        key={editing?.id ?? "new"}
        open={adding || editing !== null}
        onOpenChange={(open) => {
          if (!open) {
            setAdding(false);
            setEditing(null);
          }
        }}
        vendorId={vendor.id}
        onAdded={onApply}
        vendor={vendor}
        document={editing}
      />
    </>
  );
}

function DocumentRow({
  document: d,
  canManage,
  sendTo,
  vendorId,
  onApply,
  onEdit,
}: {
  document: VendorDocument;
  canManage: boolean;
  /** The vendor contact a renewal request goes to, security first. */
  sendTo: string;
  vendorId: string;
  onApply: (next: VendorDetail) => void;
  onEdit: () => void;
}) {
  const { toast } = useToast();
  const upload = useMutation({
    mutationFn: (file: File) => attachDocumentFile(vendorId, d.id, file),
    onSuccess: (next) => {
      onApply(next);
      toast({ title: "File attached", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "document"), tone: "danger" }),
  });
  const status = COLLECTION_STATUS_META[d.collection_status] ?? {
    label: d.collection_status,
    family: "neutral" as const,
  };
  const soon = !d.is_expired && d.expires_in_days !== null && d.expires_in_days <= 60;

  return (
    <li className="flex flex-wrap items-start justify-between gap-3 py-3">
      <div className="min-w-0 flex-1">
        <p className="text-body-md font-semibold text-text-primary">{d.title}</p>
        <p className="mt-0.5 text-caption text-text-subtle">
          {DOC_TYPE_LABEL[d.doc_type] ?? d.doc_type}
          {d.issue_date || d.valid_until ? (
            <>
              {" · covers "}
              {fmtDate(d.issue_date)} to {fmtDate(d.valid_until)}
            </>
          ) : (
            " · no coverage dates"
          )}
          {d.reviewed_by_name ? ` · reviewed by ${d.reviewed_by_name}` : ""}
        </p>
        {d.review_notes ? (
          <p className="mt-1 text-body-sm text-text-secondary">{d.review_notes}</p>
        ) : null}
      </div>

      <div className="flex shrink-0 flex-col items-end gap-1.5">
        <StatusPill status={status.family} label={status.label} kind="inline" />
        {d.valid_until ? (
          <span
            className={cn(
              "tabular text-caption",
              d.is_expired
                ? "font-semibold text-status-danger-text"
                : soon
                  ? "font-semibold text-status-warning-text"
                  : "text-text-subtle",
            )}
          >
            {d.is_expired ? "Expired " : "Expires "}
            {fmtCountdown(d.expires_in_days)}
          </span>
        ) : null}
        {(d.is_expired || soon) && canManage ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              const subject = encodeURIComponent(`Renewal: ${d.title}`);
              const body = encodeURIComponent(
                `Our copy of ${d.title} ${d.is_expired ? "has expired" : `expires ${fmtCountdown(d.expires_in_days)}`}. Could you send the current version?`,
              );
              // The request goes to the vendor from the reader's own mail client,
              // addressed to their security contact where there is one.
              window.location.href = `mailto:${encodeURIComponent(sendTo)}?subject=${subject}&body=${body}`;
            }}
          >
            Request renewal
          </Button>
        ) : null}
        {canManage ? (
          <>
            <label
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-md border border-border px-2.5 py-1 text-label-sm text-text-secondary hover:bg-surface-hover"
              aria-busy={upload.isPending}
            >
              <Icon name="paperclip" className="size-3.5" />
              {upload.isPending ? "Attaching…" : d.evidence_id ? "Replace file" : "Attach file"}
              <input
                type="file"
                className="sr-only"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) upload.mutate(file);
                  e.target.value = "";
                }}
              />
            </label>
            <Button variant="ghost" size="icon-sm" aria-label={`Edit ${d.title}`} onClick={onEdit}>
              <Icon name="edit" className="size-4" />
            </Button>
          </>
        ) : null}
      </div>
    </li>
  );
}

function AddDocumentDialog({
  open,
  onOpenChange,
  vendorId,
  vendor,
  document: editing,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  vendorId: string;
  vendor: VendorDetail;
  /** Null adds a document; a document edits it, and can mark it reviewed. */
  document: VendorDocument | null;
  onAdded: (next: VendorDetail) => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(editing?.title ?? "");
  const [docType, setDocType] = useState<string>(editing?.doc_type ?? "soc_report");
  const [issueDate, setIssueDate] = useState(editing?.issue_date ?? "");
  const [validUntil, setValidUntil] = useState(editing?.valid_until ?? "");
  const [collectionStatus, setCollectionStatus] = useState(
    editing?.collection_status ?? "requested",
  );
  const [reviewNotes, setReviewNotes] = useState(editing?.review_notes ?? "");

  const add = useMutation<VendorDetail | VendorDocument>({
    mutationFn: () => {
      const body = {
        title: title.trim(),
        doc_type: docType,
        issue_date: issueDate || null,
        valid_until: validUntil || null,
        collection_status: collectionStatus,
      };
      return editing
        ? updateDocument(vendorId, editing.id, {
            ...body,
            review_notes: reviewNotes.trim() || null,
          })
        : addDocument(vendorId, body);
    },
    onSuccess: (created) => {
      // This route answers with the one row, not the whole vendor, so patch the
      // detail cache rather than refetching the lot.
      // Adding answers with the one row and editing with the whole vendor, so
      // patch the detail cache either way rather than refetching the lot.
      onAdded(
        "documents" in created
          ? (created as VendorDetail)
          : { ...vendor, documents: [...vendor.documents, created as VendorDocument] },
      );
      void queryClient.invalidateQueries({ queryKey: ["vendor", vendorId] });
      onOpenChange(false);
      if (!editing) setTitle("");
      toast({ title: editing ? "Document saved" : "Document added", tone: "success" });
    },
    onError: (e: unknown) => toast({ title: errorToast(e, "document"), tone: "danger" }),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="sm">
        <DialogHeader>
          <DialogTitle>{editing ? "Edit document" : "Add document"}</DialogTitle>
          <DialogDescription>
            Record what the vendor sent. The owner is reminded before it expires.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (title.trim()) add.mutate();
          }}
        >
          <DialogBody className="space-y-3.5">
            <TextField
              label="Title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="SOC 2 Type II FY2026"
              autoFocus
            />
            <div className="grid gap-3.5 sm:grid-cols-2">
              <SelectField label="Type">
                <Select value={docType} onValueChange={setDocType}>
                  <SelectTrigger aria-label="Document type" />
                  <SelectContent>
                    {DOC_TYPES.map((t) => (
                      <SelectItem key={t} value={t}>
                        {DOC_TYPE_LABEL[t]}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </SelectField>
              <SelectField label="Status">
                <Select value={collectionStatus} onValueChange={setCollectionStatus}>
                  <SelectTrigger aria-label="Collection status" />
                  <SelectContent>
                    <SelectItem value="requested">Requested</SelectItem>
                    <SelectItem value="received">Received</SelectItem>
                    <SelectItem value="reviewed">Reviewed</SelectItem>
                  </SelectContent>
                </Select>
              </SelectField>
            </div>
            <div className="grid gap-3.5 sm:grid-cols-2">
              <TextField
                label="Issued"
                optional
                type="date"
                value={issueDate}
                onChange={(e) => setIssueDate(e.target.value)}
              />
              <TextField
                label="Valid until"
                optional
                type="date"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
              />
            </div>
            {editing ? (
              <TextArea
                label="Review notes"
                optional
                hint="Stamped with your name when the status is Reviewed."
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                rows={3}
                maxLength={8000}
              />
            ) : null}
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={add.isPending} disabled={!title.trim()}>
              {editing ? "Save document" : "Add document"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
