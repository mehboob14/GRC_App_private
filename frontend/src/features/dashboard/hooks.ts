import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { ApiError } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { dashboardApi } from "./api";
import { evidenceGaps, summarizeFrameworks, summarizePolicies } from "./model";

/**
 * One hook per section, so each tile loads, fails and retries on its own and a
 * slow or forbidden module never holds the rest of the page back.
 */

/** A minute: these are summaries, not a feed, and nothing on this page polls. */
const STALE_MS = 60_000;

/** A role that cannot read a module is refused with a 403. The dashboard hides
 *  that tile instead of showing a failure for something the person was never
 *  meant to see. */
export function isForbidden(error: unknown): boolean {
  return error instanceof ApiError && error.status === 403;
}

/** What the signed-in role may read, so a tile it cannot read is never mounted
 *  (and so never asks). The server still decides; this only avoids the noise. */
export type Access = {
  /** frameworks:read, which covers the control library and the posture. */
  compliance: boolean;
  evidence: boolean;
  risks: boolean;
  vendors: boolean;
  vulnerabilities: boolean;
  assets: boolean;
  tasks: boolean;
  documents: boolean;
};

export function useAccess(): Access {
  const { principal } = useAuth();
  return useMemo(() => {
    // Read straight off the principal: the shared hasPermission helper warns in
    // development for any key the frontend's own list has not caught up with,
    // and the risk keys are not on it yet. The answer is the same either way,
    // since the server is the authority.
    const granted = new Set<string>(principal?.permissions ?? []);
    return {
      compliance: granted.has("frameworks:read"),
      evidence: granted.has("evidence:read"),
      risks: granted.has("risks:read"),
      vendors: granted.has("vendors:read"),
      vulnerabilities: granted.has("vulnerabilities:read"),
      assets: granted.has("assets:read"),
      tasks: granted.has("tasks:read"),
      documents: granted.has("documents:read"),
    };
  }, [principal]);
}

function useSection<T>(name: string, queryFn: () => Promise<T>, enabled = true) {
  const { principal } = useAuth();
  return useQuery({
    // Scoped to the workspace and the person, so switching either one can never
    // show the other's numbers.
    queryKey: ["dashboard", principal?.tenant_id, principal?.membership_id, name],
    queryFn,
    staleTime: STALE_MS,
    enabled,
  });
}

// -- the workspace ------------------------------------------------------------

export const usePosture = (enabled = true) => useSection("posture", dashboardApi.posture, enabled);
export const useEngagement = () => useSection("engagement", dashboardApi.engagement);
export const useFrameworks = () =>
  useSection("frameworks", async () => summarizeFrameworks((await dashboardApi.controlReport()).rows));
export const useRisks = () => useSection("risks", dashboardApi.risks);
export const useVendors = () => useSection("vendors", dashboardApi.vendors);
export const useVulnerabilities = () => useSection("vulnerabilities", dashboardApi.vulnerabilities);
export const useAssets = () => useSection("assets", dashboardApi.assets);
export const useTasks = () => useSection("tasks", dashboardApi.tasks);
export const usePolicies = () =>
  useSection("policies", async () => {
    const [rows, kpis] = await Promise.all([dashboardApi.documents(), dashboardApi.documentKpis()]);
    return summarizePolicies(rows, kpis);
  });

// -- the caller's own work ----------------------------------------------------

const useMyTasks = (enabled: boolean) => useSection("my-tasks", dashboardApi.myTasks, enabled);
const useMyApprovals = (enabled: boolean) => useSection("my-approvals", dashboardApi.myApprovals, enabled);
const useMyCampaigns = (enabled: boolean) => useSection("my-campaigns", dashboardApi.myCampaigns, enabled);

/** Owned controls that lack evidence which still counts. Two reads, one answer. */
function useMyEvidenceGaps(enabled: boolean) {
  const { principal } = useAuth();
  const membershipId = principal?.membership_id ?? "";
  return useSection(
    "my-evidence-gaps",
    async () => {
      const [controls, evidence] = await Promise.all([
        dashboardApi.myControls(membershipId),
        dashboardApi.evidence(),
      ]);
      return evidenceGaps(controls, evidence);
    },
    enabled && membershipId !== "",
  );
}

/** Whether a source this role can read has settled, and what to retry if not. */
function settle(
  enabled: boolean,
  query: { isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown },
) {
  const on = enabled && !isForbidden(query.error);
  return { on, pending: on && query.isPending, failed: on && query.isError, retry: () => void query.refetch() };
}

/**
 * My Day reads four sources at once and shows them as one queue. Each source is
 * fetched on its own; this only reports, for the queue as a whole, whether any
 * is still loading, which failed, and how to try the failed ones again.
 */
export function useMyDay(access: Access) {
  const tasks = useMyTasks(access.tasks);
  const approvals = useMyApprovals(access.documents);
  const campaigns = useMyCampaigns(access.documents);
  const gaps = useMyEvidenceGaps(access.compliance && access.evidence);

  const states = {
    tasks: settle(access.tasks, tasks),
    approvals: settle(access.documents, approvals),
    campaigns: settle(access.documents, campaigns),
    gaps: settle(access.compliance && access.evidence, gaps),
  };
  const active = Object.values(states).filter((source) => source.on);

  return {
    tasks,
    approvals,
    campaigns,
    gaps,
    /** Per source, for the cards that need only some of them. */
    states,
    /** At least one source this role can read. Without one there is nothing to show. */
    hasSources: active.length > 0,
    loading: active.some((source) => source.pending),
    failed: active.some((source) => source.failed),
    retryFailed: () => active.filter((source) => source.failed).forEach((source) => source.retry()),
  };
}
