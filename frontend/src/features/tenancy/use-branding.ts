import { useQuery } from "@tanstack/react-query";
import { readableAccent } from "@/lib/color";
import { useAuth } from "@/lib/auth/auth-context";
import { brandingApi } from "./branding-api";

/** Branding changes when an operator saves it, not while someone is working. */
const BRANDING_STALE_MS = 60 * 60 * 1000;

export type WorkspaceBranding = {
  /** The provider has set a logo or a colour, so the workspace's look replaces Verity's. */
  branded: boolean;
  /** The logo as a data URL, once it has loaded. */
  logo: string | null;
  /** The primary colour, darkened if it needed to be, or null to keep Verity's blue. */
  accent: string | null;
  footer: string | null;
};

const UNBRANDED: WorkspaceBranding = {
  branded: false,
  logo: null,
  accent: null,
  footer: null,
};

/**
 * What the signed in workspace looks like, read from `GET /tenant/branding`.
 *
 * Branding is decoration and must never get in the way: nothing here throws, and
 * a slow, refused or failed request leaves the workspace looking like Verity. The
 * answer is kept for an hour, and the key carries the workspace, so switching
 * workspaces can never show the previous one's look.
 */
export function useWorkspaceBranding(): WorkspaceBranding {
  const { principal } = useAuth();
  const tenantId = principal?.tenant_id;

  const branding = useQuery({
    queryKey: ["tenant-branding", tenantId],
    queryFn: brandingApi.get,
    enabled: Boolean(tenantId),
    staleTime: BRANDING_STALE_MS,
  });
  const logoRef = branding.data?.logo_ref ?? null;
  const logo = useQuery({
    // Keyed on the stored reference: a new upload is a new key, never the old image.
    queryKey: ["tenant-logo", tenantId, logoRef],
    queryFn: brandingApi.logo,
    enabled: Boolean(tenantId) && logoRef !== null,
    staleTime: Infinity,
  });

  const data = branding.data;
  if (!data) return UNBRANDED;
  return {
    branded: Boolean(data.logo_ref || data.primary_color),
    logo: logo.data ?? null,
    accent: readableAccent(data.primary_color),
    footer: data.document_footer?.trim() || null,
  };
}
