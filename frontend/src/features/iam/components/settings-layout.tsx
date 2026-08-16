import { NavLink, Outlet } from "react-router-dom";
import { Icon, Tooltip } from "@/components/ui";
import type { IconName } from "@/components/ui/icon";
import { cn } from "@/lib/cn";

type SettingsItem = { label: string; icon: IconName; to?: string; soon?: boolean };
type SettingsGroup = { label: string; items: SettingsItem[] };

// Access and security are one area (the screenshot): who can get in, and how.
// Organization is the company profile; Integrations are later-phase config.
const GROUPS: SettingsGroup[] = [
  {
    label: "Access & Security",
    items: [
      { label: "People", icon: "users", to: "/settings/people" },
      { label: "Groups", icon: "users", to: "/settings/groups" },
      { label: "Roles & Permissions", icon: "shield", to: "/settings/roles" },
      { label: "Authentication", icon: "shield", soon: true },
      { label: "SSO", icon: "globe", soon: true },
      { label: "MFA", icon: "shield", to: "/settings/security" },
    ],
  },
  {
    label: "Organization",
    items: [{ label: "Company", icon: "grid", to: "/settings/company" }],
  },
  {
    label: "Integrations",
    items: [
      { label: "Integrations", icon: "plug", soon: true },
      { label: "API Keys", icon: "gear", soon: true },
      { label: "Webhooks", icon: "activity", soon: true },
    ],
  },
];

// Audit log lives in the main nav too, but a settings-side entry matches the
// requested tree; it links out to the same page.
const AUDIT_ITEM: SettingsItem = { label: "Audit Log", icon: "doc", to: "/audit-log" };

const ROW =
  "flex h-8 w-full items-center gap-2.5 rounded-sm px-2.5 text-left text-label-sm transition-colors duration-80 ease-state";

function SettingsNavRow({ item }: { item: SettingsItem }) {
  if (item.soon || !item.to) {
    return (
      <Tooltip content={`${item.label} arrives in a later phase`} side="right">
        <button type="button" aria-disabled className={cn(ROW, "cursor-not-allowed")}>
          <Icon name={item.icon} className="size-4 text-text-secondary opacity-60" />
          <span className="min-w-0 flex-1 truncate text-text-secondary opacity-70">
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
      // /settings/security backs the "MFA" row; end-match so it doesn't also
      // light up under a future /settings/security/* child.
      end
      className={({ isActive }) =>
        cn(ROW, isActive ? "bg-action-accent-tint" : "hover:bg-surface-hover")
      }
    >
      {({ isActive }) => (
        <>
          <Icon
            name={item.icon}
            className={cn("size-4", isActive ? "text-action-accent" : "text-text-secondary")}
          />
          <span
            className={cn(
              "min-w-0 flex-1 truncate",
              isActive ? "text-action-accent" : "text-text-secondary",
            )}
          >
            {item.label}
          </span>
        </>
      )}
    </NavLink>
  );
}

export function SettingsLayout() {
  return (
    <div className="flex gap-8">
      <aside className="w-56 shrink-0" aria-label="Settings sections">
        <h1 className="mb-5 px-2.5 font-display text-heading-md text-text-primary">
          Settings
        </h1>
        {GROUPS.map((group) => (
          <div key={group.label} className="mb-5">
            <p className="mb-1.5 px-2.5 type-overline">{group.label}</p>
            <div className="flex flex-col gap-0.5">
              {group.items.map((item) => (
                <SettingsNavRow key={item.label} item={item} />
              ))}
            </div>
          </div>
        ))}
        <div className="border-t border-border pt-3">
          <SettingsNavRow item={AUDIT_ITEM} />
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}
