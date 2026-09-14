import { apiFetch } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import type {
  AddFindingInput,
  CveLookup,
  ImportResult,
  RemediationPlan,
  SlaPolicy,
  VulnInstance,
  VulnInstanceDetail,
  VulnKpis,
  VulnListFilters,
  VulnReport,
  VulnThroughput,
} from "./types";

/** Data layer for the vulnerabilities module, wired to the real backend. */

function query(filters: VulnListFilters): string {
  const p = new URLSearchParams();
  if (filters.state) p.set("state", filters.state);
  if (filters.severity && filters.severity !== "all") p.set("severity", filters.severity);
  if (filters.asset_id) p.set("asset_id", filters.asset_id);
  if (filters.kev_only) p.set("kev_only", "true");
  if (filters.overdue_only) p.set("overdue_only", "true");
  if (filters.search) p.set("search", filters.search);
  const s = p.toString();
  return s ? `?${s}` : "";
}

export async function listVulnerabilities(filters: VulnListFilters = {}): Promise<VulnInstance[]> {
  return apiFetch<VulnInstance[]>(`/vulnerabilities${query(filters)}`);
}

export async function getVulnerability(id: string): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}`);
}

/** Real assets (for the manual-add picker, and for joining findings to an
 *  asset type on the overview dashboard) — the assets *feature* api is still
 *  mock-backed, so we hit the real endpoint directly for genuine ids. */
export async function listAssetOptions(): Promise<
  Array<{ id: string; name: string; asset_type: string }>
> {
  const page = await apiFetch<{ items: Array<{ id: string; name: string; asset_type: string }> }>(
    "/assets?page_size=200",
  );
  return (page.items ?? []).map((a) => ({ id: a.id, name: a.name, asset_type: a.asset_type }));
}

export async function vulnerabilityKpis(): Promise<VulnKpis> {
  return apiFetch<VulnKpis>("/vulnerabilities/kpis");
}

export async function getSlaPolicy(): Promise<SlaPolicy[]> {
  return apiFetch<SlaPolicy[]>("/vulnerabilities/sla");
}

export async function setSlaPolicy(severity: string, days: number | null): Promise<SlaPolicy[]> {
  return apiFetch<SlaPolicy[]>("/vulnerabilities/sla", {
    method: "PUT",
    body: JSON.stringify({ severity, days }),
  });
}

/** The canonical import columns the parser reads — kept in sync with the
 *  backend `_row_to_finding` and the register/import Template buttons. */
export const VULN_TEMPLATE_COLUMNS = [
  "asset_id",
  "asset",
  "title",
  "severity",
  "cve",
  "cvss",
  "cvss_vector",
  "cwe",
  "description",
  "recommendation",
  "component",
  "port",
  "url",
  "evidence",
] as const;

/** Build and download a sample import CSV (header + one worked example) so a
 *  downloaded-and-filled file imports cleanly. Shared by the module header
 *  and the import page. */
export function downloadVulnImportTemplate(): void {
  const example: Record<string, string> = {
    asset_id: "",
    asset: "web-server-01",
    title: "Example SQL injection",
    severity: "high",
    cve: "CVE-2024-1234",
    cvss: "8.5",
    cvss_vector: "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
    cwe: "CWE-89",
    description: "Unsanitised input reaches the SQL layer.",
    recommendation: "Parameterise queries and validate input.",
    component: "Web application",
    port: "443",
    url: "https://app.example.com/login",
    evidence: "' OR 1=1-- returned all rows",
  };
  const esc = (v: string) => (/[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v);
  const csv = [
    VULN_TEMPLATE_COLUMNS.join(","),
    VULN_TEMPLATE_COLUMNS.map((c) => esc(example[c] ?? "")).join(","),
  ].join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = "verity_vulnerability_import_template.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export async function addFinding(input: AddFindingInput): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>("/vulnerabilities", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export async function transitionVulnerability(
  id: string,
  toState: string,
  note?: string,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/transition`, {
    method: "POST",
    body: JSON.stringify({ to_state: toState, note: note ?? null }),
  });
}

export async function verifyVulnerability(
  id: string,
  resolutionNotes?: string,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/verify`, {
    method: "POST",
    body: JSON.stringify({ resolution_notes: resolutionNotes ?? null }),
  });
}

export async function acceptVulnerability(
  id: string,
  reason: string,
  expiresAt: string,
  compensatingControls?: string | null,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/accept`, {
    method: "POST",
    body: JSON.stringify({
      reason,
      expires_at: expiresAt,
      compensating_controls: compensatingControls ?? null,
    }),
  });
}

export async function vulnerabilityThroughput(): Promise<VulnThroughput> {
  return apiFetch<VulnThroughput>("/vulnerabilities/throughput");
}

/** Resolve a CVE from a finding title (best-effort NVD autofill for manual add). */
export async function lookupCveByTitle(title: string, cveId?: string | null): Promise<CveLookup> {
  return apiFetch<CveLookup>("/vulnerabilities/lookup-by-title", {
    method: "POST",
    body: JSON.stringify({ title, cve_id: cveId ?? null }),
  });
}

/** Re-pull live threat intel (EPSS/KEV/exploit/patch) for this finding's CVE. */
export async function reenrichVulnerability(id: string): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/reenrich`, { method: "POST" });
}

/** Set the accountable owner and replace the finding's assignment targets.
 *  Owner drives SLA escalation and remediation approval; targets are the
 *  additional people, roles and groups on the finding. */
export async function assignVulnerability(
  id: string,
  ownerMembershipId: string | null,
  targets: Array<{ target_type: "user" | "role" | "group"; target_id: string }>,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/assign`, {
    method: "POST",
    body: JSON.stringify({ owner_membership_id: ownerMembershipId, targets }),
  });
}

/** Record the same finding on another asset (a sibling instance). */
export async function linkVulnerabilityAsset(
  id: string,
  assetId: string,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/link-asset`, {
    method: "POST",
    body: JSON.stringify({ asset_id: assetId }),
  });
}

/** Move this finding to a different asset (it was misattributed). */
export async function moveVulnerabilityAsset(
  id: string,
  assetId: string,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/move-asset`, {
    method: "POST",
    body: JSON.stringify({ asset_id: assetId }),
  });
}

// ---- remediation plan lifecycle (P8/P9) ----

export async function getRemediationPlan(id: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan`);
}

export async function generateRemediationPlan(id: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan`, { method: "POST" });
}

export async function approveRemediationPlan(id: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan/approve`, {
    method: "POST",
  });
}

export async function applyRemediationPlan(id: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan/apply`, {
    method: "POST",
  });
}

export async function verifyRemediationPlan(id: string, evidence: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan/verify`, {
    method: "POST",
    body: JSON.stringify({ evidence }),
  });
}

export async function cancelRemediationPlan(id: string, reason: string): Promise<RemediationPlan> {
  return apiFetch<RemediationPlan>(`/vulnerabilities/${id}/remediation-plan/cancel`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function listVulnReports(): Promise<VulnReport[]> {
  return apiFetch<VulnReport[]>("/vulnerabilities/reports");
}

export async function reparseVulnReport(id: string): Promise<ImportResult> {
  return apiFetch<ImportResult>(`/vulnerabilities/reports/${id}/reparse`, { method: "POST" });
}

/** Authenticated file fetch for the report download (a plain link 401s). */
export async function downloadVulnReport(id: string): Promise<Blob> {
  const response = await fetch(`/api/v1/vulnerabilities/reports/${id}/download`, {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  return response.blob();
}

export async function importVulnerabilities(
  file: File,
  reportName: string,
  reportType = "vulnerability_scan",
  scanTool?: string,
): Promise<ImportResult> {
  const form = new FormData();
  form.set("file", file);
  form.set("report_name", reportName);
  form.set("report_type", reportType);
  if (scanTool) form.set("scan_tool", scanTool);
  // apiFetch sets the bearer + JSON headers; a multipart body needs a raw fetch
  // so the browser writes the multipart boundary itself.
  const response = await fetch("/api/v1/vulnerabilities/import", {
    method: "POST",
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
    body: form,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.error?.message ?? "Import failed");
  }
  return response.json();
}

/** Ask for the risk on a finding to be accepted for a fixed period. Duration,
 *  not a date: the clock starts when the approver says yes. */
export async function requestVulnException(
  id: string,
  body: {
    duration_days: number;
    rationale: string;
    potential_risks: string;
    compensating_controls?: string | null;
  },
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/exception`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/** Approve or reject the open request. The server refuses a decision from
 *  whoever raised it, and requires a note on a rejection. */
export async function decideVulnException(
  id: string,
  approve: boolean,
  note?: string,
): Promise<VulnInstanceDetail> {
  return apiFetch<VulnInstanceDetail>(`/vulnerabilities/${id}/exception/decide`, {
    method: "POST",
    body: JSON.stringify({ approve, note: note ?? null }),
  });
}
