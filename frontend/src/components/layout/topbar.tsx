import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import {
  Avatar,
  Button,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
  identityBgClass,
  SearchInput,
  Tooltip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

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
        "flex items-center justify-center rounded-sm font-display font-extrabold text-text-inverse",
        identityBgClass(tenantId),
        className,
      )}
    >
      {name.slice(0, 1).toUpperCase()}
    </span>
  );
}

export function Topbar() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { principal, switchWorkspace, signOut } = useAuth();
  const [switching, setSwitching] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);

  // ⌘K / Ctrl+K focuses global search. The full command palette is a later
  // phase; the shortcut contract starts now so the reflex carries over.
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        searchRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

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
        // New session applied in place — refresh all workspace-scoped data.
        await queryClient.invalidateQueries();
        return;
      }
      // The target workspace needs another auth step (Admin memberships
      // require MFA). Those steps live on PublicOnly routes, and the current
      // session isn't valid for the target — so drop it and hand off to the
      // sign-in surface, which owns the challenge / enrollment / choice UI.
      signOut();
      if (response.status === "mfa_enrollment_required") {
        navigate(`/mfa/enroll?challenge=${response.challenge_token}`, {
          replace: true,
        });
      } else {
        // mfa_required carries a challenge_token; select_workspace a
        // selection_token — the sign-in page resumes either from nav state.
        navigate("/sign-in", { replace: true, state: { pending: response } });
      }
    },
    onSettled: () => setSwitching(false),
  });

  const workspaces = workspacesQuery.data ?? [];
  const activeName = principal?.tenant_name ?? "Workspace";

  return (
    <header className="flex h-topbar shrink-0 items-center gap-3.5 border-b border-border bg-surface-primary px-5">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2.5 rounded-md border border-border py-1 pl-1.5 pr-2.5 transition-colors duration-80 ease-state hover:bg-surface-hover"
            aria-label="Switch workspace"
            disabled={switching}
          >
            <WorkspaceMark
              tenantId={principal?.tenant_id ?? activeName}
              name={activeName}
              className="size-7 text-body-sm"
            />
            <span className="flex flex-col items-start">
              <span className="text-label-md font-bold text-text-primary">
                {activeName}
              </span>
              <span className="text-caption text-text-subtle">
                {principal?.role_names[0] ?? "Member"}
              </span>
            </span>
            <Icon name="chev" className="size-4 text-text-subtle" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
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
                <WorkspaceMark
                  tenantId={ws.tenant_id}
                  name={ws.tenant_name}
                  className="size-7 text-caption"
                />
                <span className="flex min-w-0 flex-1 flex-col">
                  <span className="truncate text-body-md font-semibold">
                    {ws.tenant_name}
                  </span>
                  <span className="text-caption text-text-subtle">
                    {ws.role_name}
                  </span>
                </span>
                {active ? (
                  <Icon
                    name="check"
                    aria-label="Current workspace"
                    className="size-4 shrink-0 text-action-accent"
                  />
                ) : null}
              </DropdownMenuItem>
            );
          })}
          {workspaces.length > 1 ? (
            <p className="px-2.5 pb-1 pt-1.5 text-caption text-text-subtle">
              Signed in across{" "}
              <span className="tabular">{workspaces.length}</span> workspaces —
              switching is audited
            </p>
          ) : null}
        </DropdownMenuContent>
      </DropdownMenu>

      <SearchInput
        ref={searchRef}
        className="max-w-[460px] flex-1"
        placeholder="Search controls, evidence, risks, vendors…"
        shortcut="⌘K"
        readOnly
        aria-label="Global search"
        title="Search arrives with the compliance modules — ⌘K already focuses it"
      />

      <div className="flex-1" />

      {/* Docs are a later phase — same honest affordance as the sidebar. */}
      <Tooltip content="Help & docs arrive in a later phase">
        <button
          type="button"
          aria-label="Help — arrives in a later phase"
          aria-disabled
          className="flex size-9 cursor-not-allowed items-center justify-center rounded-sm border border-border bg-surface-primary"
        >
          <Icon name="help" className="size-4 text-text-subtle" />
        </button>
      </Tooltip>

      {/* Notifications ship in a later phase: no fake badge — an honest,
          empty popover (§7.2 bell + popover channel). */}
      <DropdownMenu>
        <Tooltip content="Notifications">
          <DropdownMenuTrigger asChild>
            <Button variant="secondary" size="icon" aria-label="Notifications">
              <Icon name="bell" className="size-4 text-text-secondary" />
            </Button>
          </DropdownMenuTrigger>
        </Tooltip>
        <DropdownMenuContent align="end" className="w-[320px]">
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          <div className="flex flex-col items-center px-4 pb-4 pt-3 text-center">
            <span className="flex size-10 items-center justify-center rounded-md bg-surface-hover">
              <Icon name="bell" className="size-5 text-text-subtle" />
            </span>
            <p className="mt-2 font-display text-title-sm text-text-primary">
              Nothing here yet
            </p>
            <p className="mt-1 text-body-sm text-text-subtle">
              Alerts on failing checks and expiring evidence arrive with the
              notifications module in a later phase.
            </p>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      <div className="mx-1 h-6 w-px bg-border" />

      <DropdownMenu>
        <Tooltip content="Account">
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="flex items-center gap-2 rounded-md p-0.5 transition-colors duration-80 ease-state hover:bg-surface-hover"
              aria-label="User menu"
            >
              <Avatar
                name={principal?.user.full_name ?? "User"}
                seed={principal?.user.email}
              />
              <Icon name="chev" className="size-4 text-text-subtle" />
            </button>
          </DropdownMenuTrigger>
        </Tooltip>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>
            {principal?.user.full_name ?? "Account"}
          </DropdownMenuLabel>
          <DropdownMenuItem onSelect={() => navigate("/settings/security")}>
            Security
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            onSelect={() => {
              signOut();
              navigate("/sign-in", { replace: true });
            }}
          >
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
