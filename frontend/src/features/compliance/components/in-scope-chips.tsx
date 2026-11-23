import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";

/** Frameworks a scope item puts this asset, vendor or group in scope for (SC-4). */
function useInScopeFor(refType: "asset" | "vendor" | "group") {
  const { principal } = useAuth();
  return useQuery({
    queryKey: ["in-scope-for", principal?.tenant_id, refType],
    queryFn: () => apiFetch<Record<string, string[]>>(`/engagement/in-scope-for?ref_type=${refType}`),
    enabled: hasPermission(principal, "frameworks:read"),
    staleTime: 60_000,
  });
}

const NAME: Record<string, string> = { SOC2: "SOC 2", ISO27001: "ISO 27001" };

export function InScopeChips({ refType, id }: { refType: "asset" | "vendor" | "group"; id: string }) {
  const codes = useInScopeFor(refType).data?.[id] ?? [];
  if (!codes.length) return null;
  return (
    <span className="inline-flex flex-wrap items-center gap-1 text-caption text-text-secondary">
      In scope for
      {codes.map((c) => (
        <span key={c} className="rounded-sm bg-surface-sunken px-1.5 py-px text-text-primary">
          {NAME[c] ?? c}
        </span>
      ))}
    </span>
  );
}
