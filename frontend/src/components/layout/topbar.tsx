import { useNavigate, useLocation } from "react-router-dom";
import {
  Avatar,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
  Tooltip,
} from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { NotificationBell } from "@/features/notifications/components/notification-bell";
import { AcknowledgementsBell } from "@/features/documents/components/acknowledgements-bell";
import { useShellHeader } from "@/components/layout/shell-header";
import { FOOTER_ITEMS, NAV_SECTIONS } from "@/components/layout/nav-config";

/** Fallback title from the active nav item — used on drill-down pages (which
 *  carry their own DetailHeader) so the bar is never blank. A page that renders
 *  <PageHeader> overrides this with its own title. */
function navTitleForPath(pathname: string): string {
  const items = [...NAV_SECTIONS.flatMap((s) => s.items), ...FOOTER_ITEMS];
  const match = items
    .filter((i) => i.to && pathname.startsWith(i.to))
    .sort((a, b) => (b.to?.length ?? 0) - (a.to?.length ?? 0))[0];
  return match?.label ?? "";
}

export function Topbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const { principal, signOut } = useAuth();
  const shell = useShellHeader();

  const title = shell?.title ?? navTitleForPath(location.pathname);

  return (
    <header className="flex shrink-0 flex-col border-b border-border bg-surface-primary">
      {/* Row 1 — module title (left) + global actions (right) */}
      <div className="flex h-topbar items-center gap-3.5 px-5">
        <h1 className="min-w-0 flex-1 truncate font-display text-heading-md text-text-primary">
          {title}
        </h1>

        <Tooltip content="Help & docs arrive in a later phase">
          <button
            type="button"
            aria-label="Help, arrives in a later phase"
            aria-disabled
            className="flex size-9 shrink-0 cursor-not-allowed items-center justify-center rounded-sm border border-border bg-surface-primary"
          >
            <Icon name="help" className="size-4 text-text-subtle" />
          </button>
        </Tooltip>

        <AcknowledgementsBell />
        <NotificationBell />

        <div className="mx-1 h-6 w-px shrink-0 bg-border" />

        <DropdownMenu>
          <Tooltip content="Account">
            <DropdownMenuTrigger asChild>
              <button
                type="button"
                className="flex shrink-0 items-center gap-2 rounded-md p-0.5 transition-colors duration-80 ease-state hover:bg-surface-hover"
                aria-label="User menu"
              >
                <Avatar name={principal?.user.full_name ?? "User"} seed={principal?.user.email} />
                <Icon name="chev" className="size-4 shrink-0 text-text-subtle" />
              </button>
            </DropdownMenuTrigger>
          </Tooltip>
          <DropdownMenuContent align="end">
            <DropdownMenuLabel>{principal?.user.full_name ?? "Account"}</DropdownMenuLabel>
            <DropdownMenuItem onSelect={() => navigate("/settings/security/mfa")}>
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
      </div>

      {/* Row 2 — the module's tab strip portals in here, separated from the
          heading by its own divider (reference layout). `empty:hidden`
          collapses the row — and its border — on pages that have no tabs. */}
      <div ref={shell?.setTabsSlot} className="border-t border-border px-5 empty:hidden" />
    </header>
  );
}
