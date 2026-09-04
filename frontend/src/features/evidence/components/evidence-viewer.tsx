import { Button, FileViewer, Icon } from "@/components/ui";
import { evidenceApi } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/session";
import type { Evidence } from "@/lib/api/types";

/**
 * Preview of a piece of evidence.
 *
 * Files render through the shared `FileViewer`, which covers every content type
 * the server will store (`core/storage.py` sniffs magic bytes against a
 * ten-value allowlist): pdf, png/jpeg/gif/webp, docx, csv, plain text and json
 * inline, with a named download prompt for xlsx and pptx, which no browser
 * renders natively. A link is not a file and gets its own card.
 */

/** The download route is authenticated, so a bare `src="/api/..."` would 401.
 *  Every preview goes through the bearer token into a blob. */
export function fetchEvidenceBlob(id: string): () => Promise<Blob> {
  return async () => {
    const response = await fetch(evidenceApi.downloadUrl(id), {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    });
    if (!response.ok) throw new Error(String(response.status));
    return response.blob();
  };
}

export function EvidenceViewer({ item, heightClass }: { item: Evidence; heightClass?: string }) {
  if (item.kind === "link") {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-surface-sunken px-4 py-10 text-center">
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

  return (
    <FileViewer
      fileKey={item.id}
      title={item.title}
      filename={item.filename}
      contentType={item.content_type}
      fetchBlob={fetchEvidenceBlob(item.id)}
      heightClass={heightClass}
    />
  );
}
