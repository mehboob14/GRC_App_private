import { NavLink, useLocation } from "react-router-dom";
import { Avatar, Badge, Icon, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import {
  FOOTER_ITEMS,
  NAV_SECTIONS,
  type NavItem,
} from "@/components/layout/nav-config";
import { ThemeToggle } from "@/components/layout/theme-toggle";

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

export function Sidebar() {
  const location = useLocation();
  const { principal } = useAuth();
  const settingsActive = location.pathname.startsWith("/settings");

  return (
    <aside
      className="flex h-full w-sidebar shrink-0 flex-col border-r border-border bg-surface-primary px-3 pb-3 pt-4"
      aria-label="Primary"
    >
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
                  active={
                    item.to ? location.pathname.startsWith(item.to) : false
                  }
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
            active={
              item.id === "settings"
                ? settingsActive
                : item.to
                  ? location.pathname.startsWith(item.to)
                  : false
            }
          />
        ))}
        <div className="mt-2 flex items-center gap-1.5">
          {/* Identity display only — account actions live in the topbar user
              menu, so this is not a (dead) button. */}
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
    </aside>
  );
}
