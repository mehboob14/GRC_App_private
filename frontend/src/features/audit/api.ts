import { saveBlob } from "@/components/ui";
import { ApiError } from "@/lib/api/client";
import type { ApiErrorBody } from "@/lib/api/types";
import { getAccessToken } from "@/lib/auth/session";
import type { AuditExportOptions } from "./types";

/**
 * Download the audit trail as a file. A bare link would 401, since the token rides in
 * the Authorization header, so the file is fetched with it and saved from a blob.
 *
 * A refusal is thrown as the API's own error rather than "download failed", so a range
 * too long for Excel reaches the reader as the server's advice, and a dropped
 * connection reads as one (a CSV streams, so it can drop after the headers arrive).
 */
export async function downloadAuditExport(options: AuditExportOptions): Promise<void> {
  const params = new URLSearchParams({ format: options.format });
  if (options.from) params.set("from", options.from);
  if (options.to) params.set("to", options.to);
  if (options.includeSystem) params.set("include_system", "true");

  let response: Response;
  try {
    response = await fetch(`/api/v1/audit-log/export?${params.toString()}`, {
      headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    });
  } catch {
    throw ApiError.network();
  }
  if (!response.ok) {
    let body: ApiErrorBody;
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      body = {
        error: {
          code: "http_error",
          message: "Something went wrong. Try again, or contact support if it continues.",
          correlation_id: "unknown",
        },
      };
    }
    throw new ApiError(response.status, body);
  }

  let blob: Blob;
  try {
    blob = await response.blob();
  } catch {
    throw ApiError.network();
  }
  const named = /filename="?([^"]+)"?/.exec(response.headers.get("Content-Disposition") ?? "");
  const today = new Date().toISOString().slice(0, 10);
  await saveBlob(() => Promise.resolve(blob), named?.[1] ?? `audit-log-${today}.${options.format}`);
}
