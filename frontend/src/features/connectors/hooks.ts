import { useEffect, useRef, useState } from "react";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from "@tanstack/react-query";
import { useToast } from "@/components/ui";
import { errorToast } from "@/lib/api/describe-error";
import {
  connectorKeys,
  getAutomation,
  getControlComposition,
  getRequirementChain,
  listConnections,
  runConnection,
} from "./api";

/** A run is collected in the background, so the page polls until it lands. */
const POLL_MS = 2000;
/** How long a click keeps polling before the run row itself says "running". */
const GRACE_MS = 15_000;

export function refreshAutomation(queryClient: QueryClient) {
  void queryClient.invalidateQueries({ queryKey: connectorKeys.connections });
  void queryClient.invalidateQueries({ queryKey: ["control-automation"] });
  void queryClient.invalidateQueries({ queryKey: connectorKeys.composition });
  void queryClient.invalidateQueries({ queryKey: ["requirement-chain"] });
  void queryClient.invalidateQueries({ queryKey: ["evidence"] });
}

/** What evidences every control: the register's "Evidenced by" column. */
export function useControlComposition(enabled = true) {
  return useQuery({
    queryKey: connectorKeys.composition,
    queryFn: getControlComposition,
    enabled,
    staleTime: 60_000,
  });
}

/** A criterion, its controls, and what evidences each. */
export function useRequirementChain(requirementId: string | null) {
  return useQuery({
    queryKey: connectorKeys.chain(requirementId ?? ""),
    queryFn: () => getRequirementChain(requirementId!),
    enabled: requirementId !== null,
  });
}

export function useAutomation(controlId: string) {
  const [kickedAt, setKickedAt] = useState(0);
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: connectorKeys.automation(controlId),
    queryFn: () => getAutomation(controlId),
    enabled: controlId.length > 0,
    refetchInterval: (q) =>
      q.state.data?.running || Date.now() - kickedAt < GRACE_MS
        ? POLL_MS
        : false,
  });
  // A run files its evidence as it lands, so a result newer than the one this page
  // already holds means the evidence list beside it is out of date too.
  const lastRun = query.data ? (query.data.last_run_at ?? "never") : undefined;
  const seen = useRef(lastRun);
  useEffect(() => {
    if (seen.current !== undefined && lastRun !== undefined && seen.current !== lastRun) {
      void queryClient.invalidateQueries({ queryKey: ["evidence"] });
    }
    seen.current = lastRun;
  }, [lastRun, queryClient]);
  return { ...query, kick: () => setKickedAt(Date.now()) };
}

export function useConnections(enabled = true) {
  const [kickedAt, setKickedAt] = useState(0);
  const query = useQuery({
    queryKey: connectorKeys.connections,
    queryFn: listConnections,
    enabled,
    refetchInterval: (q) =>
      q.state.data?.some((c) => c.latest_run?.status === "running") ||
      Date.now() - kickedAt < GRACE_MS
        ? POLL_MS
        : false,
  });
  return { ...query, kick: () => setKickedAt(Date.now()) };
}

/** Start a run on each connection; `onStarted` begins the polling. */
export function useRunConnections(onStarted: () => void) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  return useMutation({
    mutationFn: (ids: string[]) => Promise.all(ids.map(runConnection)),
    onSuccess: () => {
      onStarted();
      refreshAutomation(queryClient);
      toast({ title: "Run started", tone: "success" });
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "connection"), tone: "danger" }),
  });
}
