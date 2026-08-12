import { Link, NavLink, useLocation } from "react-router-dom";
import { Avatar, Badge, Button, Icon, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import {
  FOOTER_ITEMS,
  NAV_SECTIONS,
  RAIL_ITEMS,
  type NavItem,
} from "@/components/layout/nav-config";
import { ThemeToggle } from "@/components/layout/theme-toggle";

type SidebarProps = {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

const NAV_ROW =
  "flex h-8 w-full items-center gap-2.5 rounded-sm px-2.5 text-left transition-colors duration-80 ease-state";

function NavRow({ item, active }: { item: NavItem; active?: boolean }) {
  // Later-phase module: keyboard-reachable but explicitly not enabled —
  // aria-disabled (not `disabled`) so the tooltip still shows on focus/hover.
  if (item.comingSoon || !item.to) {
    return (
      <Tooltip content={`${item.label} arrives in a later phase`} side="right">
        <button
          type="button"
          aria-disabled
          className={cn(NAV_ROW, "cursor-not-allowed")}
        >
          <Icon
            name={item.icon}
            className="size-4 text-text-secondary opacity-60"
          />
          <span className="min-w-0 flex-1 truncate text-label-sm text-text-secondary opacity-70">
            {item.label}
          </span>
          <span className="font-sans text-overline uppercase text-text-subtle">
            Soon
          </span>
        </button>
      </Tooltip>
    );
  }

  return (
    <NavLink
      to={item.to}
      aria-current={active ? "page" : undefined}
      className={cn(NAV_ROW, active ? "bg-action-accent-tint" : "hover:bg-surface-hover")}
    >
      <Icon
        name={item.icon}
        className={cn("size-4", active ? "text-action-accent" : "text-text-secondary")}
      />
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-label-sm",
          active ? "text-action-accent" : "text-text-secondary",
        )}
      >
        {item.label}
      </span>
      {item.count != null ? (
        <Badge variant={item.countTone === "review" ? "countWarn" : "count"}>
          {item.count}
        </Badge>
      ) : null}
    </NavLink>
  );
}

export function Sidebar({ collapsed = false, onToggleCollapsed }: SidebarProps) {
  const location = useLocation();
  const { principal } = useAuth();
  const settingsActive = location.pathname.startsWith("/settings");

  return (
    <aside
      className={cn(
        "flex h-full shrink-0 border-r border-border bg-surface-primary",
        collapsed ? "w-12" : "w-sidebar",
      )}
      aria-label="Primary"
    >
      {/* Icon rail — Figma Sidebar Rail 48px. Items link to their section's
          first live route; later-phase sections are explicit about it. */}
      <div className="flex w-12 shrink-0 flex-col items-center justify-between border-r border-border bg-surface-page px-2 py-2.5">
        <div className="flex flex-col items-center gap-1.5">
          <div className="flex size-8 items-center justify-center rounded-md bg-action-primary text-action-primary-fg">
            <Icon name="check" className="size-4" aria-hidden />
          </div>
          <div className="h-px w-6 bg-border" />
          {RAIL_ITEMS.map((item) =>
            item.to ? (
              <Tooltip key={item.id} content={item.label} side="right">
                <NavLink
                  to={item.to}
                  aria-label={item.label}
                  className={({ isActive }) =>
                    cn(
                      "flex size-8 items-center justify-center rounded-sm text-text-secondary transition-colors duration-80 ease-state hover:bg-surface-primary hover:text-text-primary",
                      isActive && "bg-surface-primary text-action-accent",
                    )
                  }
                >
                  <Icon name={item.icon} className="size-4" />
                </NavLink>
              </Tooltip>
            ) : (
              <Tooltip
                key={item.id}
                content={`${item.label} arrives in a later phase`}
                side="right"
              >
                <button
                  type="button"
                  aria-label={`${item.label} — arrives in a later phase`}
                  aria-disabled
                  className="flex size-8 cursor-not-allowed items-center justify-center rounded-sm text-text-subtle"
                >
                  <Icon name={item.icon} className="size-4" />
                </button>
              </Tooltip>
            ),
          )}
        </div>
        <div className="flex flex-col items-center gap-1">
          <Tooltip content="Settings" side="right">
            <Link
              to="/settings/security"
              aria-label="Settings"
              className={cn(
                "flex size-8 items-center justify-center rounded-sm text-text-secondary transition-colors duration-80 ease-state hover:bg-surface-primary hover:text-text-primary",
                settingsActive && "bg-surface-primary text-action-accent",
              )}
            >
              <Icon name="gear" className="size-4" />
            </Link>
          </Tooltip>
          <Tooltip content={collapsed ? "Expand sidebar" : "Collapse sidebar"} side="right">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={onToggleCollapsed}
            >
              <Icon name="chevr" className={cn("size-4", !collapsed && "rotate-180")} />
            </Button>
          </Tooltip>
        </div>
      </div>

      {!collapsed ? (
        <div className="flex min-w-0 flex-1 flex-col px-3 pb-3 pt-4">
          <div className="mb-4 flex items-center gap-2.5 px-2 pt-1">
            <div className="flex size-8 items-center justify-center rounded-md bg-action-primary text-action-primary-fg">
              <Icon name="check" className="size-[18px]" aria-hidden />
            </div>
            <span className="font-display text-heading-sm text-text-primary">
              Verity
            </span>
            <span className="ml-auto rounded-xs border border-border px-1.5 py-0.5 font-sans text-overline uppercase text-text-subtle">
              GRC
            </span>
          </div>

          <nav className="min-h-0 flex-1 overflow-y-auto" aria-label="Modules">
            {NAV_SECTIONS.map((section) => (
              <div key={section.id} className="mb-1">
                <div className="px-2.5 pb-1.5 pt-3">
                  <p className="type-overline">{section.label}</p>
                </div>
                <div className="flex flex-col gap-0.5">
                  {section.items.map((item) => (
                    <NavRow
                      key={item.id}
                      item={item}
                      active={item.to ? location.pathname.startsWith(item.to) : false}
                    />
                  ))}
                </div>
              </div>
            ))}
          </nav>

          <div className="mt-2 border-t border-border pt-2">
            {FOOTER_ITEMS.map((item) => (
              <NavRow
                key={item.id}
                item={item}
                active={item.id === "settings" ? settingsActive : false}
              />
            ))}
            <div className="mt-2 flex items-center gap-1.5">
              {/* Identity display only — account actions live in the topbar
                  user menu, so this is not a (dead) button. */}
              <div className="flex min-w-0 flex-1 items-center gap-2 rounded-md border border-border bg-surface-sunken px-2 py-2">
                <Avatar
                  name={principal?.user.full_name ?? "User"}
                  seed={principal?.user.email}
                  size="md"
                />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-label-sm text-text-primary">
                    {principal?.user.full_name ?? "User"}
                  </span>
                  <span className="block truncate text-caption text-text-subtle">
                    {principal?.role_names[0] ?? "Member"}
                  </span>
                </span>
              </div>
              <ThemeToggle />
            </div>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
