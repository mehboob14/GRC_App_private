import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useState } from "react";
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
  SearchInput,
} from "@/components/ui";
import { authApi } from "@/lib/api/endpoints";
import { useAuth } from "@/lib/auth/auth-context";

export function Topbar() {
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
    mutationFn: async (membershipId: string) => {
      setSwitching(true);
      await switchWorkspace(membershipId);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries();
    },
    onSettled: () => setSwitching(false),
  });

  const activeName = principal?.tenant_name ?? "Workspace";
  const mark = activeName.slice(0, 1).toUpperCase();

  return (
    <header className="flex h-topbar shrink-0 items-center gap-3.5 border-b border-border bg-bg-elevated px-5">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2.5 rounded-lg border border-border py-[5px] pl-1.5 pr-2.5 hover:bg-bg-sunken"
            aria-label="Switch workspace"
            disabled={switching}
          >
            <span className="flex size-[26px] items-center justify-center rounded-md bg-accent font-display text-body-sm font-extrabold text-accent-fg">
              {mark}
            </span>
            <span className="flex flex-col items-start">
              <span className="text-label-md font-bold text-text">
                {activeName}
              </span>
              <span className="text-caption text-text-faint">
                {principal?.role_names[0] ?? "Member"}
              </span>
            </span>
            <Icon name="chev" className="size-[15px] text-text-faint" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          {(workspacesQuery.data ?? []).map((ws) => {
            const active = ws.membership_id === principal?.membership_id;
            return (
              <DropdownMenuItem
                key={ws.membership_id}
                disabled={active || switching}
                onSelect={() => {
                  if (!active) switchMutation.mutate(ws.membership_id);
                }}
              >
                <span className="flex size-7 items-center justify-center rounded-md bg-accent text-caption font-extrabold text-accent-fg">
                  {ws.tenant_name.slice(0, 1)}
                </span>
                <span className="flex flex-col">
                  <span className="text-body-md font-semibold">
                    {ws.tenant_name}
                  </span>
                  <span className="text-caption text-text-faint">
                    {ws.role_name}
                    {active ? " · current" : ""}
                  </span>
                </span>
              </DropdownMenuItem>
            );
          })}
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled>Manage workspaces — soon</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <SearchInput
        className="max-w-[460px] flex-1"
        placeholder="Search controls, evidence, risks, vendors…"
        shortcut="⌘K"
        readOnly
        aria-label="Global search"
      />

      <div className="flex-1" />

      <Button variant="secondary" size="icon" aria-label="Help">
        <Icon name="help" className="size-[17px] text-text-muted" />
      </Button>

      <div className="relative">
        <Button variant="secondary" size="icon" aria-label="Notifications">
          <Icon name="bell" className="size-[17px] text-text-muted" />
        </Button>
        <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full border-2 border-bg-elevated bg-fail text-overline text-text-inverse">
          3
        </span>
      </div>

      <div className="mx-1 h-6 w-px bg-border" />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2 rounded-lg p-0.5 hover:bg-bg-sunken"
            aria-label="User menu"
          >
            <Avatar
              name={principal?.user.full_name ?? "User"}
              seed={principal?.user.email}
            />
            <Icon name="chev" className="size-[15px] text-text-faint" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>
            {principal?.user.full_name ?? "Account"}
          </DropdownMenuLabel>
          <DropdownMenuItem disabled>Profile</DropdownMenuItem>
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
