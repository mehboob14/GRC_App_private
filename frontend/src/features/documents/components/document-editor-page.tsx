import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import DOMPurify from "dompurify";
import mammoth from "mammoth";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  ErrorState,
  Icon,
  SegmentedControl,
  StatusPill,
  TextField,
  useToast,
} from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  downloadDocumentBlob,
  getDocumentDetail,
  saveDocumentContent,
} from "@/features/documents/api";
import type { ChangeType } from "@/features/documents/types";
import { LIFECYCLE_META } from "../labels";
import { companyNameList } from "../placeholder-marks";
import { useAuth } from "@/lib/auth/auth-context";
import { RichTextEditor } from "./rich-text-editor";

/**
 * Full-screen policy editor, opened in its own tab from the Content tab. Renders
 * outside the app shell (ADR-0012): just the document and the editor.
 */
export function DocumentEditorPage() {
  const { documentId } = useParams();
  const { toast } = useToast();
  const { principal } = useAuth();
  const [html, setHtml] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);
  // A failed Word conversion must not open an empty editor over a real policy:
  // saving that would replace the content with nothing.
  const [convertError, setConvertError] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["documents", documentId],
    queryFn: () => getDocumentDetail(documentId!),
    enabled: Boolean(documentId),
  });
  const doc = query.data;

  // Load the editable content once. Authored docs use their HTML; a Word file is
  // parsed to HTML here (in this tab) via mammoth — that's the "parse only on
  // edit" step. PDFs cannot become editable rich text.
  useEffect(() => {
    if (!doc || html !== null) return;
    if (doc.content_format === "html") {
      setHtml(doc.content_html ?? "");
    } else if (doc.content_format === "docx") {
      downloadDocumentBlob(doc.id)
        .then(async (blob) => {
          const { value } = await mammoth.convertToHtml({
            arrayBuffer: await blob.arrayBuffer(),
          });
          setHtml(DOMPurify.sanitize(value) || "<p></p>");
        })
        .catch((error: unknown) =>
          setConvertError(describeError(error, "document").message),
        );
    }
  }, [doc, html]);

  const saveMutation = useMutation({
    mutationFn: ({ summary, changeType }: { summary: string; changeType: ChangeType }) =>
      saveDocumentContent(documentId!, html ?? "", changeType, summary || undefined),
    onSuccess: () => {
      setDirty(false);
      setSaving(false);
      setSummary("");
      toast({ title: "Content saved as a new version", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

  const [saving, setSaving] = useState(false);
  const [summary, setSummary] = useState("");
  const [changeType, setChangeType] = useState<ChangeType>("minor");

  // Warn before leaving with unsaved edits.
  useEffect(() => {
    const handler = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  if (query.isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-body-md text-text-subtle">
        Loading editor…
      </div>
    );
  }
  if (query.isError) {
    const e = describeError(query.error, "document");
    return (
      <div className="flex h-screen items-center justify-center p-6">
        <ErrorState
          className="max-w-lg"
          title={e.title}
          description={e.message}
          referenceId={e.referenceId}
          onRetry={e.retryable ? () => void query.refetch() : undefined}
        />
      </div>
    );
  }
  if (!doc) {
    return (
      <div className="flex h-screen items-center justify-center text-body-md text-text-secondary">
        Document not found.
      </div>
    );
  }
  if (doc.content_format === "pdf") {
    return (
      <div className="mx-auto mt-24 max-w-md text-center">
        <p className="text-body-md text-text-primary">PDFs can't be edited as rich text.</p>
        <p className="mt-1 text-body-sm text-text-secondary">
          Upload a new version to replace this file, or download it to edit externally.
        </p>
        <Button className="mt-4" variant="secondary" onClick={() => window.close()}>
          Close
        </Button>
      </div>
    );
  }
  if (convertError !== null) {
    return (
      <div className="flex h-screen items-center justify-center p-6">
        <ErrorState
          className="max-w-lg"
          title="This document could not be opened for editing"
          description={convertError}
        />
      </div>
    );
  }
  if (html === null) {
    return (
      <div className="flex h-screen items-center justify-center text-body-md text-text-subtle">
        {doc.content_format === "docx" ? "Converting document…" : "Loading editor…"}
      </div>
    );
  }

  const life = LIFECYCLE_META[doc.lifecycle];
  const placeholderLabels = Object.fromEntries(doc.placeholders.map((p) => [p.key, p.label]));
  const companyNames = companyNameList(doc.company_name, principal?.tenant_name);

  return (
    <div className="flex h-screen flex-col bg-surface-page">
      <header className="flex h-16 shrink-0 items-center gap-3 border-b border-border bg-surface-primary px-5">
        <span className="grid size-10 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
          <Icon name="book" className="size-5" />
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate font-display text-heading-md text-text-primary">{doc.title}</h1>
          <p className="flex items-center gap-3 text-caption text-text-subtle">
            <StatusPill status={life.family} label={life.label} kind="inline" />
            <span className="tabular">Version {doc.version}</span>
            {dirty ? (
              <span className="flex items-center gap-1.5 font-semibold text-status-warning-text">
                <span className="size-1.5 rounded-full bg-status-warning-base" aria-hidden />
                Unsaved changes
              </span>
            ) : null}
          </p>
        </div>
        <Button variant="secondary" onClick={() => window.close()}>
          <Icon name="x" className="size-4" />
          Close
        </Button>
        <Button loading={saveMutation.isPending} disabled={!dirty} onClick={() => setSaving(true)}>
          <Icon name="check" className="size-4" />
          Save version
        </Button>
      </header>

      <div className="min-h-0 flex-1">
        <RichTextEditor
          content={html}
          placeholderLabels={placeholderLabels}
          companyNames={companyNames}
          onChange={(next) => {
            setHtml(next);
            setDirty(true);
          }}
        />
      </div>
      {/* Every save writes a version, and the version list is what someone
          reads months later to answer "what changed and why". Asking for one
          line here is the difference between a history of "Content edited."
          and a history that means something. */}
      <Dialog
        open={saving}
        onOpenChange={(next) => {
          if (!next) setSaving(false);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save a new version</DialogTitle>
            <DialogDescription>The previous version stays in the history.</DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <TextField
              label="What changed?"
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Tightened the access review cadence to monthly"
            />
            <div>
              <span className="mb-1 block text-label-md font-semibold text-text-primary">
                Significance
              </span>
              <SegmentedControl
                value={changeType}
                onChange={(next) => setChangeType(next as ChangeType)}
                label="Version significance"
                items={[
                  { id: "patch", label: "Patch" },
                  { id: "minor", label: "Minor" },
                  { id: "major", label: "Major" },
                ]}
              />
              <p className="mt-1 text-caption text-text-subtle">
                Major for a rewrite, patch for a typo.
              </p>
            </div>
          </DialogBody>
          <DialogFooter>
            <Button variant="secondary" onClick={() => setSaving(false)}>
              Cancel
            </Button>
            <Button
              loading={saveMutation.isPending}
              onClick={() => saveMutation.mutate({ summary: summary.trim(), changeType })}
            >
              Save version
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
