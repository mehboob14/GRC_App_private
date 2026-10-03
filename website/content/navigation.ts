import type { IconName } from "@/components/ui/icon";
import { moduleGroups, modules, type ModuleGroupId, type Status } from "./catalog";

export interface MenuLink {
  title: string;
  description?: string;
  href: string;
  icon?: IconName;
  status?: Status;
}

export interface MenuColumn {
  title: string;
  links: MenuLink[];
}

const groupIcon: Record<ModuleGroupId, IconName> = { compliance: "shield", risk: "scales", security: "server", platform: "stack" };

export const platformMenu: MenuColumn[] = moduleGroups.map((group) => ({
  title: group.name,
  links: modules
    .filter((item) => item.group === group.id)
    .map((item) => ({ title: item.name, description: item.summary, href: `/platform/${item.slug}/`, icon: item.icon, status: item.status })),
}));

export { groupIcon };

export const industries = [
  { slug: "banking-financial-services", name: "Banking and financial services", short: "Banks, DFIs, microfinance and Islamic banks", icon: "bank" },
  { slug: "fintech-payments", name: "Fintech and payments", short: "Payment providers, wallets and lenders", icon: "credit-card" },
  { slug: "healthcare", name: "Healthcare", short: "Providers, health tech and insurers", icon: "heartbeat" },
  { slug: "saas-technology", name: "SaaS and technology", short: "Software companies selling to enterprises", icon: "cloud" },
  { slug: "government-public-sector", name: "Government and public sector", short: "Ministries, regulators and agencies", icon: "building" },
] as const satisfies ReadonlyArray<{ slug: string; name: string; short: string; icon: IconName }>;

export type IndustrySlug = (typeof industries)[number]["slug"];

export const solutionsMenu: MenuColumn[] = [
  {
    title: "By industry",
    links: industries.map((item) => ({ title: item.name, description: item.short, href: `/solutions/${item.slug}/`, icon: item.icon })),
  },
  {
    title: "By framework",
    links: [
      { title: "SOC 2", description: "AICPA Trust Services Criteria", href: "/frameworks/?q=SOC%202", icon: "seal", status: "live" },
      { title: "ISO/IEC 27001", description: "Information security management", href: "/frameworks/?q=27001", icon: "certificate", status: "soon" },
      { title: "PCI DSS", description: "Payment card data security", href: "/frameworks/?q=PCI", icon: "credit-card", status: "soon" },
      { title: "SBP frameworks", description: "State Bank of Pakistan", href: "/frameworks/?region=pk", icon: "bank", status: "soon" },
      { title: "UAE frameworks", description: "UAE IA, DESC, ADHICS, PDPL", href: "/frameworks/?region=ae", icon: "globe", status: "soon" },
      { title: "APRA and Essential Eight", description: "Australian requirements", href: "/frameworks/?region=au", icon: "globe", status: "soon" },
    ],
  },
];

export const resourcesMenu: MenuColumn[] = [
  {
    title: "Learn",
    links: [
      { title: "Documentation", description: "Task-by-task guides for every module", href: "/docs/", icon: "book" },
      { title: "Your first half hour", description: "Get a new workspace useful fast", href: "/docs/get-started/quick-start/", icon: "rocket" },
      { title: "Key concepts", description: "Controls, evidence and linked records", href: "/docs/get-started/key-concepts/", icon: "graph" },
      { title: "Release notes", description: "What is live and what changed", href: "/docs/reference/release-notes/", icon: "list" },
    ],
  },
  {
    title: "Explore",
    links: [
      { title: "Framework library", description: "Every framework, with its status", href: "/frameworks/", icon: "stack" },
      { title: "Security at Verity", description: "How we protect your workspace", href: "/security/", icon: "lock" },
      { title: "Glossary", description: "The words Verity uses", href: "/docs/reference/glossary/", icon: "hash" },
      { title: "Platform overview", description: "Every module in one view", href: "/platform/", icon: "compass" },
    ],
  },
];

export const footerColumns: MenuColumn[] = [
  { title: "Platform", links: [{ title: "Overview", href: "/platform/" }, ...modules.filter((m) => m.status === "live").map((m) => ({ title: m.name, href: `/platform/${m.slug}/` }))] },
  { title: "Coming soon", links: modules.filter((m) => m.status === "soon").map((m) => ({ title: m.name, href: `/platform/${m.slug}/` })) },
  { title: "Solutions", links: [...industries.map((i) => ({ title: i.name, href: `/solutions/${i.slug}/` })), { title: "Framework library", href: "/frameworks/" }] },
  { title: "Resources", links: [{ title: "Documentation", href: "/docs/" }, { title: "Release notes", href: "/docs/reference/release-notes/" }, { title: "Glossary", href: "/docs/reference/glossary/" }, { title: "Security", href: "/security/" }, { title: "Why Verity", href: "/why-verity/" }, { title: "Pricing", href: "/pricing/" }] },
];
