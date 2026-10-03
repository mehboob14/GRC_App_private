import { useEffect } from "react";
import { useAuth } from "@/lib/auth/auth-context";
import { useTheme } from "@/lib/theme";
import { publishReportBranding } from "./report-branding";
import { useWorkspaceBranding } from "./use-branding";

/**
 * Applies the workspace's branding to everything that is not drawn by a component:
 * the accent tokens, the browser tab title and the footer for printed reports.
 *
 * Every effect undoes itself, so leaving the shell (sign out) or changing workspace
 * puts Verity's own look back at once, before the next workspace's branding loads.
 * The logo and the name are drawn by the sidebar from the same hook.
 */
export function BrandingEffects() {
  const { principal } = useAuth();
  const { setAccent } = useTheme();
  const { branded, accent, footer, logo } = useWorkspaceBranding();
  const name = principal?.tenant_name;

  useEffect(() => {
    setAccent(accent);
    return () => setAccent(null);
  }, [accent, setAccent]);

  useEffect(() => {
    if (!branded || !name) return;
    const original = document.title;
    document.title = name;
    return () => {
      document.title = original;
    };
  }, [branded, name]);

  useEffect(() => {
    publishReportBranding({ footer, logo });
    return () => publishReportBranding(null);
  }, [footer, logo]);

  return null;
}
