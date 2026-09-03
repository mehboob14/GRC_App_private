import { NavLink, Outlet } from "react-router-dom";
import { Icon, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { IconName } from "@/components/ui/icon";

const ROW =
  "flex h-8 w-full items-center gap-2.5 rounded-sm px-2.5 text-left text-label-sm transition-colors duration-80 ease-state";

// Manage-accounts surfaces land with the connector sync backend;
// listed for orientation, disabled until then.
const MANAGE: { label: string; icon: IconName }[] = [
  { label: "Access Reviews", icon: "audit" },
  { label: "Devices", icon: "box" },
  { label: "Infrastructure", icon: "grid" },
];

export function ConnectionsLayout() {
  return (
    <div className="flex gap-8">
      <aside className="w-56 shrink-0" aria-label="Connections navigation">
        {/* The page itself carries the h1; the rail only names the group, so it
            sits a rank below rather than repeating the title at heading size. */}
        <p className="mb-5 px-2.5 text-label-md text-text-secondary">
          Connections
        </p>
        <div className="flex flex-col gap-0.5">
          <NavLink
            to="/connectors"
            end
            className={({ isActive }) =>
              cn(ROW, isActive ? "bg-action-accent-tint" : "hover:bg-surface-hover")
            }
          >
            {({ isActive }) => (
              <>
                <Icon
                  name="plug"
                  className={cn("size-4", isActive ? "text-action-accent" : "text-text-secondary")}
                />
                <span
                  className={cn(
                    "min-w-0 flex-1 truncate",
                    isActive ? "text-action-accent" : "text-text-secondary",
                  )}
                >
                  All connections
                </span>
              </>
            )}
          </NavLink>
        </div>

        <div className="mt-5">
          <p className="mb-1.5 px-2.5 type-overline">Manage Accounts</p>
          <div className="flex flex-col gap-0.5">
            {MANAGE.map((item) => (
              <Tooltip
                key={item.label}
                content={`${item.label} arrives in a later phase`}
                side="right"
              >
                <button type="button" aria-disabled className={cn(ROW, "cursor-not-allowed")}>
                  <Icon name={item.icon} className="size-4 text-text-secondary opacity-60" />
                  <span className="min-w-0 flex-1 truncate text-text-secondary opacity-70">
                    {item.label}
                  </span>
                  <span className="type-overline">Soon</span>
                </button>
              </Tooltip>
            ))}
          </div>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
