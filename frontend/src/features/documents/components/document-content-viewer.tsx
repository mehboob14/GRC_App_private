import { useEffect, useState } from "react";
import DOMPurify from "dompurify";
import mammoth from "mammoth";
import { Button, Icon, useToast } from "@/components/ui";
import { downloadDocumentBlob } from "@/features/documents/api";
import type { DocumentDetail } from "@/features/documents/types";
import "../document-prose.css";

const MIN = 60;
const MAX = 200;
const STEP = 10;

/**
 * The Content tab. Every document type renders inline here by default: PDFs in
 * the browser's native viewer, authored HTML and Word files in a zoomable
 * "paper" surface. A Word file is converted to read-only HTML with mammoth —
 * the same conversion the editor uses, but not editable here, and done entirely
 * client-side so the original file never leaves the browser. Editing opens the
 * rich editor in its own tab. Files are fetched with the auth token (ADR-0012).
 */
export function DocumentContentViewer({
  doc,
  onEdit,
}: {
  doc: DocumentDetail;
  onEdit: () => void;
}) {
  const { toast } = useToast();
  const [zoom, setZoom] = useState(100);
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [docxHtml, setDocxHtml] = useState<string | null>(null);

  const isPdf = doc.content_format === "pdf";
  const isDocx = doc.content_format === "docx";

  // PDF → object URL for the browser's native viewer (no parsing).
  useEffect(() => {
    if (!isPdf) return;
    let revoked = false;
    let url: string | null = null;
    downloadDocumentBlob(doc.id)
      .then((blob) => {
        if (revoked) return;
        url = URL.createObjectURL(blob);
        setFileUrl(url);
      })
      .catch(() => setFileUrl(null));
    return () => {
      revoked = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [doc.id, isPdf]);

  // Word → converted to read-only HTML for the inline preview (client-side).
  useEffect(() => {
    if (!isDocx) return;
    let cancelled = false;
    downloadDocumentBlob(doc.id)
      .then(async (blob) => {
        const { value } = await mammoth.convertToHtml({
          arrayBuffer: await blob.arrayBuffer(),
        });
        if (!cancelled) setDocxHtml(DOMPurify.sanitize(value));
      })
      .catch(() => {
        if (!cancelled) setDocxHtml("");
      });
    return () => {
      cancelled = true;
    };
  }, [doc.id, isDocx]);

  async function download() {
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

  // -- PDF: native viewer (as-is) ------------------------------------------
  if (isPdf) {
    return (
      <div className="rounded-lg border border-border bg-surface-sunken">
        <div className="flex items-center justify-between border-b border-border bg-surface-primary px-3 py-2">
          <span className="text-body-sm text-text-secondary">{doc.filename}</span>
          <Button variant="secondary" size="sm" onClick={download}>
            <Icon name="download" className="size-4" />
            Download
          </Button>
        </div>
        {fileUrl ? (
          <iframe title={doc.title} src={fileUrl} className="h-[72vh] w-full" />
        ) : (
          <p className="px-3 py-10 text-center text-body-sm text-text-subtle">Loading file…</p>
        )}
      </div>
    );
  }

  // -- Authored HTML or converted Word: zoomable paper ---------------------
  const html = isDocx ? docxHtml : DOMPurify.sanitize(doc.content_html ?? "");
  const converting = isDocx && docxHtml === null;
  const failed = isDocx && docxHtml === "";

  return (
    <div className="rounded-lg border border-border bg-surface-sunken">
      <div className="flex items-center justify-between gap-2 border-b border-border bg-surface-primary px-3 py-2">
        <div className="flex items-center gap-1">
          <Button
            variant="ghost" size="icon-sm" aria-label="Zoom out"
            disabled={zoom <= MIN} onClick={() => setZoom((z) => Math.max(MIN, z - STEP))}
          >
            <span className="text-body-md">−</span>
          </Button>
          <span className="w-12 text-center text-body-sm tabular text-text-secondary">{zoom}%</span>
          <Button
            variant="ghost" size="icon-sm" aria-label="Zoom in"
            disabled={zoom >= MAX} onClick={() => setZoom((z) => Math.min(MAX, z + STEP))}
          >
            <span className="text-body-md">+</span>
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setZoom(100)} disabled={zoom === 100}>
            Reset
          </Button>
          {isDocx ? (
            <span className="ml-1 text-caption text-text-subtle">Converted preview</span>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {isDocx ? (
            <Button variant="secondary" size="sm" onClick={download}>
              <Icon name="download" className="size-4" />
              Download original
            </Button>
          ) : null}
          <Button variant="secondary" size="sm" onClick={onEdit}>
            <Icon name="type" className="size-4" />
            Edit content
          </Button>
        </div>
      </div>
      <div className="max-h-[72vh] overflow-auto p-6">
        {converting ? (
          <p className="py-10 text-center text-body-sm text-text-subtle">Rendering document…</p>
        ) : failed ? (
          <div className="py-10 text-center">
            <p className="text-body-sm text-text-secondary">
              This file couldn't be previewed here.
            </p>
            <Button className="mt-3" variant="secondary" size="sm" onClick={download}>
              <Icon name="download" className="size-4" />
              Download original
            </Button>
          </div>
        ) : (
          <div
            className="mx-auto origin-top rounded-lg border border-border bg-surface-primary shadow-1"
            style={{ width: 820, transform: `scale(${zoom / 100})`, transformOrigin: "top center" }}
          >
            <div
              className="prose-doc px-12 py-10"
              dangerouslySetInnerHTML={{ __html: html ?? "" }}
            />
          </div>
        )}
      </div>
    </div>
  );
}
