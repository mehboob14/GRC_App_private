import { getAccessToken } from "@/lib/auth/session";
import { getProviderToken, isProviderPath } from "@/lib/provider/session";

/** The only image types the API serves as a logo. SVG is deliberately not one. */
const IMAGE_TYPE = /^image\/(png|jpeg|webp)$/;

function blobToDataUrl(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result));
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });
}

/**
 * An authenticated image as a self-contained data URL.
 *
 * An <img src> cannot send the bearer token, so the bytes are fetched here and
 * handed to the page as a URL that needs no header. That also lets the same
 * value be written into a printed report, which a popup document could not load
 * from a path that wants a header. The token follows the same rule as `apiFetch`:
 * the platform admin's for /provider/* paths, the workspace's for the rest.
 *
 * Resolves to null for anything that is not a PNG, JPEG or WebP, and for every
 * failure: a missing image is a fallback for the caller to draw, never an error.
 */
export async function fetchImageDataUrl(path: string): Promise<string | null> {
  const token = isProviderPath(path) ? getProviderToken() : getAccessToken();
  if (!token) return null;
  try {
    const response = await fetch(`/api/v1${path}`, {
      headers: { Authorization: `Bearer ${token}`, Accept: "image/*" },
    });
    if (!response.ok || !IMAGE_TYPE.test(response.headers.get("Content-Type") ?? "")) {
      return null;
    }
    return await blobToDataUrl(await response.blob());
  } catch {
    return null;
  }
}
