/**
 * The documentation sidebar, in reading order. Every MDX page under
 * content/docs/ must appear here exactly once, and every entry must have a
 * page: the build fails otherwise. A page's status (live, preview, soon) is
 * read from its own front matter, never from here.
 */

export type DocsIcon =
  | "rocket"
  | "shield"
  | "file"
  | "check"
  | "scales"
  | "handshake"
  | "server"
  | "plug"
  | "gear"
  | "map"
  | "book";

export interface DocsNavItem {
  /** Path under content/docs without the extension, e.g. "compliance/controls". */
  slug: string;
  /** Sidebar label. The page's own title is used for its heading. */
  label: string;
}

export interface DocsNavGroup {
  id: string;
  title: string;
  icon: DocsIcon;
  items: DocsNavItem[];
}

export const docsNav: DocsNavGroup[] = [
  {
    id: "get-started",
    title: "Get started",
    icon: "rocket",
    items: [
      { slug: "get-started/introduction", label: "Introduction to Verity" },
      { slug: "get-started/quick-start", label: "Your first half hour" },
      { slug: "get-started/sign-in-and-security", label: "Sign in and two-factor" },
      { slug: "get-started/navigating-verity", label: "Finding your way around" },
      { slug: "get-started/key-concepts", label: "Key concepts" },
    ],
  },
  {
    id: "compliance",
    title: "Compliance",
    icon: "shield",
    items: [
      { slug: "compliance/frameworks", label: "Frameworks and readiness" },
      { slug: "compliance/controls", label: "Controls" },
      { slug: "compliance/evidence", label: "Evidence" },
      { slug: "compliance/automated-checks", label: "Automated checks" },
      { slug: "compliance/framework-library", label: "More frameworks" },
    ],
  },
  {
    id: "policies",
    title: "Policies and documents",
    icon: "file",
    items: [
      { slug: "policies/documents-and-policies", label: "Draft a policy" },
      { slug: "policies/approval-and-publishing", label: "Approve and publish" },
      { slug: "policies/acknowledgement-campaigns", label: "Acknowledgement campaigns" },
    ],
  },
  {
    id: "tasks",
    title: "Tasks and approvals",
    icon: "check",
    items: [
      { slug: "tasks/overview", label: "Tasks and issues" },
      { slug: "tasks/service-levels-and-approvals", label: "Service levels and approvals" },
    ],
  },
  {
    id: "risk",
    title: "Risk management",
    icon: "scales",
    items: [
      { slug: "risk/risk-register", label: "The risk register" },
      { slug: "risk/treatment-and-acceptance", label: "Treat or accept a risk" },
      { slug: "risk/library-and-settings", label: "Library and settings" },
      { slug: "risk/enterprise-risk", label: "Enterprise risk" },
      { slug: "risk/business-continuity", label: "Business continuity" },
    ],
  },
  {
    id: "vendors",
    title: "Third-party risk",
    icon: "handshake",
    items: [
      { slug: "vendors/overview", label: "How vendor risk works" },
      { slug: "vendors/requests-and-intake", label: "Requests and intake" },
      { slug: "vendors/tiering", label: "Tiering" },
      { slug: "vendors/questionnaires", label: "Questionnaires and the portal" },
      { slug: "vendors/assessment-and-findings", label: "Assessment and findings" },
      { slug: "vendors/contracts-monitoring-offboarding", label: "Contracts to offboarding" },
    ],
  },
  {
    id: "security-operations",
    title: "Security operations",
    icon: "server",
    items: [
      { slug: "assets/inventory", label: "Asset inventory" },
      { slug: "assets/hygiene-and-dependencies", label: "Hygiene and dependencies" },
      { slug: "assets/import-and-custom-fields", label: "Import assets" },
      { slug: "vulnerabilities/findings-and-priority", label: "Findings and priority" },
      { slug: "vulnerabilities/importing-findings", label: "Import findings" },
      { slug: "vulnerabilities/remediation", label: "Remediation and exceptions" },
      { slug: "monitoring/continuous-monitoring", label: "Continuous monitoring" },
      { slug: "monitoring/device-monitoring", label: "Device monitoring" },
      { slug: "monitoring/access-reviews", label: "Access reviews" },
    ],
  },
  {
    id: "integrations",
    title: "Integrations",
    icon: "plug",
    items: [
      { slug: "integrations/overview", label: "How connections work" },
      { slug: "integrations/github", label: "GitHub" },
    ],
  },
  {
    id: "administration",
    title: "Administration",
    icon: "gear",
    items: [
      { slug: "admin/people", label: "People and invitations" },
      { slug: "admin/roles-and-groups", label: "Roles and groups" },
      { slug: "admin/security-settings", label: "Security settings" },
      { slug: "admin/custom-fields", label: "Custom fields" },
      { slug: "admin/audit-log-and-isolation", label: "Audit log and isolation" },
    ],
  },
  {
    id: "roadmap",
    title: "Coming soon",
    icon: "map",
    items: [
      { slug: "roadmap/trust-center", label: "Trust Center" },
      { slug: "roadmap/questionnaire-automation", label: "Questionnaire automation" },
      { slug: "roadmap/security-awareness-training", label: "Security awareness training" },
      { slug: "roadmap/ai-assistant", label: "AI assistant and drafting" },
      { slug: "roadmap/single-sign-on", label: "Single sign-on" },
      { slug: "roadmap/soc-reports", label: "SOC 1 and SOC 3" },
    ],
  },
  {
    id: "reference",
    title: "Reference",
    icon: "book",
    items: [
      { slug: "reference/glossary", label: "Glossary" },
      { slug: "reference/release-notes", label: "Release notes" },
    ],
  },
];

/** Every page slug in reading order. */
export const docsOrder: string[] = docsNav.flatMap((group) => group.items.map((item) => item.slug));
