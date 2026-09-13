import { useNavigate, useLocation } from "react-router-dom";
import {
  Avatar,
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
  Icon,
} from "@/components/ui";
import { useAuth } from "@/lib/auth/auth-context";
import { NotificationBell } from "@/features/notifications/components/notification-bell";
import { AcknowledgementsBell } from "@/features/documents/components/acknowledgements-bell";
import { useShellHeader } from "@/components/layout/shell-header";
import { FOOTER_ITEMS, NAV_SECTIONS } from "@/components/layout/nav-config";

/** The active nav item. Its label is the fallback title on drill-down pages
 *  (which carry their own DetailHeader) so the bar is never blank, and its icon
 *  is the module icon unless a PageHeader names another. */
function navItemForPath(pathname: string) {
  const items = [...NAV_SECTIONS.flatMap((s) => s.items), ...FOOTER_ITEMS];
  return items
    .filter((i) => i.to && pathname.startsWith(i.to.replace(/\/[^/]+\/[^/]+$/, "")))
    .sort((a, b) => (b.to?.length ?? 0) - (a.to?.length ?? 0))[0];
}

export function Topbar() {
  const location = useLocation();
  const shell = useShellHeader();
  const heading = shell?.heading;
  const navItem = navItemForPath(location.pathname);
  const title = heading?.title ?? navItem?.label ?? "";
  const icon = heading?.icon ?? navItem?.icon;

  return (
    <header className="flex shrink-0 flex-col border-b border-border bg-surface-primary">
      {/* Row 1: the module heading, its own actions, then the global cluster. */}
      <div className="flex h-topbar items-center gap-3 px-5">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          {icon ? (
            <span className="grid size-9 shrink-0 place-items-center rounded-md bg-action-accent-tint text-action-accent">
              <Icon name={icon} className="size-5" />
            </span>
          ) : null}
          <div className="min-w-0">
            <h1 className="truncate font-display text-heading-md text-text-primary">{title}</h1>
            {heading?.subtitle ? (
              <p className="truncate text-caption text-text-subtle">{heading.subtitle}</p>
            ) : null}
          </div>
        </div>

        <div ref={shell?.setActionsSlot} className="flex shrink-0 items-center gap-2 empty:hidden" />

        <div className="ml-2 flex shrink-0 items-center gap-0.5">
          <AcknowledgementsBell />
          <NotificationBell />
        </div>

        <AccountMenu />
      </div>

      {/* Row 2: the module's tab strip portals in here. `empty:hidden`
          collapses the row, and its border, on pages that have no tabs. */}
      <div ref={shell?.setTabsSlot} className="border-t border-border px-5 empty:hidden" />
    </header>
  );
}

/**
 * Who is signed in, in words rather than a bare avatar: name and role on the
 * chip, the email in the menu so a person with two accounts can tell which one
 * this is.
 */
function AccountMenu() {
  const navigate = useNavigate();
  const { principal, signOut } = useAuth();
  const name = principal?.user.full_name ?? "Account";
  const role = principal?.role_names[0] ?? "Member";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`Account menu for ${name}`}
          className="ml-1 flex h-10 shrink-0 items-center gap-2 rounded-full border border-border bg-surface-primary py-1 pl-1 pr-3 transition-colors duration-80 ease-state hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent data-[state=open]:bg-surface-hover"
        >
          <Avatar name={name} seed={principal?.user.email} />
          <span className="hidden min-w-0 text-left md:block">
            <span className="block max-w-[10rem] truncate text-label-sm text-text-primary">
              {name}
            </span>
            <span className="block max-w-[10rem] truncate text-caption text-text-subtle">
              {role}
            </span>
          </span>
          <Icon name="chev" className="size-3.5 text-text-subtle" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-64">
        <div className="flex items-center gap-2.5 px-2.5 py-2">
          <Avatar name={name} seed={principal?.user.email} size="lg" />
          <div className="min-w-0">
            <p className="truncate text-label-md text-text-primary">{name}</p>
            <p className="truncate text-caption text-text-subtle">{principal?.user.email}</p>
          </div>
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => navigate("/settings/security/mfa")}>
          <Icon name="lock" className="size-4 text-text-subtle" />
          Security
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          variant="danger"
          onSelect={() => {
            signOut();
            navigate("/sign-in", { replace: true });
          }}
        >
          <Icon name="signout" className="size-4" />
          Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
