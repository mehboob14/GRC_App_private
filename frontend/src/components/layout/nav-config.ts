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
 * Primary nav — three groups (Overview · Compliance · Risk) plus a utility
 * footer. Later-phase modules are listed for orientation but carry an explicit
 * "Soon" affordance — never a fake count or a dead link.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { id: "get-started", label: "Get Started", icon: "check", to: "/quick-start" },
      { id: "dashboard", label: "Dashboard", icon: "grid", to: "/dashboard" },
      { id: "tasks", label: "Tasks", icon: "audit", comingSoon: true },
    ],
  },
  {
    id: "compliance",
    label: "Compliance",
    items: [
      { id: "frameworks", label: "Frameworks", icon: "shield", to: "/frameworks" },
      { id: "controls", label: "Controls", icon: "controls", to: "/controls" },
      { id: "evidence", label: "Evidence", icon: "doc", to: "/evidence" },
      { id: "policies", label: "Policies & Documents", icon: "book", comingSoon: true },
    ],
  },
  {
    id: "risk",
    label: "Risk",
    items: [
      { id: "risks", label: "Risks", icon: "risk", comingSoon: true },
      { id: "vendors", label: "Vendors", icon: "vendor", comingSoon: true },
      { id: "assets", label: "Assets", icon: "box", comingSoon: true },
      { id: "vulnerabilities", label: "Vulnerabilities", icon: "bug", comingSoon: true },
    ],
  },
];

export const FOOTER_ITEMS: NavItem[] = [
  { id: "connectors", label: "Connections", icon: "plug", to: "/connectors" },
  { id: "audit-log", label: "Audit Log", icon: "doc", to: "/audit-log" },
  { id: "settings", label: "Settings", icon: "gear", to: "/settings/access/people" },
];
