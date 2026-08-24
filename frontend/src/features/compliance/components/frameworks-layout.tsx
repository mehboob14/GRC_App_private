import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";

/** Scope is a property of the framework you are being audited against, so it
 *  lives inside Frameworks rather than competing with it in the sidebar.
 *
 *  Scope and Coverage were one tab, which put two different jobs on one screen:
 *  Scope is a form you fill in once, Coverage is a report you come back to. */
const TABS = [
  { to: "/frameworks/dashboard", label: "Dashboard", end: false },
  { to: "/frameworks/list", label: "Frameworks", end: false },
  { to: "/frameworks/scope", label: "Scope", end: false },
] as const;

export function FrameworksLayout() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <nav
        className="mb-5 flex gap-1 border-b border-border"
        aria-label="Framework sections"
      >
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              cn(
                "relative -mb-px px-3 py-2.5 text-label-md transition-colors duration-150 ease-state",
                isActive
                  ? "text-action-accent"
                  : "text-text-secondary hover:text-text-primary",
              )
            }
          >
            {({ isActive }) => (
              <>
                {tab.label}
                {isActive ? (
                  <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" />
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
