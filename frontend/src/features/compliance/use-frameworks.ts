import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { workspaceFrameworks, type WorkspaceFramework } from "./frameworks-api";

/** The framework every screen answers for until the workspace picks another. */
export const DEFAULT_FRAMEWORK = "SOC2";

export const WORKSPACE_FRAMEWORKS_KEY = ["workspace-frameworks"] as const;

/** The catalogue as this workspace sees it: each framework and whether it was added. */
export function useWorkspaceFrameworks() {
  return useQuery({
    queryKey: WORKSPACE_FRAMEWORKS_KEY,
    queryFn: workspaceFrameworks,
    staleTime: 60_000,
  });
}

/**
 * The framework a Frameworks screen is about, read from `?framework=CODE` so a
 * link and a refresh keep it, and absent for SOC 2. Read straight from the URL
 * rather than from the workspace list, so a screen can ask the server for the
 * right framework without waiting for the list to load.
 */
export function useFrameworkCode(): string {
  const [params] = useSearchParams();
  return params.get("framework") || DEFAULT_FRAMEWORK;
}

/** Search string that keeps the selection when moving between Frameworks tabs. */
export function frameworkSearch(code: string): string {
  return code && code !== DEFAULT_FRAMEWORK ? `?framework=${encodeURIComponent(code)}` : "";
}

export function useSelectedFramework(): {
  frameworks: WorkspaceFramework[];
  added: WorkspaceFramework[];
  selected: WorkspaceFramework | null;
  code: string;
  select: (code: string) => void;
  isLoading: boolean;
} {
  const query = useWorkspaceFrameworks();
  const [params, setParams] = useSearchParams();
  const code = useFrameworkCode();
  const frameworks = query.data ?? [];
  const added = frameworks.filter((f) => f.added);
  const selected = frameworks.find((f) => f.code === code) ?? null;

  const select = (next: string) => {
    const nextParams = new URLSearchParams(params);
    if (next === DEFAULT_FRAMEWORK) nextParams.delete("framework");
    else nextParams.set("framework", next);
    setParams(nextParams, { replace: true });
  };

  return { frameworks, added, selected, code, select, isLoading: query.isLoading };
}
