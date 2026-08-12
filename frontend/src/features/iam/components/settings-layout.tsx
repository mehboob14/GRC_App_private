import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";

const TABS = [
  { to: "/settings/groups", label: "Groups" },
  { to: "/settings/roles", label: "Roles & permissions" },
  { to: "/settings/security", label: "Security" },
] as const;

export function SettingsLayout() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <nav
        className="mb-5 flex gap-1 border-b border-border"
        aria-label="Settings sections"
      >
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                "relative -mb-px px-3 py-2.5 text-[13px] font-medium text-text-muted hover:text-text",
                isActive && "text-accent",
              )
            }
          >
            {({ isActive }) => (
              <>
                {tab.label}
                {isActive ? (
                  <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-accent" />
                ) : null}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
