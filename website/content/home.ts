import type { Capability } from "./catalog";
import type { Feature } from "@/components/sections/pillar";
import type { IconName } from "@/components/ui/icon";

/**
 * Homepage copy. Kept out of components so the page can be translated by
 * swapping this module. Section order and its reasoning: design.md, section 5.
 */

export const hero = {
  eyebrow: "Compliance as a service, end to end",
  title: "Your source of truth for compliance and security",
  lead: "Verity brings your frameworks, controls, evidence, policies, risks, vendors and systems into one connected workspace. See what needs attention, prove what works, and walk into every audit ready.",
};

export const facts = {
  title: "Ready on day one",
  note: "Shipped in every workspace",
};

export const problem = {
  eyebrow: "Why it is hard today",
  title: "Compliance work lives everywhere except one place.",
  lead: "Controls in spreadsheets, evidence in shared drives, vendor reviews in email, vulnerabilities in a ticket queue. Every new framework repeats the work, and the weeks before an audit turn into a hunt.",
  pains: [
    { icon: "copy", title: "The same proof, collected again and again", text: "Every framework asks for access reviews. Without one control set, each audit starts from zero." },
    { icon: "clock", title: "Evidence that quietly goes stale", text: "Exports and screenshots expire, and nobody notices until an auditor does." },
    { icon: "handshake", title: "Vendors nobody is watching", text: "Third parties get your data on a signature. Reviews happen once, if at all." },
    { icon: "scroll", title: "Decisions without a trail", text: "Risks are accepted in a meeting and forgotten, with no owner, no expiry and no record." },
  ] satisfies { icon: IconName; title: string; text: string }[],
  resolution: "Verity replaces the scatter with one connected record. Every control, document, risk, vendor and system has an owner, a status and a history.",
};

export const pillars: {
  id: string;
  eyebrow: string;
  title: string;
  lead: string;
  link: { href: string; label: string };
  features: Feature[];
  chips: Capability[];
}[] = [
  {
    id: "prove-compliance",
    eyebrow: "Prove compliance",
    title: "Compliance automation",
    lead: "Turn every framework you answer to into one owned set of controls. Verity maps requirements to controls, keeps the evidence behind each one current, and shows your readiness as it is today.",
    link: { href: "/platform/compliance-automation/", label: "Explore compliance automation" },
    features: [
      { icon: "tree", title: "Map once, satisfy many", text: "One control answers every framework that asks for it, so evidence is collected once." },
      { icon: "clock", title: "Evidence that stays fresh", text: "Renewal dates mark proof as aging before it goes stale, so nothing expires unnoticed." },
      { icon: "gauge", title: "Readiness you can show", text: "Live readiness by framework, criterion and owner, not a slide deck." },
    ],
    chips: [
      { name: "Frameworks and controls", status: "live", href: "/platform/compliance-automation/" },
      { name: "Evidence", status: "live", href: "/platform/evidence-management/" },
      { name: "Automated checks", status: "live", href: "/platform/integrations/" },
      { name: "More framework libraries", status: "soon", href: "/frameworks/" },
      { name: "Trust Center", status: "soon", href: "/platform/trust-center/" },
      { name: "SOC 1 and SOC 3", status: "soon", href: "/frameworks/?q=SOC" },
    ],
  },
  {
    id: "manage-risk",
    eyebrow: "Manage risk",
    title: "Risk and third parties",
    lead: "Score every risk the same way, decide what to do about it, and give every vendor the scrutiny its risk deserves, from the first request to offboarding.",
    link: { href: "/platform/third-party-risk/", label: "Explore third-party risk" },
    features: [
      { icon: "scales", title: "One matrix for the whole organisation", text: "Inherent and residual scores on a matrix you configure, with a 60-risk starter library." },
      { icon: "handshake", title: "Vendors reviewed in proportion", text: "Tiering decides how deep a review goes, who signs it off and how often it repeats." },
      { icon: "signature", title: "Decisions that keep their reasons", text: "Every acceptance has a justification, an approver and an expiry. When it lapses, the risk reopens." },
    ],
    chips: [
      { name: "Risk register", status: "live", href: "/platform/risk-management/" },
      { name: "Third-party risk", status: "live", href: "/platform/third-party-risk/" },
      { name: "Vendor questionnaires and portal", status: "live", href: "/docs/vendors/questionnaires/" },
      { name: "Enterprise risk and KRIs", status: "soon", href: "/platform/enterprise-risk-management/" },
      { name: "Business continuity", status: "soon", href: "/platform/business-continuity/" },
    ],
  },
  {
    id: "secure-estate",
    eyebrow: "Secure the estate",
    title: "Assets and vulnerabilities",
    lead: "Know what you run, who owns it and what is wrong with it. Verity ties every vulnerability to an asset, ranks it by real-world risk, and holds remediation to a deadline.",
    link: { href: "/platform/vulnerability-management/", label: "Explore vulnerability management" },
    features: [
      { icon: "server", title: "An inventory with owners", text: "Criticality comes from what each system holds, with review cadence and dependencies." },
      { icon: "target", title: "Priority beyond CVSS", text: "Known exploitation, exploit likelihood and asset criticality decide what gets fixed first." },
      { icon: "clock", title: "Remediation against the clock", text: "Windows by priority, remediation plans, and exceptions that expire." },
    ],
    chips: [
      { name: "Asset inventory", status: "live", href: "/platform/asset-inventory/" },
      { name: "Vulnerability management", status: "live", href: "/platform/vulnerability-management/" },
      { name: "Scanner imports", status: "live", href: "/docs/vulnerabilities/importing-findings/" },
      { name: "Continuous monitoring", status: "soon", href: "/platform/continuous-monitoring/" },
      { name: "Device monitoring", status: "soon", href: "/platform/device-monitoring/" },
      { name: "Access reviews", status: "soon", href: "/platform/access-reviews/" },
    ],
  },
  {
    id: "govern",
    eyebrow: "Govern with confidence",
    title: "Policies and people",
    lead: "Write policies from proven templates, route them for approval, and make sure everyone who must read them has signed. Every step is on the record.",
    link: { href: "/platform/policy-management/", label: "Explore policy management" },
    features: [
      { icon: "file", title: "Start from 15 templates", text: "Draft in a real editor, map the policy to controls, and keep every version." },
      { icon: "stamp", title: "Approval you can evidence", text: "Approval tiers and named approvers, recorded for the auditor." },
      { icon: "users", title: "Acknowledged by everyone who must", text: "Targeted campaigns and a signature trail for each person, kept as evidence." },
    ],
    chips: [
      { name: "Policies and documents", status: "live", href: "/platform/policy-management/" },
      { name: "Acknowledgement campaigns", status: "live", href: "/docs/policies/acknowledgement-campaigns/" },
      { name: "Tasks and service levels", status: "live", href: "/platform/workflows-and-approvals/" },
      { name: "Audit log", status: "live", href: "/security/" },
      { name: "Security awareness training", status: "soon", href: "/platform/security-awareness-training/" },
    ],
  },
];

export const ai = {
  id: "ai",
  eyebrow: "AI that drafts, people who decide",
  title: "Verity assistant",
  lead: "Ask about your programme in plain language, draft policies and procedures from your own records, and turn scan reports into findings you review. AI never approves, publishes or changes a record. A person always does.",
  link: { href: "/platform/ai-assistant/", label: "Read about the assistant" },
  features: [
    { icon: "sparkle", title: "Drafts that are clearly marked", text: "AI content carries its origin and goes through the same approval as yours." },
    { icon: "chat", title: "Answers from your own records", text: "Plain-language questions about controls, risks, vendors and findings." },
    { icon: "user-check", title: "A person always decides", text: "No AI output changes a status, a score or a decision on its own." },
  ] satisfies Feature[],
};

export const steps: { icon: IconName; title: string; text: string }[] = [
  { icon: "stack", title: "Choose your frameworks", text: "Start with the SOC 2 library on day one and add more as new libraries arrive." },
  { icon: "user-check", title: "Give every control an owner", text: "Assign people and groups, set due dates, and make sure nothing is left unowned." },
  { icon: "plug", title: "Collect and connect", text: "Upload evidence, import your asset and vendor lists, and connect GitHub." },
  { icon: "seal", title: "Monitor and prove", text: "Watch readiness, keep evidence fresh, and give auditors a link instead of a folder." },
];

export const trace = {
  eyebrow: "One connected record",
  title: "Follow any finding to the proof behind it.",
  lead: "A vulnerability, the asset it sits on, the risk it creates, the control that treats it and the evidence that proves it are linked records in Verity, not five spreadsheets. Every step is in the audit log.",
};

export const frameworksTeaser = {
  eyebrow: "Frameworks",
  title: "Every framework you answer to, on one set of controls.",
  lead: "SOC 2 ships today. Libraries for international standards and for the regulators our customers report to in Pakistan, the UAE, Australia, the United States and Europe are on the way.",
  note: "Verity organises the work. Certification and attestation come from your auditor or certification body.",
};

export const industriesTeaser = {
  eyebrow: "Industries",
  title: "Built for organisations that have to prove it.",
  lead: "Banks, payment companies, hospitals, software companies and public bodies answer to different rulebooks. Verity organises the work the same way for all of them.",
};

export const integrationsTeaser = {
  eyebrow: "Integrations",
  title: "Checks that run on the systems you already use.",
  lead: "Connect GitHub today and seven automated checks run every day. Connections for cloud, identity, ticketing and observability are coming next.",
  note: "A broken connection shows as an error, never as a failed control.",
};

export const securityTeaser = {
  eyebrow: "Security at Verity",
  title: "Built like the controls it tracks.",
  lead: "Banks and regulators ask how we protect the evidence they keep with us. These answers come from how the platform is built.",
  items: [
    { icon: "lock", title: "Sealed workspaces", text: "Each workspace is isolated by the database itself on every query, and automated tests prove it." },
    { icon: "users", title: "Least-privilege access", text: "Six built-in roles, groups and granular permissions for each module and action." },
    { icon: "fingerprint", title: "Two-factor for administrators", text: "Require two-factor sign-in for administrators, with a 12-character password rule by default." },
    { icon: "calendar", title: "Time-boxed auditor access", text: "External auditors and consultants get access windows that close on their own." },
    { icon: "scroll", title: "Append-only audit log", text: "Every change records who, when, before and after. Nobody can edit or delete it, administrators included." },
    { icon: "key", title: "Secrets encrypted", text: "Connection tokens and two-factor secrets are encrypted before they reach the database." },
  ] satisfies { icon: IconName; title: string; text: string }[],
};

export const docsTeaser = {
  eyebrow: "Documentation",
  title: "Learn Verity task by task.",
  lead: "Step-by-step guides with screenshots for every module, searchable from anywhere with ⌘K.",
  links: [
    { icon: "rocket", title: "Your first half hour", href: "/docs/get-started/quick-start/", text: "Get a new workspace useful fast." },
    { icon: "shield", title: "Controls", href: "/docs/compliance/controls/", text: "Give every control an owner." },
    { icon: "folder", title: "Evidence", href: "/docs/compliance/evidence/", text: "Collect proof and keep it fresh." },
    { icon: "handshake", title: "Vendors", href: "/docs/vendors/overview/", text: "Run the twelve-stage lifecycle." },
    { icon: "bug", title: "Vulnerabilities", href: "/docs/vulnerabilities/findings-and-priority/", text: "Prioritise and remediate on time." },
    { icon: "gear", title: "Administration", href: "/docs/admin/people/", text: "People, roles and the audit log." },
  ] satisfies { icon: IconName; title: string; href: string; text: string }[],
};

export const faqs: { q: string; a: string }[] = [
  { q: "Which frameworks can we use today?", a: "The SOC 2 library ships with every workspace: 61 criteria mapped to 114 control templates. You can add controls of your own today. Libraries for ISO/IEC 27001, PCI DSS, NIST, HIPAA, GDPR and regional frameworks such as the State Bank of Pakistan's, the UAE's and APRA's are coming soon, on the same control set." },
  { q: "Is Verity only for SOC 2?", a: "No. Alongside frameworks and controls, Verity runs evidence, policies and acknowledgements, tasks with service levels, a risk register, the full third-party risk lifecycle, an asset inventory and vulnerability management, all linked to each other." },
  { q: "Does Verity certify us?", a: "No. Certifications and attestation reports are issued by independent auditors and certification bodies. Verity organises the controls, evidence and decisions they review, and gives auditors time-boxed access to see them." },
  { q: "How does Verity use AI?", a: "The Verity assistant is coming soon. Wherever AI helps in Verity, the rule is the same: it drafts and suggests, and a person decides. AI content is marked as such, goes through the same approval as anything a person writes, and cannot change a status, a score or a decision on its own." },
  { q: "Who can see our data?", a: "Only the people you invite, with the roles you give them. Each workspace is sealed by the database itself, every change is written to an append-only audit log, and external auditors get access windows that close on their own. Talk to us about hosting and data-residency requirements." },
  { q: "How is Verity priced?", a: "By plan, based on the modules and frameworks you need and the size of your organisation. Compare the plans on the pricing page, or talk to our team for a quote." },
  { q: "How do we get started?", a: "Start a trial and follow the Get Started checklist, which tracks your real setup progress, or book a demo and we will walk through the parts that matter to you." },
];

export const finalCta = {
  title: "Be audit-ready every day, not just in audit week.",
  lead: "See how Verity fits the frameworks you answer to and the way your teams already work.",
};
