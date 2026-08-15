import type { IconName } from "@/components/ui/icon";

export type NavItem = {
  id: string;
  label: string;
  icon: IconName;
  to?: string;
  /** Live count sourced from real data — never on comingSoon items. */
  count?: number;
  countTone?: "fail" | "review";
  comingSoon?: boolean;
};

export type NavSection = {
  id: string;
  label: string;
  items: NavItem[];
};

/**
 * Primary nav — three groups, Drata-style (Overview · Compliance ·
 * Organization) plus a utility footer. Later-phase modules are listed for
 * orientation but carry an explicit "Soon" affordance — never a fake count or
 * a dead link. Kept to 8 grouped items so the rail stays scannable.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { id: "get-started", label: "Get Started", icon: "check", to: "/quick-start" },
      { id: "dashboard", label: "Dashboard", icon: "grid", comingSoon: true },
    ],
  },
  {
    id: "compliance",
    label: "Compliance",
    items: [
      { id: "frameworks", label: "Frameworks", icon: "shield", comingSoon: true },
      { id: "controls", label: "Controls", icon: "controls", comingSoon: true },
      { id: "evidence", label: "Evidence", icon: "doc", comingSoon: true },
    ],
  },
  {
    id: "organization",
    label: "Organization",
    items: [
      { id: "risk", label: "Risk", icon: "risk", comingSoon: true },
      { id: "vendors", label: "Vendors", icon: "vendor", comingSoon: true },
      { id: "governance", label: "Governance", icon: "layers", comingSoon: true },
    ],
  },
];

export const FOOTER_ITEMS: NavItem[] = [
  { id: "connectors", label: "Connections", icon: "plug", to: "/connectors" },
  { id: "audit-log", label: "Audit log", icon: "audit", to: "/audit-log" },
  { id: "settings", label: "Settings", icon: "gear", to: "/settings/people" },
];
