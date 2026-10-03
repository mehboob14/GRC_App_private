/**
 * Branding for documents that leave the app as a printed page, such as the
 * control gap assessment.
 *
 * Those pages are built by plain functions in a popup window, outside React, so
 * they cannot call a hook. The workspace shell publishes what it already loaded
 * (see BrandingEffects) and `withReportBranding` reads it back: no request at
 * print time, and nothing to wait for. When the shell has not loaded branding, or
 * the workspace has none, the page is returned untouched.
 */

type ReportBranding = {
  footer: string | null;
  /** A data URL, so the popup can draw it without a bearer token. */
  logo: string | null;
};

const NONE: ReportBranding = { footer: null, logo: null };

let current: ReportBranding = NONE;

/** Called by the shell as branding loads, and again with nothing on sign out or
 *  workspace switch, so one workspace's footer can never print on another's report. */
export function publishReportBranding(next: ReportBranding | null): void {
  current = next ?? NONE;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Only the raster types the API serves, so nothing but an image can reach `src`. */
const SAFE_IMAGE = /^data:image\/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+$/;

/**
 * Adds the workspace's logo above the report and its footer after it. The report's
 * own HTML is passed in and returned, so the caller changes by one call.
 */
export function withReportBranding(html: string): string {
  const { footer, logo } = current;
  let branded = html;

  if (logo && SAFE_IMAGE.test(logo)) {
    const mark = `<img src="${logo}" alt="" style="display:block;max-height:48px;max-width:220px;margin:0 0 14px" />`;
    branded = branded.replace(/<body[^>]*>/i, (open) => open + mark);
  }
  if (footer) {
    const block = `<div style="margin-top:28px;padding-top:10px;border-top:1px solid #E4E7EC;color:#667085;font-size:11px;white-space:pre-wrap">${escapeHtml(footer)}</div>`;
    const end = branded.toLowerCase().lastIndexOf("</body>");
    if (end !== -1) {
      branded = branded.slice(0, end) + block + branded.slice(end);
    }
  }
  return branded;
}
