import { apiFetch } from "@/lib/api/client";
import { getAccessToken } from "@/lib/auth/session";
import type { ScopeModel } from "@/lib/api/types";

/**
 * The frameworks a workspace runs, the overlap preview, and the Statement of
 * Applicability. `apiFetch` adds `/api/v1`.
 */

/** A framework in the catalogue, as this workspace sees it. */
export type WorkspaceFramework = {
  framework_id: string;
  code: string;
  name: string;
  description: string | null;
  scope_model: ScopeModel;
  position: number;
  version_id: string | null;
  version: string | null;
  requirement_count: number;
  added: boolean;
  added_at: string | null;
};

export type OverlapGroup = {
  group: string;
  total: number;
  covered: number;
  partly: number;
  needs_new: number;
  no_control: number;
};

export type OverlapControl = { code: string; name: string; category: string };

/** What adding a framework would mean here, counted from what the workspace runs now. */
export type FrameworkOverlap = {
  framework_id: string;
  code: string;
  name: string;
  version: string;
  added: boolean;
  requirements_total: number;
  /** A control already running is the main route to the requirement. */
  covered: number;
  /** Only controls that cover part of it are running. */
  partly: number;
  /** Nothing running answers it; adding the framework brings the controls that do. */
  needs_new: number;
  no_control: number;
  controls_in_use: number;
  controls_to_adopt: OverlapControl[];
  groups: OverlapGroup[];
};

export type FrameworkAdded = {
  framework: WorkspaceFramework;
  controls_adopted: number;
  links_created: number;
};

export type RequirementState = "excluded" | "met" | "partly" | "not_started" | "no_controls";
export type ProvidedBy = "organization" | "supplier";

export type ApplicabilityControl = {
  control_id: string;
  code: string;
  name: string;
  status: string;
  ready: boolean;
  coverage: "full" | "partial" | null;
};

export type ApplicabilityRow = {
  requirement_id: string;
  requirement_key: string;
  code: string;
  name: string;
  description: string | null;
  category: string;
  /** Cannot be excluded: the management system clauses. */
  locked: boolean;
  applicable: boolean;
  justification: string | null;
  provided_by: ProvidedBy;
  owner_membership_id: string | null;
  owner_name: string | null;
  reviewed_at: string | null;
  state: RequirementState;
  controls: ApplicabilityControl[];
};

export type ApplicabilitySummary = {
  total: number;
  applicable: number;
  excluded: number;
  reviewed: number;
  met: number;
  partly: number;
  not_started: number;
  no_controls: number;
};

export type Statement = {
  framework_id: string;
  code: string;
  name: string;
  version: string;
  scope_statement: string | null;
  summary: ApplicabilitySummary;
  rows: ApplicabilityRow[];
};

export type ApplicabilityPut = {
  applicable: boolean;
  justification?: string | null;
  provided_by?: ProvidedBy;
  owner_membership_id?: string | null;
  /** Stamp the row as reviewed now. */
  reviewed?: boolean;
};

export const workspaceFrameworks = () => apiFetch<WorkspaceFramework[]>("/tenant-frameworks");

export const frameworkOverlap = (frameworkId: string) =>
  apiFetch<FrameworkOverlap>(`/frameworks/${frameworkId}/overlap`);

export const addFramework = (frameworkId: string) =>
  apiFetch<FrameworkAdded>("/tenant-frameworks", {
    method: "POST",
    body: JSON.stringify({ framework_id: frameworkId }),
  });

export const getStatement = (frameworkId: string) =>
  apiFetch<Statement>(`/frameworks/${frameworkId}/applicability`);

export const putApplicability = (frameworkId: string, requirementId: string, body: ApplicabilityPut) =>
  apiFetch<ApplicabilityRow>(`/frameworks/${frameworkId}/applicability/${requirementId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });

/** Authenticated download: a bare link would 401, the token rides in a header. */
export async function downloadStatement(frameworkId: string): Promise<void> {
  const response = await fetch(`/api/v1/frameworks/${frameworkId}/soa.xlsx`, {
    headers: { Authorization: `Bearer ${getAccessToken() ?? ""}` },
  });
  if (!response.ok) throw new Error("download failed");
  const blob = await response.blob();
  const match = /filename="?([^"]+)"?/.exec(response.headers.get("Content-Disposition") ?? "");
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = match?.[1] ?? "statement-of-applicability.xlsx";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
