import type { Status } from "./catalog";

export type Region = "global" | "us" | "pk" | "ae" | "au" | "eu";
export type FrameworkCategory = "security" | "privacy" | "financial-services" | "payments" | "healthcare" | "government" | "cloud" | "ai" | "resilience" | "audit-reporting" | "critical-infrastructure";
export type FrameworkIndustry = "banking" | "fintech" | "healthcare" | "saas" | "government";

export interface Framework {
  id: string;
  name: string;
  shortName: string;
  issuer: string;
  region: Region;
  jurisdictionNote?: string;
  categories: FrameworkCategory[];
  industries: FrameworkIndustry[];
  version: string;
  type: "standard" | "regulation" | "law" | "framework" | "attestation";
  summary: string;
  whoItsFor: string;
  status: Status;
}

export const regions: { id: Region; name: string; short: string }[] = [
  { id: "global", name: "International", short: "Global" },
  { id: "us", name: "United States", short: "US" },
  { id: "pk", name: "Pakistan", short: "PK" },
  { id: "ae", name: "United Arab Emirates", short: "UAE" },
  { id: "au", name: "Australia", short: "AU" },
  { id: "eu", name: "European Union", short: "EU" },
];

export const categoryNames: Record<FrameworkCategory, string> = {
  security: "Information security",
  privacy: "Privacy and data protection",
  "financial-services": "Financial services",
  payments: "Payments",
  healthcare: "Healthcare",
  government: "Government",
  cloud: "Cloud",
  ai: "Artificial intelligence",
  resilience: "Resilience and continuity",
  "audit-reporting": "Audit reports",
  "critical-infrastructure": "Critical infrastructure",
};

/** The verified catalog lives in frameworks.data.ts. Only SOC 2 is live. */
export { frameworks } from "./frameworks.data";

import { frameworks as all } from "./frameworks.data";

export function frameworksByRegion(region: Region): Framework[] {
  return all.filter((framework) => framework.region === region);
}

export function frameworkCount(status?: Status): number {
  return status ? all.filter((framework) => framework.status === status).length : all.length;
}
