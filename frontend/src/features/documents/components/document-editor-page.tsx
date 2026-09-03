import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import DOMPurify from "dompurify";
import mammoth from "mammoth";
import { Button, CodeChip, ErrorState, Icon, useToast } from "@/components/ui";
import { describeError, errorToast } from "@/lib/api/describe-error";
import {
  downloadDocumentBlob,
  getDocumentDetail,
  saveDocumentContent,
} from "@/features/documents/api";
import { RichTextEditor } from "./rich-text-editor";

/**
 * Full-screen policy editor, opened in its own tab from the Content tab. Renders
 * outside the app shell (ADR-0012): just the document and the editor.
 */
export function DocumentEditorPage() {
  const { documentId } = useParams();
  const { toast } = useToast();
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
    mutationFn: () => saveDocumentContent(documentId!, html ?? ""),
    onSuccess: () => {
      setDirty(false);
      toast({ title: "Content saved as a new version", tone: "success" });
    },
    onError: (error: unknown) => toast({ title: errorToast(error, "document"), tone: "danger" }),
  });

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

  return (
    <div className="flex h-screen flex-col bg-surface-page">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-border bg-surface-primary px-4 py-2.5">
        <div className="flex min-w-0 items-center gap-3">
          <CodeChip code={doc.code} />
          <div className="min-w-0">
            <p className="truncate text-body-md font-medium text-text-primary">{doc.title}</p>
            <p className="text-caption text-text-subtle">
              Editing content · v{doc.version}
              {dirty ? " · unsaved changes" : ""}
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Button variant="secondary" onClick={() => window.close()}>
            Close
          </Button>
          <Button
            loading={saveMutation.isPending}
            disabled={!dirty}
            onClick={() => saveMutation.mutate()}
          >
            <Icon name="check" className="size-4" />
            Save
          </Button>
        </div>
      </header>

      <div className="min-h-0 flex-1">
        <RichTextEditor
          content={html}
          onChange={(next) => {
            setHtml(next);
            setDirty(true);
          }}
        />
      </div>
    </div>
  );
}
