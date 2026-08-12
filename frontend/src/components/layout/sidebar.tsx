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

type SidebarProps = {
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
};

function NavRow({ item, active }: { item: NavItem; active?: boolean }) {
  const content = (
    <>
      <Icon
        name={item.icon}
        className={cn(
          "size-[17px]",
          active ? "text-accent" : "text-text-muted",
          item.comingSoon && "opacity-60",
        )}
      />
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-[12.5px] leading-[12.5px]",
          active
            ? "font-semibold text-accent"
            : "font-medium text-text-muted",
          item.comingSoon && "opacity-70",
        )}
      >
        {item.label}
      </span>
      {item.count != null ? (
        <Badge variant={item.countTone === "review" ? "countWarn" : "count"}>
          {item.count}
        </Badge>
      ) : null}
      {item.comingSoon && !item.count ? (
        <span className="text-[9px] font-bold uppercase tracking-wide text-text-faint">
          Soon
        </span>
      ) : null}
    </>
  );

  const className = cn(
    "flex w-full items-center gap-2.5 rounded-md px-2.5 py-[7px] text-left transition-colors",
    active ? "bg-accent-tint" : "hover:bg-bg-sunken",
    item.comingSoon && "cursor-not-allowed",
  );

  if (item.comingSoon || !item.to) {
    return (
      <Tooltip content={`${item.label} — coming soon`} side="right">
        <button type="button" className={className} aria-disabled disabled>
          {content}
        </button>
      </Tooltip>
    );
  }

  return (
    <NavLink
      to={item.to}
      className={({ isActive }) =>
        cn(
          className,
          isActive && "bg-accent-tint",
        )
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            name={item.icon}
            className={cn(
              "size-[17px]",
              isActive || active ? "text-accent" : "text-text-muted",
            )}
          />
          <span
            className={cn(
              "min-w-0 flex-1 truncate text-[12.5px] leading-[12.5px]",
              isActive || active
                ? "font-semibold text-accent"
                : "font-medium text-text-muted",
            )}
          >
            {item.label}
          </span>
        </>
      )}
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
        "flex h-full shrink-0 border-r border-border bg-bg-elevated",
        collapsed ? "w-12" : "w-sidebar",
      )}
      aria-label="Primary"
    >
      {/* Icon rail — Figma Sidebar Rail 48px */}
      <div className="flex w-12 shrink-0 flex-col items-center justify-between border-r border-border bg-bg px-2 py-2.5">
        <div className="flex flex-col items-center gap-1.5">
          <div className="flex size-[30px] items-center justify-center rounded-lg bg-accent text-accent-fg shadow-mark">
            <Icon name="check" className="size-[17px]" aria-hidden />
          </div>
          <div className="h-px w-6 bg-border" />
          {RAIL_ITEMS.map((item) => (
            <Tooltip key={item.id} content={item.label} side="right">
              <button
                type="button"
                aria-label={item.label}
                className="relative flex size-8 items-center justify-center rounded-md text-text-muted hover:bg-bg-elevated hover:text-text"
              >
                <Icon name={item.icon} className="size-[17px]" />
                {item.dot ? (
                  <span className="absolute right-1.5 top-1.5 size-1.5 rounded-full bg-fail" />
                ) : null}
              </button>
            </Tooltip>
          ))}
        </div>
        <div className="flex flex-col items-center gap-1">
          <Tooltip content="Settings" side="right">
            <Link
              to="/settings/security"
              aria-label="Settings"
              className={cn(
                "flex size-8 items-center justify-center rounded-md text-text-muted hover:bg-bg-elevated hover:text-text",
                settingsActive && "bg-bg-elevated text-accent",
              )}
            >
              <Icon name="gear" className="size-[17px]" />
            </Link>
          </Tooltip>
          <Tooltip content={collapsed ? "Expand sidebar" : "Collapse sidebar"} side="right">
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={onToggleCollapsed}
            >
              <Icon name="chevr" className={cn("size-[17px]", !collapsed && "rotate-180")} />
            </Button>
          </Tooltip>
        </div>
      </div>

      {!collapsed ? (
        <div className="flex min-w-0 flex-1 flex-col px-3 pb-3 pt-[15px]">
          <div className="mb-4 flex items-center gap-2.5 px-2 pt-1">
            <div className="flex size-[30px] items-center justify-center rounded-lg bg-accent text-accent-fg shadow-mark">
              <Icon name="check" className="size-[18px]" aria-hidden />
            </div>
            <span className="font-display text-[18px] font-extrabold tracking-[-0.36px] text-text">
              Verity
            </span>
            <span className="ml-auto rounded-sm border border-border px-[5px] py-0.5 text-[9px] font-bold tracking-[0.36px] text-text-faint">
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
            <button
              type="button"
              className="mt-2 flex w-full items-center gap-2 rounded-lg border border-border bg-bg-sunken px-2 py-2 text-left hover:bg-bg"
            >
              <Avatar
                name={principal?.user.full_name ?? "User"}
                seed={principal?.user.email}
                size="md"
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[12.5px] font-semibold text-text">
                  {principal?.user.full_name ?? "User"}
                </span>
                <span className="block truncate text-[10px] text-text-faint">
                  {(principal?.role_names[0] ?? "Member") === "Admin"
                    ? "Security Lead · Admin"
                    : principal?.role_names[0] ?? "Member"}
                </span>
              </span>
              <Icon name="chev" className="size-[15px] text-text-faint" />
            </button>
          </div>
        </div>
      ) : null}
    </aside>
  );
}
