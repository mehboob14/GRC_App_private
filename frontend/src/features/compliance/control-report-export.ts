import { controlsApi } from "@/lib/api/endpoints";
import { getAccessToken } from "@/lib/auth/session";
import type { ControlReport } from "@/lib/api/types";
import { withReportBranding } from "@/features/tenancy/report-branding";

/**
 * The gap-assessment export. CSV and XLSX are rendered server-side (one dataset,
 * one KPI computation) and downloaded here through an authenticated fetch — a
 * bare <a href> would 401, since the token rides in the Authorization header,
 * not a cookie. PDF is produced from the same report JSON by printing a branded
 * page, so it needs no server-side PDF engine.
 */

export async function downloadControlReport(
  format: "csv" | "xlsx",
): Promise<void> {
  const response = await fetch(controlsApi.reportExportUrl(format), {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("export failed");
  const blob = await response.blob();
  const disposition = response.headers.get("Content-Disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? `control-gap-assessment.${format}`;
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const STATUS_LABEL: Record<string, string> = {
  not_started: "Not started",
  in_progress: "In progress",
  implemented: "Implemented",
  not_applicable: "Not applicable",
};

/**
 * Open a print-ready report in a new window and invoke the browser's print
 * dialog, where the reader chooses "Save as PDF". Self-contained inline styles,
 * so it does not depend on the app's stylesheet being present in the new window.
 */
export function printControlReport(
  report: ControlReport,
  workspaceName: string,
): void {
  const k = report.kpis;
  const generated = new Date(report.generated_at).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const kpiCard = (label: string, value: string | number) => `
    <div class="kpi">
      <div class="kpi-value">${escapeHtml(String(value))}</div>
      <div class="kpi-label">${escapeHtml(label)}</div>
    </div>`;

  const pctOf = (n: number) =>
    k.controls_total === 0 ? 0 : Math.round((n / k.controls_total) * 100);

  const statusRows = Object.entries(STATUS_LABEL)
    .map(
      ([key, label]) =>
        `<tr><td>${escapeHtml(label)}</td><td class="num">${k.by_status[key] ?? 0}</td></tr>`,
    )
    .join("");

  const bodyRows = report.rows
    .map(
      (row) => `
      <tr>
        <td class="code">${escapeHtml(row.code)}</td>
        <td>${escapeHtml(row.name)}</td>
        <td>${escapeHtml(row.category)}</td>
        <td>${escapeHtml(row.sub_category ?? "")}</td>
        <td>${escapeHtml(row.control_type ?? "")}</td>
        <td>${escapeHtml(row.status_label)}</td>
        <td>${escapeHtml(row.owner_name ?? "Unassigned")}</td>
        <td>${escapeHtml(row.frameworks.join(", "))}</td>
        <td>${escapeHtml(row.criteria.join(", "))}</td>
        <td class="num">${row.evidence_count}</td>
      </tr>`,
    )
    .join("");

  const html = `<!doctype html>
<html><head><meta charset="utf-8" />
<title>Control gap assessment</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #101828; margin: 32px; }
  h1 { font-size: 20px; margin: 0 0 2px; }
  .sub { color: #667085; font-size: 12px; margin-bottom: 20px; }
  .kpis { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 22px; }
  .kpi { border: 1px solid #E4E7EC; border-radius: 8px; padding: 10px 14px; min-width: 120px; }
  .kpi-value { font-size: 22px; font-weight: 700; }
  .kpi-label { font-size: 11px; color: #667085; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 2px; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.04em; color: #475467; margin: 20px 0 8px; }
  table { width: 100%; border-collapse: collapse; font-size: 11px; }
  th { text-align: left; background: #F4F5F7; color: #475467; padding: 6px 8px; border-bottom: 1px solid #E4E7EC; font-size: 10px; text-transform: uppercase; letter-spacing: 0.03em; }
  td { padding: 5px 8px; border-bottom: 1px solid #EEF0F3; vertical-align: top; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.code { font-weight: 700; white-space: nowrap; }
  .status-table { width: auto; margin-bottom: 8px; }
  .status-table td { border: 0; padding: 2px 16px 2px 0; }
  @page { size: landscape; }
  @media print { body { margin: 12mm; } thead { display: table-header-group; } tr { break-inside: avoid; } }
</style></head>
<body>
  <h1>Control gap assessment</h1>
  <div class="sub">${escapeHtml(workspaceName)} · ${escapeHtml(report.framework_label)} · generated ${escapeHtml(generated)}</div>

  <div class="kpis">
    ${kpiCard("Controls in scope", k.controls_total)}
    ${kpiCard("With evidence", `${k.controls_evidenced} (${pctOf(k.controls_evidenced)}%)`)}
    ${kpiCard("With an owner", `${k.controls_owned} (${pctOf(k.controls_owned)}%)`)}
    ${kpiCard("Ready for audit", `${k.controls_ready} (${pctOf(k.controls_ready)}%)`)}
    ${kpiCard("Failing an automated test", k.controls_failing_automation)}
    ${kpiCard("Criteria mapped", k.criteria_mapped)}
    ${kpiCard("Disabled", k.controls_disabled)}
  </div>

  <h2>Controls by status</h2>
  <table class="status-table"><tbody>${statusRows}</tbody></table>

  <h2>Controls (${report.rows.length})</h2>
  <table>
    <thead><tr>
      <th>Code</th><th>Control</th><th>Type</th><th>Sub-type</th><th>Design</th>
      <th>Status</th><th>Owner</th><th>Framework</th><th>Criteria</th><th>Evidence</th>
    </tr></thead>
    <tbody>${bodyRows}</tbody>
  </table>
</body></html>`;

  const win = window.open("", "_blank");
  if (!win) throw new Error("popup blocked");
  win.document.write(withReportBranding(html));
  win.document.close();
  win.focus();
  // Give the new document a tick to lay out before the print dialog opens.
  win.setTimeout(() => win.print(), 250);
}
