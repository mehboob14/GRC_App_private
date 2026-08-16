import { NavLink, Outlet } from "react-router-dom";
import { Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import { settingsCategory } from "@/features/iam/components/settings-nav";

/**
 * A settings category page: the category name as the title, its sub-sections as
 * a top tab bar, and the active tab's page below (the Drata "Organization
 * Details → Org info / Key personnel" pattern). Rendered by each category route.
 */
export function SettingsSection({ categoryId }: { categoryId: string }) {
  const category = settingsCategory(categoryId);
  if (!category) return null;

  return (
    <div>
      <h1 className="font-display text-heading-lg text-text-primary">
        {category.label}
      </h1>
      <nav
        className="mb-6 mt-4 flex gap-1 border-b border-border"
        aria-label={`${category.label} sections`}
      >
        {category.tabs.map((tab) =>
          tab.soon ? (
            <Tooltip key={tab.label} content={`${tab.label} arrives in a later phase`}>
              <span className="-mb-px flex cursor-not-allowed items-center gap-1.5 px-3 py-2.5 text-label-md text-text-subtle">
                {tab.label}
                <span className="font-sans text-overline uppercase text-text-subtle">
                  Soon
                </span>
              </span>
            </Tooltip>
          ) : (
            <NavLink
              key={tab.label}
              to={tab.to}
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
          ),
        )}
      </nav>
      <Outlet />
    </div>
  );
}
