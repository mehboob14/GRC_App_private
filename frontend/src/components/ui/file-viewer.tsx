import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import DOMPurify from "dompurify";
import mammoth from "mammoth";
import { cn } from "@/lib/cn";
import "@/styles/document-prose.css";
import { Button } from "./button";
import { Icon, type IconName } from "./icon";
import { canReadOoxml, readSlides, readWorkbook, type Sheet, type Slide } from "./ooxml";

/**
 * In-platform preview of a stored file, for any module that holds one.
 *
 * The file is fetched with the caller's authenticated fetcher and turned into a
 * blob, because the API is authenticated and a bare `<img src="/api/…">` would
 * 401.
 *
 * On the sandbox attribute, which is deliberately absent from the PDF frame:
 * the browser's built-in PDF viewer is itself a scripted document, so ANY
 * sandbox value blanks the frame — `""`, `allow-scripts`, `allow-same-origin`
 * and both together all render nothing, silently, with no console error. The
 * bytes are safe by construction instead: `core/storage.py` sniffs magic bytes
 * and only ever records `application/pdf` for a file starting with `%PDF-`, and
 * a blob: URL is never content-sniffed, so its recorded type is authoritative
 * and uploaded bytes cannot be reinterpreted as HTML. html, svg and xml are
 * refused at upload, so they never reach this component at all.
 */

/** OOXML types the server accepts on upload (the `core/storage.py` allowlist). */
export const DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
export const XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
export const PPTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation";

/** Render caps. A preview is a look, not a full reader — past these the file is
 *  better opened in its own application, and rendering it would jank the tab. */
const MAX_TEXT_CHARS = 400_000;
const MAX_TABLE_ROWS = 500;

export type FileKind = "pdf" | "image" | "docx" | "csv" | "text" | "sheet" | "slides" | "unknown";

export function detectFileKind(contentType: string | null, filename: string | null): FileKind {
  const type = (contentType ?? "").toLowerCase();
  const name = (filename ?? "").toLowerCase();
  if (type === "application/pdf") return "pdf";
  if (/^image\/(png|jpeg|gif|webp)$/.test(type)) return "image";
  if (type === DOCX_CONTENT_TYPE) return "docx";
  if (type === XLSX_CONTENT_TYPE) return "sheet";
  if (type === PPTX_CONTENT_TYPE) return "slides";
  // The server sniffs magic bytes, so every plain-text upload arrives as
  // text/plain — a csv is only distinguishable from a txt by its name.
  if (type === "text/plain" && /\.(csv|tsv)$/.test(name)) return "csv";
  if (type === "text/plain" || type === "application/json") return "text";
  return "unknown";
}

/** RFC-4180-ish: honours quoted fields, escaped quotes and embedded newlines.
 *  Splitting on "," would mangle any export with a comma inside a description,
 *  which in a compliance export is most of them. */
function parseDelimited(text: string, delimiter: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    if (quoted) {
      if (char !== '"') {
        field += char;
      } else if (text[i + 1] === '"') {
        field += '"';
        i += 1;
      } else {
        quoted = false;
      }
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === delimiter) {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char;
    }
  }
  if (field !== "" || row.length > 0) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

type Loaded =
  | { kind: "pdf"; url: string }
  | { kind: "image"; url: string }
  | { kind: "docx"; html: string }
  | { kind: "csv"; rows: string[][]; truncated: boolean }
  | { kind: "text"; text: string; truncated: boolean }
  | { kind: "sheet"; sheets: Sheet[] }
  | { kind: "slides"; slides: Slide[] };

/** Named so a file we genuinely cannot read says which kind it was. */
const NAMED: Record<string, { label: string; icon: IconName }> = {
  sheet: { label: "Excel workbook", icon: "spreadsheet" },
  slides: { label: "PowerPoint deck", icon: "layers" },
};

export function FileViewer({
  fileKey,
  title,
  filename,
  contentType,
  fetchBlob,
  heightClass = "h-[32rem]",
  className,
}: {
  /** Stable identity of the file (the record id). The fetch re-runs when this
   *  changes — never on `fetchBlob`, which callers pass as an inline arrow and
   *  which would otherwise refetch on every render. */
  fileKey: string;
  title: string;
  filename: string | null;
  contentType: string | null;
  /** Authenticated fetch of the bytes. Called once per file. */
  fetchBlob: () => Promise<Blob>;
  heightClass?: string;
  className?: string;
}) {
  const kind = useMemo(() => detectFileKind(contentType, filename), [contentType, filename]);
  const [state, setState] = useState<Loaded | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fetchRef = useRef(fetchBlob);
  fetchRef.current = fetchBlob;

  useEffect(() => {
    // Nothing to fetch for a format we cannot read at all — go straight to
    // the download prompt rather than pulling megabytes to throw them away.
    if (kind === "unknown") return;
    if ((kind === "sheet" || kind === "slides") && !canReadOoxml()) return;

    let objectUrl: string | null = null;
    let cancelled = false;
    setState(null);
    setError(null);

    void (async () => {
      try {
        const blob = await fetchRef.current();
        if (cancelled) return;

        if (kind === "docx") {
          const { value } = await mammoth.convertToHtml({ arrayBuffer: await blob.arrayBuffer() });
          if (!cancelled) setState({ kind: "docx", html: DOMPurify.sanitize(value) });
          return;
        }
        if (kind === "csv" || kind === "text") {
          const raw = await blob.text();
          if (cancelled) return;
          const truncated = raw.length > MAX_TEXT_CHARS;
          const text = truncated ? raw.slice(0, MAX_TEXT_CHARS) : raw;
          if (kind === "text") {
            setState({ kind: "text", text, truncated });
            return;
          }
          const all = parseDelimited(text, filename?.toLowerCase().endsWith(".tsv") ? "\t" : ",");
          setState({
            kind: "csv",
            rows: all.slice(0, MAX_TABLE_ROWS),
            truncated: truncated || all.length > MAX_TABLE_ROWS,
          });
          return;
        }
        if (kind === "sheet") {
          const sheets = await readWorkbook(blob, MAX_TABLE_ROWS);
          if (!cancelled) setState({ kind: "sheet", sheets });
          return;
        }
        if (kind === "slides") {
          const slides = await readSlides(blob);
          if (!cancelled) setState({ kind: "slides", slides });
          return;
        }
        objectUrl = URL.createObjectURL(blob);
        setState(
          kind === "pdf" ? { kind: "pdf", url: objectUrl } : { kind: "image", url: objectUrl },
        );
      } catch {
        if (!cancelled) setError("Couldn't load this file for preview.");
      }
    })();

    return () => {
      cancelled = true;
      // Revoked on unmount and on every change of file, or each preview would
      // leak its blob for the lifetime of the tab.
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [kind, filename, fileKey]);

  const frame = (body: ReactNode) => (
    <div className={cn("overflow-hidden rounded-lg border border-border bg-surface-sunken", className)}>
      {body}
    </div>
  );

  if (error) {
    return frame(
      <div className="px-4 py-10 text-center">
        <p className="text-body-sm text-status-danger-text">{error}</p>
      </div>,
    );
  }

  if (kind === "unknown" || ((kind === "sheet" || kind === "slides") && !canReadOoxml())) {
    const named = NAMED[kind];
    return frame(
      <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
        <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover text-text-subtle">
          <Icon name={named?.icon ?? "doc"} className="size-5" aria-hidden />
        </span>
        <p className="max-w-md text-body-md text-text-secondary">
          {named
            ? `This browser can't unpack a ${named.label}. Download it to open in its own application.`
            : "This file type can't be previewed in the browser. Download it to open it."}
        </p>
        <p className="text-caption text-text-subtle">
          {filename ?? "file"}
          {contentType ? ` · ${contentType}` : ""}
        </p>
      </div>,
    );
  }

  if (!state) {
    return frame(
      <p className={cn("flex items-center justify-center text-body-sm text-text-subtle", heightClass)}>
        <Icon name="spinner" className="mr-2 size-4 animate-spin" aria-hidden />
        Loading file…
      </p>,
    );
  }

  if (state.kind === "pdf") {
    // No sandbox attribute — see the note at the top of this file.
    return <iframe title={title} src={state.url} className={cn("w-full rounded-lg border border-border bg-surface-sunken", heightClass, className)} />;
  }

  if (state.kind === "image") {
    return frame(
      <div className="flex justify-center p-3">
        <img
          src={state.url}
          alt={title}
          className="max-h-[32rem] w-auto max-w-full rounded-sm object-contain"
        />
      </div>,
    );
  }

  if (state.kind === "docx") {
    return frame(
      <div className={cn("overflow-auto bg-surface-primary p-6", heightClass)}>
        {/* Sanitised by DOMPurify above: an uploaded file is untrusted input. */}
        <div className="document-prose" dangerouslySetInnerHTML={{ __html: state.html }} />
      </div>,
    );
  }

  if (state.kind === "csv") {
    const [head, ...body] = state.rows;
    return frame(
      <div className={cn("overflow-auto", heightClass)}>
        <table className="w-full border-collapse text-caption">
          <thead className="sticky top-0 bg-surface-primary">
            <tr>
              {(head ?? []).map((cell, i) => (
                <th
                  key={i}
                  className="border-b border-border px-3 py-2 text-left font-semibold text-text-primary"
                >
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {body.map((cells, r) => (
              <tr key={r} className="even:bg-surface-sunken">
                {cells.map((cell, c) => (
                  <td key={c} className="border-b border-border px-3 py-1.5 text-text-secondary">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {state.truncated ? (
          <p className="px-3 py-2 text-caption text-text-subtle">
            Preview truncated. Download the file for the full contents.
          </p>
        ) : null}
      </div>,
    );
  }

  if (state.kind === "sheet") {
    return frame(<SheetView sheets={state.sheets} heightClass={heightClass} />);
  }

  if (state.kind === "slides") {
    return frame(
      <div className={cn("space-y-3 overflow-auto p-4", heightClass)}>
        {state.slides.length === 0 ? (
          <p className="text-body-sm text-text-subtle">This deck has no readable text.</p>
        ) : (
          state.slides.map((slide) => (
            <section key={slide.name} className="rounded-md border border-border bg-surface-primary p-4">
              <h3 className="mb-1.5 text-caption uppercase tracking-wide text-text-subtle">
                {slide.name}
              </h3>
              {slide.lines.length === 0 ? (
                <p className="text-body-sm text-text-subtle">No text on this slide.</p>
              ) : (
                <ul className="space-y-1">
                  {slide.lines.map((line, i) => (
                    <li
                      key={i}
                      className={cn(
                        "text-text-primary",
                        i === 0 ? "text-body-md font-semibold" : "text-body-sm",
                      )}
                    >
                      {line}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))
        )}
      </div>,
    );
  }

  return frame(
    <>
      {/* Rendered as text, never as markup: an uploaded file is untrusted input. */}
      <pre className={cn("overflow-auto p-4 text-caption leading-relaxed text-text-secondary", heightClass)}>
        {state.text}
      </pre>
      {state.truncated ? (
        <p className="border-t border-border px-4 py-2 text-caption text-text-subtle">
          Preview truncated. Download the file for the full contents.
        </p>
      ) : null}
    </>,
  );
}

/** A workbook, one sheet at a time. The first row is treated as the header —
 *  true of essentially every spreadsheet used as evidence. */
function SheetView({ sheets, heightClass }: { sheets: Sheet[]; heightClass: string }) {
  const [active, setActive] = useState(0);
  const sheet = sheets[active];

  if (!sheet) {
    return <p className="p-4 text-body-sm text-text-subtle">This workbook has no sheets.</p>;
  }

  const [head, ...body] = sheet.rows;
  const width = Math.max(head?.cells.length ?? 0, ...body.map((r) => r.cells.length), 0);

  return (
    <>
      {sheets.length > 1 ? (
        <div className="flex gap-1 overflow-x-auto border-b border-border bg-surface-primary px-2 py-1.5">
          {sheets.map((s, i) => (
            <button
              key={s.name}
              type="button"
              onClick={() => setActive(i)}
              className={cn(
                "shrink-0 rounded-sm px-2.5 py-1 text-caption transition-colors",
                i === active
                  ? "bg-action-accent-tint font-semibold text-text-link"
                  : "text-text-secondary hover:bg-surface-hover",
              )}
            >
              {s.name}
            </button>
          ))}
        </div>
      ) : null}
      <div className={cn("overflow-auto", heightClass)}>
        {sheet.rows.length === 0 ? (
          <p className="p-4 text-body-sm text-text-subtle">This sheet is empty.</p>
        ) : (
          <table className="w-full border-collapse text-caption">
            <thead className="sticky top-0 bg-surface-primary">
              <tr>
                <th className="w-10 border-b border-r border-border bg-surface-sunken px-2 py-2" />
                {Array.from({ length: width }, (_, i) => (
                  <th
                    key={i}
                    className="whitespace-nowrap border-b border-border px-3 py-2 text-left font-semibold text-text-primary"
                  >
                    {head?.cells[i] ?? ""}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((row) => (
                <tr key={row.index} className="even:bg-surface-sunken">
                  {/* The workbook's own row number, so a reader can talk about
                      "row 42" the way they would in Excel. A sparse sheet skips
                      numbers, and counting rendered rows would mislabel them. */}
                  <td className="border-b border-r border-border bg-surface-sunken px-2 py-1.5 text-right tabular text-text-faint">
                    {row.index}
                  </td>
                  {Array.from({ length: width }, (_, c) => (
                    <td
                      key={c}
                      className="whitespace-nowrap border-b border-border px-3 py-1.5 text-text-secondary"
                    >
                      {row.cells[c] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

/** Save a fetched blob to disk under its original filename. */
export async function saveBlob(fetchBlob: () => Promise<Blob>, filename: string): Promise<void> {
  const url = URL.createObjectURL(await fetchBlob());
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

/** A download button that works off the same fetcher the viewer uses. */
export function FileDownloadButton({
  fetchBlob,
  filename,
  onError,
  size = "sm",
  variant = "secondary",
}: {
  fetchBlob: () => Promise<Blob>;
  filename: string;
  onError?: (error: unknown) => void;
  size?: "sm" | "md";
  variant?: "primary" | "secondary";
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Button
      variant={variant}
      size={size}
      loading={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await saveBlob(fetchBlob, filename);
        } catch (error) {
          onError?.(error);
        } finally {
          setBusy(false);
        }
      }}
    >
      <Icon name="download" className="size-4" />
      Download
    </Button>
  );
}
