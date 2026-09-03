import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
  Icon,
  identityBgClass,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";
import { resumePendingAuth } from "@/lib/auth/resume-auth";

/** Workspace tile — identity-ramp mark, same vocabulary as person avatars. */
function WorkspaceMark({
  tenantId,
  name,
  className,
}: {
  tenantId: string;
  name: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "flex items-center justify-center rounded-sm font-display font-extrabold",
        identityBgClass(tenantId),
        className,
      )}
    >
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

/**
 * Bottom-of-sidebar workspace switcher. Opens upward (it sits at the bottom of
 * the rail), and owns workspace switching — a switch that needs a further auth
 * step drops the session and hands off to the sign-in surface.
 */
export function WorkspaceSwitcher() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { principal, switchWorkspace, signOut } = useAuth();
  const [switching, setSwitching] = useState(false);

  const workspacesQuery = useQuery({
    queryKey: ["workspaces", principal?.user.id],
    queryFn: () => authApi.listWorkspaces(),
    enabled: Boolean(principal),
  });

  const switchMutation = useMutation({
    mutationFn: (membershipId: string) => {
      setSwitching(true);
      return switchWorkspace(membershipId);
    },
    onSuccess: async (response) => {
      if (response.status === "authenticated") {
        await queryClient.invalidateQueries();
        return;
      }
      signOut();
      resumePendingAuth(response, navigate);
    },
    onSettled: () => setSwitching(false),
  });

  const workspaces = workspacesQuery.data ?? [];
  const activeName = principal?.tenant_name ?? "Workspace";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex w-full items-center gap-2 rounded-md border border-border bg-surface-sunken px-2 py-2 text-left transition-colors duration-80 ease-state hover:bg-surface-hover"
          aria-label="Switch workspace"
          disabled={switching}
        >
          <WorkspaceMark
            tenantId={principal?.tenant_id ?? activeName}
            name={activeName}
            className="size-7 shrink-0 text-body-sm"
          />
          <span className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-label-sm font-bold text-text-primary">{activeName}</span>
            <span className="truncate text-caption text-text-subtle">
              {principal?.role_names[0] ?? "Member"}
            </span>
          </span>
          <Icon name="chev" className="size-4 shrink-0 text-text-subtle" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent side="top" align="start" sideOffset={8} className="w-[248px]">
        <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
        {workspaces.map((ws) => {
          const active = ws.membership_id === principal?.membership_id;
          return (
            <DropdownMenuItem
              key={ws.membership_id}
              disabled={switching}
              aria-current={active || undefined}
              onSelect={() => {
                if (!active) switchMutation.mutate(ws.membership_id);
              }}
              className="h-auto py-1.5"
            >
              <WorkspaceMark tenantId={ws.tenant_id} name={ws.tenant_name} className="size-7 text-caption" />
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="truncate text-body-md font-semibold">{ws.tenant_name}</span>
                <span className="text-caption text-text-subtle">{ws.role_name}</span>
              </span>
              {active ? (
                <Icon name="check" aria-label="Current workspace" className="size-4 shrink-0 text-action-accent" />
              ) : null}
            </DropdownMenuItem>
          );
        })}
        {workspaces.length > 1 ? (
          <p className="px-2.5 pb-1 pt-1.5 text-caption text-text-subtle">
            Signed in across <span className="tabular">{workspaces.length}</span> workspaces. Switching is audited
          </p>
        ) : null}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
