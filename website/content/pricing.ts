import type { Status } from "./catalog";

/**
 * Plan packaging. This is a proposal for the product owner to confirm: the
 * site shows no prices, and every "Talk to sales" action opens the demo form
 * with the tier preselected. Statuses follow content/catalog.ts.
 */

export type TierId = "essentials" | "growth" | "enterprise" | "regulated";

export interface Tier {
  id: TierId;
  name: string;
  tagline: string;
  bestFor: string;
  highlights: string[];
  dark?: boolean;
}

export const tiers: Tier[] = [
  {
    id: "essentials",
    name: "Essentials",
    tagline: "Your first framework, done properly.",
    bestFor: "Teams preparing for their first SOC 2 audit.",
    highlights: ["SOC 2 library: 61 criteria, 114 control templates", "Evidence with renewal dates and review", "Policies from 15 templates, with acknowledgements", "Tasks with service levels", "Risk register with a 60-risk library", "Time-boxed auditor access"],
  },
  {
    id: "growth",
    name: "Growth",
    tagline: "More frameworks, one programme.",
    bestFor: "Companies answering several frameworks and customer reviews.",
    highlights: ["Everything in Essentials", "Third-party risk: the twelve-stage vendor lifecycle", "Asset inventory and vulnerability management", "GitHub with seven daily automated checks", "Custom fields for assets and vulnerabilities", "Additional framework libraries as they ship"],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    tagline: "Risk, security and compliance at scale.",
    bestFor: "Larger organisations with several teams and systems.",
    highlights: ["Everything in Growth", "Continuous monitoring across your stack (coming soon)", "Enterprise risk: self-assessments and KRIs (coming soon)", "Single sign-on and access reviews (coming soon)", "AI assistant and drafting (coming soon)", "Questionnaire automation (coming soon)"],
  },
  {
    id: "regulated",
    name: "Regulated",
    tagline: "Built for banks and regulated institutions.",
    bestFor: "Banks, DFIs, insurers and payment institutions under a regulator.",
    highlights: ["Everything in Enterprise", "Regulatory libraries: SBP, CBUAE, APRA and more (coming soon)", "Outsourcing and third-party registers", "Business continuity (coming soon)", "Board reporting and risk appetite (coming soon)", "Hosting and data-residency discussion with our team"],
    dark: true,
  },
];

type Cell = "yes" | "soon" | "no";

export interface FeatureRow {
  name: string;
  status: Status;
  tiers: Record<TierId, Cell>;
}

const all = (status: Status, from: TierId): FeatureRow["tiers"] => {
  const order: TierId[] = ["essentials", "growth", "enterprise", "regulated"];
  const start = order.indexOf(from);
  const cell: Cell = status === "soon" ? "soon" : "yes";
  return Object.fromEntries(order.map((tier, index) => [tier, index >= start ? cell : "no"])) as FeatureRow["tiers"];
};

export const comparison: { group: string; rows: FeatureRow[] }[] = [
  {
    group: "Compliance",
    rows: [
      { name: "SOC 2 library and controls", status: "live", tiers: all("live", "essentials") },
      { name: "Custom controls", status: "live", tiers: all("live", "essentials") },
      { name: "Evidence management and review", status: "live", tiers: all("live", "essentials") },
      { name: "Compliance dashboard by framework", status: "live", tiers: all("live", "essentials") },
      { name: "Policies, approvals and acknowledgements", status: "live", tiers: all("live", "essentials") },
      { name: "ISO 27001, PCI DSS, NIST, HIPAA, GDPR libraries", status: "soon", tiers: all("soon", "growth") },
      { name: "Regional banking and government libraries", status: "soon", tiers: all("soon", "regulated") },
      { name: "SOC 1 and SOC 3 support", status: "soon", tiers: all("soon", "enterprise") },
      { name: "Trust Center", status: "soon", tiers: all("soon", "growth") },
      { name: "Questionnaire automation", status: "soon", tiers: all("soon", "enterprise") },
    ],
  },
  {
    group: "Risk",
    rows: [
      { name: "Risk register, scoring and acceptance", status: "live", tiers: all("live", "essentials") },
      { name: "Third-party risk lifecycle", status: "live", tiers: all("live", "growth") },
      { name: "Vendor questionnaires and portal", status: "live", tiers: all("live", "growth") },
      { name: "Enterprise risk: RCSA, KRIs, incidents", status: "soon", tiers: all("soon", "enterprise") },
      { name: "Business continuity", status: "soon", tiers: all("soon", "regulated") },
    ],
  },
  {
    group: "Security",
    rows: [
      { name: "Asset inventory and import", status: "live", tiers: all("live", "growth") },
      { name: "Vulnerability management and scanner imports", status: "live", tiers: all("live", "growth") },
      { name: "GitHub automated checks", status: "live", tiers: all("live", "growth") },
      { name: "Cloud, identity and ticketing connectors", status: "soon", tiers: all("soon", "growth") },
      { name: "Continuous monitoring and alerts", status: "soon", tiers: all("soon", "enterprise") },
      { name: "Device monitoring", status: "soon", tiers: all("soon", "enterprise") },
      { name: "Access reviews", status: "soon", tiers: all("soon", "enterprise") },
      { name: "Security awareness training", status: "soon", tiers: all("soon", "growth") },
    ],
  },
  {
    group: "Platform and administration",
    rows: [
      { name: "Roles, groups and permissions", status: "live", tiers: all("live", "essentials") },
      { name: "Two-factor requirement for administrators", status: "live", tiers: all("live", "essentials") },
      { name: "Time-boxed auditor access", status: "live", tiers: all("live", "essentials") },
      { name: "Append-only audit log", status: "live", tiers: all("live", "essentials") },
      { name: "Tasks with service levels", status: "live", tiers: all("live", "essentials") },
      { name: "Custom fields", status: "live", tiers: all("live", "growth") },
      { name: "Single sign-on", status: "soon", tiers: all("soon", "enterprise") },
      { name: "AI assistant and drafting", status: "soon", tiers: all("soon", "enterprise") },
    ],
  },
];

export const pricingFaqs = [
  { q: "Why are there no prices on this page?", a: "Pricing depends on the modules and frameworks you need and the size of your organisation, so we quote each plan. Talk to our team and we will send a proposal." },
  { q: "Can we try Verity first?", a: "Yes. Start a trial and the Get Started checklist will walk you through your first workspace. If you would rather see it with us, book a demo." },
  { q: "What happens when a coming-soon feature ships?", a: "It becomes available on the plans marked for it in the table. Coming-soon items are on our roadmap; we do not publish dates for them." },
  { q: "Can we change plans later?", a: "Yes. Plans differ by module, so moving up adds modules to the workspace you already have. Nothing you have built is lost." },
];
