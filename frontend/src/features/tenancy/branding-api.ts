import { apiFetch } from "@/lib/api/client";
import { fetchImageDataUrl } from "@/lib/api/image";

/**
 * The part of a workspace's branding the app applies. The API returns more
 * (domain, mail identity); none of it is needed to draw the shell.
 */
export type TenantBranding = {
  /** The stored key of the uploaded logo, or null when there is none. */
  logo_ref: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  document_footer: string | null;
  updated_at: string;
};

export const brandingApi = {
  get: () => apiFetch<TenantBranding>("/tenant/branding"),
  /** The logo as a data URL, or null when there is none or it cannot be read. */
  logo: () => fetchImageDataUrl("/tenant/branding/logo"),
};
