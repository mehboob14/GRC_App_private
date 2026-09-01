import { NavLink, Outlet } from "react-router-dom";
import { cn } from "@/lib/cn";

/** Assets is a small workspace: the register is the day-to-day inventory,
 *  Overview is the read on the whole estate. Detail, form and import sit outside
 *  this strip — they are drill-downs, not tabs. */
const TABS = [
  { to: "/assets/overview", label: "Overview", end: false },
  { to: "/assets", label: "Register", end: true },
] as const;

export function AssetsLayout() {
  return (
    <div className="mx-auto max-w-[1200px]">
      <div className="mb-1">
        <p className="type-overline text-text-subtle">Inventory</p>
        <h1 className="mt-1 font-display text-heading-lg text-text-primary">Assets</h1>
      </div>
      <nav className="mb-5 mt-4 flex gap-1 border-b border-border" aria-label="Asset sections">
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
