import type { IconName } from "@/components/ui/icon";

/**
 * Settings information architecture, in one place. The secondary sidebar lists
 * the categories; each category page shows its `tabs` as a top tab bar (the
 * Drata pattern). `soon` tabs render disabled — no route, no dead link.
 */
export type SettingsTab = { label: string; to: string; soon?: boolean };

export type SettingsCategory = {
  id: string;
  label: string;
  icon: IconName;
  /** Route the sidebar entry points at (its first real tab). */
  to: string;
  tabs: SettingsTab[];
};

export const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    id: "access",
    label: "Access Management",
    icon: "users",
    to: "/settings/access/people",
    tabs: [
      { label: "People", to: "/settings/access/people" },
      { label: "Groups", to: "/settings/access/groups" },
      { label: "Roles & Permissions", to: "/settings/access/roles" },
    ],
  },
  {
    id: "security",
    label: "Security",
    icon: "shield",
    to: "/settings/security/mfa",
    tabs: [
      { label: "MFA", to: "/settings/security/mfa" },
      { label: "Authentication", to: "/settings/security/authentication", soon: true },
      { label: "SSO", to: "/settings/security/sso", soon: true },
    ],
  },
  {
    id: "organization",
    label: "Organization",
    icon: "grid",
    to: "/settings/organization/profile",
    tabs: [
      { label: "Org info", to: "/settings/organization/profile" },
      { label: "Key personnel", to: "/settings/organization/key-personnel", soon: true },
    ],
  },
  {
    id: "integrations",
    label: "Integrations",
    icon: "plug",
    to: "/settings/integrations",
    tabs: [
      { label: "Integrations", to: "/settings/integrations/apps", soon: true },
      { label: "API Keys", to: "/settings/integrations/api-keys", soon: true },
      { label: "Webhooks", to: "/settings/integrations/webhooks", soon: true },
    ],
  },
];

/** Lives in the main nav too; a settings-side entry matches the requested tree. */
export const SETTINGS_AUDIT = {
  label: "Audit Log",
  icon: "doc" as IconName,
  to: "/audit-log",
};

export function settingsCategory(id: string): SettingsCategory | undefined {
  return SETTINGS_CATEGORIES.find((category) => category.id === id);
}
