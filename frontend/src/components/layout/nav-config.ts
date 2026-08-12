import type { IconName } from "@/components/ui/icon";

export type NavItem = {
  id: string;
  label: string;
  icon: IconName;
  to?: string;
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
  dot?: boolean;
};

/** Nav from Figma Screens · Onboarding & Admin (121:5769). */
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
      {
        id: "controls",
        label: "Controls",
        icon: "controls",
        count: 3,
        countTone: "fail",
        comingSoon: true,
      },
      {
        id: "evidence",
        label: "Evidence",
        icon: "doc",
        count: 4,
        countTone: "review",
        comingSoon: true,
      },
      { id: "policies", label: "Policies & Docs", icon: "book", comingSoon: true },
    ],
  },
  {
    id: "monitoring",
    label: "Monitoring",
    items: [
      { id: "checks", label: "Checks", icon: "activity", comingSoon: true },
      {
        id: "findings",
        label: "Findings",
        icon: "alert",
        count: 5,
        countTone: "fail",
        comingSoon: true,
      },
      {
        id: "connectors",
        label: "Connectors",
        icon: "plug",
        count: 1,
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
      {
        id: "vulnerabilities",
        label: "Vulnerabilities",
        icon: "bug",
        count: 12,
        countTone: "fail",
        comingSoon: true,
      },
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
  { id: "overview", label: "Overview", icon: "grid", sectionId: "overview" },
  {
    id: "compliance",
    label: "Compliance",
    icon: "shield",
    sectionId: "compliance",
    dot: true,
  },
  {
    id: "monitoring",
    label: "Monitoring",
    icon: "activity",
    sectionId: "monitoring",
    dot: true,
  },
  { id: "risk", label: "Risk", icon: "risk", sectionId: "risk", dot: true },
  { id: "inventory", label: "Inventory", icon: "box", sectionId: "inventory" },
  {
    id: "access-audit",
    label: "Access & Audit",
    icon: "audit",
    sectionId: "access-audit",
  },
];

export const FOOTER_ITEMS: NavItem[] = [
  { id: "settings", label: "Settings", icon: "gear", to: "/settings/security" },
  { id: "integrations", label: "Integrations", icon: "puzzle", comingSoon: true },
];
