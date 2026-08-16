import { NavLink, Outlet } from "react-router-dom";
import { Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  SETTINGS_AUDIT,
  SETTINGS_CATEGORIES,
} from "@/features/iam/components/settings-nav";

const ROW =
  "flex h-8 w-full items-center gap-2.5 rounded-sm px-2.5 text-left text-label-sm transition-colors duration-80 ease-state";

export function SettingsLayout() {
  return (
    <div className="flex gap-8">
      <aside className="w-56 shrink-0" aria-label="Settings sections">
        <h1 className="mb-5 px-2.5 font-display text-heading-md text-text-primary">
          Settings
        </h1>
        <div className="flex flex-col gap-0.5">
          {SETTINGS_CATEGORIES.map((category) => (
            <NavLink
              key={category.id}
              to={category.to}
              className={({ isActive }) =>
                cn(ROW, isActive ? "bg-action-accent-tint" : "hover:bg-surface-hover")
              }
            >
              {({ isActive }) => (
                <>
                  <Icon
                    name={category.icon}
                    className={cn(
                      "size-4",
                      isActive ? "text-action-accent" : "text-text-secondary",
                    )}
                  />
                  <span
                    className={cn(
                      "min-w-0 flex-1 truncate",
                      isActive ? "text-action-accent" : "text-text-secondary",
                    )}
                  >
                    {category.label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </div>

        <div className="mt-3 border-t border-border pt-3">
          <NavLink
            to={SETTINGS_AUDIT.to}
            className={({ isActive }) =>
              cn(ROW, isActive ? "bg-action-accent-tint" : "hover:bg-surface-hover")
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  name={SETTINGS_AUDIT.icon}
                  className={cn(
                    "size-4",
                    isActive ? "text-action-accent" : "text-text-secondary",
                  )}
                />
                <span
                  className={cn(
                    "min-w-0 flex-1 truncate",
                    isActive ? "text-action-accent" : "text-text-secondary",
                  )}
                >
                  {SETTINGS_AUDIT.label}
                </span>
              </>
            )}
          </NavLink>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
