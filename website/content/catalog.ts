import type { IconName } from "@/components/ui/icon";

/**
 * The single source of truth for what Verity offers and whether it is
 * available. Menus, pages, chips, the pricing table and the docs all read
 * from here, so one status change updates every place that shows it.
 *
 * live    — generally available in the product today (as the user guide describes)
 * preview — visible in the product with illustrative data
 * soon    — planned; always rendered with a Coming soon badge
 */
export type Status = "live" | "preview" | "soon";

export type ModuleGroupId = "compliance" | "risk" | "security" | "platform";

export interface ModuleGroup {
  id: ModuleGroupId;
  name: string;
  description: string;
}

export interface PlatformModule {
  slug: string;
  name: string;
  /** One line for menus and cards. */
  summary: string;
  group: ModuleGroupId;
  status: Status;
  icon: IconName;
  /** Docs page that explains it, if any. */
  docs?: string;
}

export const moduleGroups: ModuleGroup[] = [
  { id: "compliance", name: "Compliance", description: "Frameworks, controls, evidence and the policies behind them." },
  { id: "risk", name: "Risk", description: "Risks, third parties and the decisions you make about them." },
  { id: "security", name: "Security", description: "The systems you run and the weaknesses in them." },
  { id: "platform", name: "Platform", description: "Connections, workflow and the assistant across every module." },
];

export const modules: PlatformModule[] = [
  { slug: "compliance-automation", name: "Compliance automation", summary: "Frameworks, controls and readiness in one control set.", group: "compliance", status: "live", icon: "shield", docs: "compliance/controls" },
  { slug: "evidence-management", name: "Evidence management", summary: "Collect proof once, map it to every control, keep it fresh.", group: "compliance", status: "live", icon: "folder", docs: "compliance/evidence" },
  { slug: "policy-management", name: "Policy management", summary: "Draft, approve, publish and get every policy acknowledged.", group: "compliance", status: "live", icon: "file", docs: "policies/documents-and-policies" },
  { slug: "trust-center", name: "Trust Center", summary: "A public page that shows customers your security posture.", group: "compliance", status: "soon", icon: "seal", docs: "roadmap/trust-center" },
  { slug: "questionnaire-automation", name: "Questionnaire automation", summary: "Answer customer security questionnaires from what you already hold.", group: "compliance", status: "soon", icon: "clipboard", docs: "roadmap/questionnaire-automation" },

  { slug: "risk-management", name: "Risk management", summary: "A scored register with treatment, acceptance and a starter library.", group: "risk", status: "live", icon: "scales", docs: "risk/risk-register" },
  { slug: "third-party-risk", name: "Third-party risk", summary: "Every vendor from request to offboarding, tiered by risk.", group: "risk", status: "live", icon: "handshake", docs: "vendors/overview" },
  { slug: "enterprise-risk-management", name: "Enterprise risk", summary: "Risk and control self-assessments, KRIs, incidents and appetite.", group: "risk", status: "soon", icon: "chart-line", docs: "risk/enterprise-risk" },
  { slug: "business-continuity", name: "Business continuity", summary: "Impact analysis, recovery plans and tested readiness.", group: "risk", status: "soon", icon: "lifebuoy", docs: "risk/business-continuity" },

  { slug: "asset-inventory", name: "Asset inventory", summary: "Every system with an owner, a criticality and its dependencies.", group: "security", status: "live", icon: "server", docs: "assets/inventory" },
  { slug: "vulnerability-management", name: "Vulnerability management", summary: "Import findings, prioritise beyond CVSS, remediate on time.", group: "security", status: "live", icon: "bug", docs: "vulnerabilities/findings-and-priority" },
  { slug: "continuous-monitoring", name: "Continuous monitoring", summary: "Checks on a schedule, with findings and alerts when one fails.", group: "security", status: "soon", icon: "pulse", docs: "monitoring/continuous-monitoring" },
  { slug: "device-monitoring", name: "Device monitoring", summary: "Know every laptop is encrypted, locked and patched.", group: "security", status: "soon", icon: "laptop", docs: "monitoring/device-monitoring" },
  { slug: "access-reviews", name: "Access reviews", summary: "Periodic reviews of who can reach what, with decisions on record.", group: "security", status: "soon", icon: "user-check", docs: "monitoring/access-reviews" },
  { slug: "security-awareness-training", name: "Security awareness training", summary: "Assign training and keep completion as evidence.", group: "security", status: "soon", icon: "graduation", docs: "roadmap/security-awareness-training" },

  { slug: "integrations", name: "Integrations", summary: "Connect source control today, and your cloud and identity stack next.", group: "platform", status: "live", icon: "plug", docs: "integrations/overview" },
  { slug: "workflows-and-approvals", name: "Tasks and approvals", summary: "Assigned work with service levels, approvals and full history.", group: "platform", status: "live", icon: "kanban", docs: "tasks/overview" },
  { slug: "ai-assistant", name: "AI assistant", summary: "Drafts and answers that a person always reviews and approves.", group: "platform", status: "soon", icon: "sparkle", docs: "roadmap/ai-assistant" },
];

export function moduleBySlug(slug: string): PlatformModule | undefined {
  return modules.find((item) => item.slug === slug);
}

export function modulesInGroup(group: ModuleGroupId): PlatformModule[] {
  return modules.filter((item) => item.group === group);
}

/** Smaller capabilities shown as chips on sections and module pages. */
export interface Capability {
  name: string;
  status: Status;
  href?: string;
}

/** Facts from the content that ships with every workspace. Keep in step with backend/src/verity/seed/content/. */
export const libraryFacts = [
  { label: "SOC 2 criteria mapped", value: "61" },
  { label: "Control templates", value: "114" },
  { label: "Policy templates", value: "15" },
  { label: "Library risks", value: "60" },
] as const;

export interface Integration {
  name: string;
  capability: string;
  status: Status;
}

/**
 * Providers by capability, from backend/src/verity/seed/content/automation/capabilities.json.
 * Providers marked not_planned there are deliberately absent.
 */
export const integrationCapabilities: { name: string; description: string; icon: IconName; providers: Integration[] }[] = [
  { name: "Version control", description: "Where code changes are proposed, reviewed and merged.", icon: "code", providers: [
    { name: "GitHub", capability: "Version control", status: "live" },
    { name: "GitLab", capability: "Version control", status: "soon" },
    { name: "Bitbucket", capability: "Version control", status: "soon" },
  ] },
  { name: "Cloud infrastructure", description: "Where production systems and data run.", icon: "cloud", providers: [
    { name: "Amazon Web Services", capability: "Cloud infrastructure", status: "soon" },
    { name: "Microsoft Azure", capability: "Cloud infrastructure", status: "soon" },
    { name: "Google Cloud", capability: "Cloud infrastructure", status: "soon" },
    { name: "DigitalOcean", capability: "Cloud infrastructure", status: "soon" },
    { name: "Heroku", capability: "Cloud infrastructure", status: "soon" },
    { name: "Render", capability: "Cloud infrastructure", status: "soon" },
    { name: "Vercel", capability: "Cloud infrastructure", status: "soon" },
    { name: "Netlify", capability: "Cloud infrastructure", status: "soon" },
    { name: "Supabase", capability: "Cloud infrastructure", status: "soon" },
    { name: "Neon", capability: "Cloud infrastructure", status: "soon" },
    { name: "Qovery", capability: "Cloud infrastructure", status: "soon" },
  ] },
  { name: "Identity", description: "Where staff accounts, sign-in rules and groups live.", icon: "fingerprint", providers: [
    { name: "Okta", capability: "Identity provider", status: "soon" },
    { name: "Google Workspace", capability: "Identity provider", status: "soon" },
    { name: "Microsoft 365 and Entra ID", capability: "Identity provider", status: "soon" },
    { name: "1Password", capability: "Password manager", status: "soon" },
  ] },
  { name: "Work and alerting", description: "Where work is tracked and people are paged.", icon: "bell", providers: [
    { name: "Jira", capability: "Ticketing", status: "soon" },
    { name: "Linear", capability: "Ticketing", status: "soon" },
    { name: "Asana", capability: "Ticketing", status: "soon" },
    { name: "ClickUp", capability: "Ticketing", status: "soon" },
    { name: "Monday", capability: "Ticketing", status: "soon" },
    { name: "Notion", capability: "Ticketing", status: "soon" },
    { name: "PagerDuty", capability: "On call and alerting", status: "soon" },
    { name: "Slack", capability: "On call and alerting", status: "soon" },
  ] },
  { name: "Network and observability", description: "The edge, logs, metrics and errors.", icon: "pulse", providers: [
    { name: "Cloudflare", capability: "Network and edge", status: "soon" },
    { name: "Tailscale", capability: "Network and edge", status: "soon" },
    { name: "Datadog", capability: "Observability", status: "soon" },
    { name: "Sentry", capability: "Observability", status: "soon" },
    { name: "Grafana", capability: "Observability", status: "soon" },
    { name: "SigNoz", capability: "Observability", status: "soon" },
    { name: "Better Stack", capability: "Observability", status: "soon" },
  ] },
  { name: "Vulnerability scanning and assets", description: "Scanners and the systems that know what exists.", icon: "detective", providers: [
    { name: "Tenable Nessus", capability: "Vulnerability scanner", status: "soon" },
    { name: "Rapid7 Nexpose", capability: "Vulnerability scanner", status: "soon" },
    { name: "Qualys", capability: "Vulnerability scanner", status: "soon" },
    { name: "BMC", capability: "Asset discovery", status: "soon" },
  ] },
];

export const githubChecks = [
  "Default branch is protected",
  "Merges need an approving review",
  "Merged changes were reviewed",
  "Checks must pass before merge",
  "Secret scanning is on",
  "Dependency alerts are on",
  "Two factor is required for code access",
] as const;
