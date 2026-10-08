import { apiFetch } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import type {
  Approver,
  AssistDraft,
  CategoryNode,
  ImportPreview,
  ImportResult,
  ImportRow,
  LibraryTemplate,
  LinkType,
  Options,
  Register,
  RegisterInput,
  RiskDetail,
  RiskFilters,
  RiskInput,
  RiskPage,
  RiskSort,
  Summary,
} from "./types";

/**
 * Data layer for the risk register. `apiFetch` adds `/api/v1`. Most mutations on
 * one risk return the whole `RiskDetail`, so callers seed the detail cache with
 * the response instead of refetching.
 */

// -- registers ---------------------------------------------------------------

export const listRegisters = () => apiFetch<Register[]>("/risks/registers");

export const createRegister = (body: RegisterInput) =>
  apiFetch<Register>("/risks/registers", { method: "POST", body: JSON.stringify(body) });

export const updateRegister = (id: string, body: RegisterInput) =>
  apiFetch<Register>(`/risks/registers/${id}`, { method: "PATCH", body: JSON.stringify(body) });

export const saveCategories = (id: string, categories: CategoryNode[]) =>
  apiFetch<Register>(`/risks/registers/${id}/categories`, {
    method: "PUT",
    body: JSON.stringify({ categories }),
  });

export const getOptions = () => apiFetch<Options>("/risks/options");

// -- register views ----------------------------------------------------------------

export function filterParams(registerId: string, f: Partial<RiskFilters>): URLSearchParams {
  const p = new URLSearchParams({ register_id: registerId });
  if (f.search) p.set("search", f.search);
  for (const v of f.statuses ?? []) p.append("statuses", v);
  for (const v of f.bands ?? []) p.append("bands", v);
  for (const v of f.category_ids ?? []) p.append("category_ids", v);
  for (const v of f.treatments ?? []) p.append("treatments", v);
  for (const v of f.department_ids ?? []) p.append("department_ids", v);
  for (const v of f.attention ?? []) p.append("attention", v);
  if (f.owner) p.set("owner", f.owner);
  if (f.cell) p.set("cell", f.cell);
  for (const v of f.custom ?? []) p.append("custom", v);
  return p;
}

export function listRisks(
  registerId: string,
  filters: Partial<RiskFilters>,
  page: number,
  pageSize: number,
  sort: RiskSort | null,
  direction: "asc" | "desc",
): Promise<RiskPage> {
  const p = filterParams(registerId, filters);
  p.set("page", String(page));
  p.set("page_size", String(pageSize));
  if (sort) {
    p.set("sort", sort);
    p.set("direction", direction);
  }
  return apiFetch<RiskPage>(`/risks?${p.toString()}`);
}

export const getSummary = (registerId: string) =>
  apiFetch<Summary>(`/risks/summary?register_id=${registerId}`);

// -- one risk -----------------------------------------------------------------------

export const getRisk = (id: string) => apiFetch<RiskDetail>(`/risks/${id}`);

export const createRisk = (body: RiskInput) =>
  apiFetch<RiskDetail>("/risks", { method: "POST", body: JSON.stringify(body) });

export const updateRisk = (id: string, body: RiskInput) =>
  apiFetch<RiskDetail>(`/risks/${id}`, { method: "PATCH", body: JSON.stringify(body) });

const post = (path: string, body: unknown = {}) =>
  apiFetch<RiskDetail>(path, { method: "POST", body: JSON.stringify(body) });

export const changeStatus = (id: string, status: string, note?: string) =>
  post(`/risks/${id}/status`, { status, note: note || null });

export const markReviewed = (id: string, note: string | null, nextReviewOn: string | null) =>
  post(`/risks/${id}/review`, { note, next_review_on: nextReviewOn });

export const linkControls = (id: string, controlIds: string[]) =>
  post(`/risks/${id}/controls`, { control_ids: controlIds });

export const unlinkControl = (id: string, controlId: string) =>
  apiFetch<RiskDetail>(`/risks/${id}/controls/${controlId}`, { method: "DELETE" });

export const linkRecord = (id: string, targetType: LinkType, targetId: string) =>
  post(`/risks/${id}/links`, { target_type: targetType, target_id: targetId });

export const unlinkRecord = (id: string, linkId: string) =>
  apiFetch<RiskDetail>(`/risks/${id}/links/${linkId}`, { method: "DELETE" });

export const addAction = (
  id: string,
  body: { title: string; priority: string; owner_membership_id: string | null; due_on: string | null },
) => post(`/risks/${id}/actions`, body);

export const listApprovers = () => apiFetch<Approver[]>("/risks/approvers");

export const requestAcceptance = (
  id: string,
  body: { approver_membership_id: string; rationale: string; expires_on: string },
) => post(`/risks/${id}/acceptances`, body);

export const decideAcceptance = (id: string, acceptanceId: string, approve: boolean, note: string) =>
  post(`/risks/${id}/acceptances/${acceptanceId}/decision`, { approve, note: note || null });

export const withdrawAcceptance = (id: string, acceptanceId: string) =>
  post(`/risks/${id}/acceptances/${acceptanceId}/withdraw`);

export const revokeAcceptance = (id: string, acceptanceId: string, reason: string) =>
  post(`/risks/${id}/acceptances/${acceptanceId}/revoke`, { reason });

// -- library, assist, promotion ------------------------------------------------------

export const listLibrary = (registerId: string) =>
  apiFetch<LibraryTemplate[]>(`/risks/library?register_id=${registerId}`);

export const adoptTemplates = (registerId: string, codes: string[]) =>
  apiFetch<{ created: number; skipped: number; controls_linked: number }>("/risks/library/adopt", {
    method: "POST",
    body: JSON.stringify({ register_id: registerId, codes }),
  });

export const assistDraft = (registerId: string, title: string, description: string | null) =>
  apiFetch<AssistDraft>("/risks/assist", {
    method: "POST",
    body: JSON.stringify({ register_id: registerId, title, description: description || null }),
  });

export const promoteFinding = (findingId: string, registerId: string) =>
  apiFetch<RiskDetail>("/risks/from-vendor-finding", {
    method: "POST",
    body: JSON.stringify({ finding_id: findingId, register_id: registerId }),
  });

// -- import and export ------------------------------------------------------------------

export function previewImport(registerId: string, file: File): Promise<ImportPreview> {
  const form = new FormData();
  form.append("register_id", registerId);
  form.append("file", file);
  return apiFetch<ImportPreview>("/risks/import/preview", { method: "POST", body: form });
}

const IMPORT_FIELDS = [
  "row_number",
  "title",
  "description",
  "category_id",
  "sub_category_id",
  "status",
  "owner_membership_id",
  "department_group_id",
  "inherent_likelihood",
  "inherent_impact",
  "residual_likelihood",
  "residual_impact",
  "root_cause",
  "consequences",
  "recommendations",
  "treatment",
  "treatment_plan",
  "treatment_due_on",
  "next_review_on",
] as const satisfies readonly (keyof ImportRow)[];

/** Only the importable fields go back: the server refuses unknown keys. */
export const commitImport = (registerId: string, rows: ImportRow[]) =>
  apiFetch<ImportResult>("/risks/import", {
    method: "POST",
    body: JSON.stringify({
      register_id: registerId,
      rows: rows.map((r) => ({
        ...Object.fromEntries(IMPORT_FIELDS.map((k) => [k, r[k]])),
        custom_fields: r.custom_fields ?? {},
      })),
    }),
  });

/** Authenticated download: a bare link would 401, the token rides in a header. */
async function download(path: string, fallback: string): Promise<void> {
  const response = await fetch(`/api/v1${path}`, {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  const blob = await response.blob();
  const match = /filename="?([^"]+)"?/.exec(response.headers.get("Content-Disposition") ?? "");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = match?.[1] ?? fallback;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export const downloadTemplate = (registerId: string) =>
  download(`/risks/import/template?register_id=${registerId}`, "risk_import_template.xlsx");

export const downloadExport = (registerId: string, format: "csv" | "xlsx", filters: Partial<RiskFilters>) => {
  const p = filterParams(registerId, filters);
  p.set("format", format);
  return download(`/risks/export?${p.toString()}`, `risk_register.${format}`);
};
