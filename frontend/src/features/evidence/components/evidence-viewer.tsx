import { useEffect, useState } from "react";
import { Button, Icon, Skeleton } from "@/components/ui";
import { evidenceApi } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/session";
import type { Evidence } from "@/lib/api/types";

/**
 * In-platform preview of a stored artefact.
 *
 * The file is fetched with the bearer token and turned into a blob URL, because
 * the API is authenticated and a bare <img src="/api/…"> would 401.
 *
 * Only formats the browser can render safely are shown inline. A blob URL is
 * same-origin, so rendering arbitrary uploaded HTML or SVG here would let an
 * uploaded file run script inside the app's own origin and reach a signed-in
 * session — the exact reason the download route sends
 * Content-Disposition: attachment. Anything off this list gets a download
 * instead of a preview, and says why.
 */
const INLINE_IMAGE = /^image\/(png|jpeg|gif|webp|bmp)$/i;
const INLINE_TEXT =
  /^(text\/(plain|csv|markdown)|application\/(json|xml)|text\/xml)$/i;
const INLINE_PDF = /^application\/pdf$/i;

/** Office formats no browser renders natively. Named so the message can be
 *  specific rather than a shrug. */
const OFFICE =
  /(officedocument|ms-?excel|ms-?word|ms-?powerpoint|opendocument)/i;

type Loaded =
  | { kind: "image" | "pdf"; url: string }
  | { kind: "text"; text: string }
  | { kind: "unsupported"; reason: string };

export function EvidenceViewer({ item }: { item: Evidence }) {
  const [state, setState] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (item.kind !== "file") return;
    const type = item.content_type ?? "";

    if (!INLINE_IMAGE.test(type) && !INLINE_TEXT.test(type) && !INLINE_PDF.test(type)) {
      setState({
        kind: "unsupported",
        reason: OFFICE.test(type)
          ? "Word, Excel and PowerPoint files cannot be rendered by a browser. Download it to open in its own application."
          : "This file type cannot be previewed safely in the browser. Download it to open it.",
      });
      return;
    }

    let objectUrl: string | null = null;
    let cancelled = false;

    void (async () => {
      try {
        const response = await fetch(evidenceApi.downloadUrl(item.id), {
          headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
        });
        if (!response.ok) throw new Error(String(response.status));
        const blob = await response.blob();
        if (cancelled) return;

        if (INLINE_TEXT.test(type)) {
          setState({ kind: "text", text: await blob.text() });
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setState({
          kind: INLINE_PDF.test(type) ? "pdf" : "image",
          url: objectUrl,
        });
      } catch {
        if (!cancelled) setError("Couldn't load this file for preview.");
      }
    })();

    return () => {
      cancelled = true;
      // Revoked on unmount and on every change of item, or each preview would
      // leak its blob for the lifetime of the tab.
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [item.id, item.kind, item.content_type]);

  if (item.kind === "link") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border bg-surface-sunken px-4 py-10 text-center">
        <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover text-text-subtle">
          <Icon name="globe" className="size-5" aria-hidden />
        </span>
        <p className="text-body-md text-text-secondary">
          This evidence is a link to a system Verity does not hold.
        </p>
        {item.link_url ? (
          <Button variant="secondary" asChild>
            <a href={item.link_url} target="_blank" rel="noopener noreferrer">
              Open in a new tab
              <Icon name="arrowr" className="size-4" />
            </a>
          </Button>
        ) : null}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md border border-status-danger-border bg-status-danger-bg px-4 py-6 text-center">
        <p className="text-body-md text-status-danger-text">{error}</p>
      </div>
    );
  }

  if (!state) return <Skeleton className="h-[28rem] w-full rounded-md" />;

  if (state.kind === "unsupported") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-md border border-dashed border-border bg-surface-sunken px-4 py-10 text-center">
        <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover text-text-subtle">
          <Icon name="doc" className="size-5" aria-hidden />
        </span>
        <p className="max-w-md text-body-md text-text-secondary">{state.reason}</p>
        <p className="text-caption text-text-subtle">
          {item.filename} · {item.content_type}
        </p>
      </div>
    );
  }

  if (state.kind === "text") {
    return (
      // Rendered as text, never as markup: an uploaded file is untrusted input.
      <pre className="max-h-[32rem] overflow-auto rounded-md border border-border bg-surface-sunken p-4 text-caption leading-relaxed text-text-secondary">
        {state.text}
      </pre>
    );
  }

  if (state.kind === "image") {
    return (
      <div className="flex justify-center rounded-md border border-border bg-surface-sunken p-3">
        <img
          src={state.url}
          alt={item.title}
          className="max-h-[32rem] w-auto max-w-full rounded-sm object-contain"
        />
      </div>
    );
  }

  return (
    <iframe
      // sandboxed: a PDF is still an uploaded file, and the blob URL is
      // same-origin. No allow-scripts, no allow-same-origin.
      sandbox=""
      src={state.url}
      title={item.title}
      className="h-[32rem] w-full rounded-md border border-border bg-surface-sunken"
    />
  );
}
