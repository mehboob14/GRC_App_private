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

export type RailItem = {
  id: string;
  label: string;
  icon: IconName;
  sectionId: string;
  /** First enabled route of the section; absent → later-phase, disabled. */
  to?: string;
};

/**
 * Nav from Figma Screens · Onboarding & Admin (121:5769). Later-phase modules
 * are listed for orientation but carry an explicit "Soon" affordance —
 * never a fake count or a dead link.
 */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: "overview",
    label: "Overview",
    items: [
      { id: "quick-start", label: "Dashboard", icon: "grid", to: "/quick-start" },
    ],
  },
  {
    id: "compliance",
    label: "Compliance",
    items: [
      { id: "frameworks", label: "Frameworks", icon: "shield", comingSoon: true },
      { id: "controls", label: "Controls", icon: "controls", comingSoon: true },
      { id: "evidence", label: "Evidence", icon: "doc", comingSoon: true },
      { id: "policies", label: "Policies & Docs", icon: "book", comingSoon: true },
    ],
  },
  {
    id: "monitoring",
    label: "Monitoring",
    items: [
      { id: "checks", label: "Checks", icon: "activity", comingSoon: true },
      { id: "findings", label: "Findings", icon: "alert", comingSoon: true },
      {
        id: "connectors",
        label: "Connectors",
        icon: "plug",
        // Matches the two down connections on the Connections screen.
        count: 2,
        countTone: "fail",
        to: "/connectors",
      },
    ],
  },
  {
    id: "risk",
    label: "Risk",
    items: [
      { id: "risk-register", label: "Risk Register", icon: "risk", comingSoon: true },
      { id: "erm", label: "ERM", icon: "layers", comingSoon: true },
      { id: "tprm", label: "Third-Party Risk", icon: "vendor", comingSoon: true },
    ],
  },
  {
    id: "inventory",
    label: "Inventory",
    items: [
      { id: "assets", label: "Assets", icon: "box", comingSoon: true },
      { id: "vulnerabilities", label: "Vulnerabilities", icon: "bug", comingSoon: true },
    ],
  },
  {
    id: "access-audit",
    label: "Access & Audit",
    items: [
      { id: "people", label: "People", icon: "users", to: "/people" },
      { id: "access-reviews", label: "Access Reviews", icon: "users", comingSoon: true },
      { id: "auditor-view", label: "Auditor View", icon: "audit", comingSoon: true },
      { id: "trust-center", label: "Trust Center", icon: "globe", comingSoon: true },
      { id: "audit-log", label: "Audit log", icon: "doc", to: "/audit-log" },
    ],
  },
];

export const RAIL_ITEMS: RailItem[] = [
  { id: "overview", label: "Overview", icon: "grid", sectionId: "overview", to: "/quick-start" },
  { id: "compliance", label: "Compliance", icon: "shield", sectionId: "compliance" },
  { id: "monitoring", label: "Monitoring", icon: "activity", sectionId: "monitoring", to: "/connectors" },
  { id: "risk", label: "Risk", icon: "risk", sectionId: "risk" },
  { id: "inventory", label: "Inventory", icon: "box", sectionId: "inventory" },
  { id: "access-audit", label: "Access & Audit", icon: "audit", sectionId: "access-audit", to: "/people" },
];

export const FOOTER_ITEMS: NavItem[] = [
  { id: "settings", label: "Settings", icon: "gear", to: "/settings/security" },
  { id: "integrations", label: "Integrations", icon: "puzzle", comingSoon: true },
];
