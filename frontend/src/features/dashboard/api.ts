import { apiFetch } from "@/lib/api/client";
import type {
  AssetSummary,
  ControlReport,
  DocumentKpis,
  DocumentRow,
  EngagementWindow,
  EvidenceRow,
  OwnedControl,
  PendingApproval,
  PendingCampaign,
  Posture,
  RiskPicture,
  RiskRegister,
  RiskSummary,
  TaskPage,
  TaskSummary,
  VendorSummary,
  VulnKpis,
} from "./types";

/**
 * Every call the dashboard makes, through the shared client. Each one reads an
 * endpoint that already exists; nothing here is dashboard specific on the
 * server. The permission each needs is noted so the page can hide the tile for
 * a role that lacks it, and a 403 that slips through hides it anyway.
 */

/** A task is "open" for the dashboard in the same four statuses the tasks
 *  overview counts. */
const OPEN_TASK_STATUSES = ["open", "in_progress", "blocked", "under_review"];

/** Large enough to hold one person's whole open queue in a single page. */
const MY_TASKS_PAGE_SIZE = "200";

export const dashboardApi = {
  /** frameworks:read */
  posture: () => apiFetch<Posture>("/engagement/dashboard"),
  engagement: () => apiFetch<EngagementWindow | null>("/engagement"),
  controlReport: () => apiFetch<ControlReport>("/controls/report"),

  /** risks:read. A summary belongs to one register, so find the default one. */
  risks: async (): Promise<RiskPicture | null> => {
    const registers = await apiFetch<RiskRegister[]>("/risks/registers");
    const active = registers.filter((register) => register.status === "active");
    const register = active.find((r) => r.is_default) ?? active[0];
    if (!register) return null;
    const summary = await apiFetch<RiskSummary>(`/risks/summary?register_id=${register.id}`);
    return { register, summary, registers: active.length };
  },

  /** vendors:read */
  vendors: () => apiFetch<VendorSummary>("/vendors/summary"),
  /** vulnerabilities:read */
  vulnerabilities: () => apiFetch<VulnKpis>("/vulnerabilities/kpis"),
  /** assets:read */
  assets: () => apiFetch<AssetSummary>("/assets/summary"),
  /** tasks:read */
  tasks: () => apiFetch<TaskSummary>("/tasks/summary"),
  /** documents:read */
  documents: () => apiFetch<DocumentRow[]>("/documents"),
  documentKpis: () => apiFetch<DocumentKpis>("/documents/kpis"),

  /** tasks:read. The register's own "assigned to me" filter. */
  myTasks: () => {
    const query = new URLSearchParams({ assignee: "me", page_size: MY_TASKS_PAGE_SIZE });
    for (const status of OPEN_TASK_STATUSES) query.append("statuses", status);
    return apiFetch<TaskPage>(`/tasks?${query.toString()}`);
  },
  /** documents:read. The same two reads the top bar's acknowledgements bell makes. */
  myApprovals: () => apiFetch<PendingApproval[]>("/documents/approvals/pending"),
  myCampaigns: () => apiFetch<PendingCampaign[]>("/documents/campaigns/pending"),
  /** frameworks:read. Live controls only: the endpoint leaves disabled ones out. */
  myControls: (membershipId: string) =>
    apiFetch<OwnedControl[]>(`/controls?owner_membership_id=${membershipId}`),
  /** evidence:read */
  evidence: () => apiFetch<EvidenceRow[]>("/evidence"),
};
