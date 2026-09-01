import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";

/** Tasks is a small workspace of its own: the register is the day-to-day view,
 *  Overview is the read on the whole queue, Settings holds the SLA matrix and
 *  templates. Detail sits outside this strip — it is a drill-down, not a tab. */
const TABS = [
  { to: "/tasks/overview", label: "Overview", end: false },
  { to: "/tasks", label: "Register", end: true },
  { to: "/tasks/settings", label: "Settings", end: false },
] as const;

export function TasksLayout() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-1">
        <p className="type-overline text-text-subtle">Operations</p>
        <h1 className="mt-1 font-display text-heading-lg text-text-primary">Tasks &amp; issues</h1>
      </div>
      <nav className="mb-5 mt-4 flex gap-1 border-b border-border" aria-label="Task sections">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              cn(
                "relative -mb-px px-3 py-2.5 text-label-md transition-colors duration-150 ease-state",
                isActive ? "text-action-accent" : "text-text-secondary hover:text-text-primary",
              )
            }
          >
            {({ isActive }) => (
              <>
                {tab.label}
                {isActive ? <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" /> : null}
              </>
            )}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  );
}
