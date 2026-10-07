import { evidenceApi } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/session";
import type { Evidence } from "@/lib/api/types";

/** The download route is authenticated, so a bare `src="/api/..."` would 401.
 *  Every preview and every download goes through the bearer token into a blob. */
export function fetchEvidenceBlob(id: string): () => Promise<Blob> {
  return async () => {
    const response = await fetch(evidenceApi.downloadUrl(id), {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    });
    if (!response.ok) throw new Error(String(response.status));
    return response.blob();
  };
}

/** Save an evidence file to disk under its own name. The object URL is revoked
 *  straight after the click so it does not leak. */
export async function downloadEvidenceFile(item: Evidence): Promise<void> {
  const blob = await fetchEvidenceBlob(item.id)();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = item.filename ?? item.title;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
