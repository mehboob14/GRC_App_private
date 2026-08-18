// The 40 integrations Verity supports. Names and categories only — no vendor
// domain, because no logo is fetched from a third-party host (see
// ConnectorLogo); bundled marks will be keyed by `id`.
//
// There is deliberately NO health/status field: nothing is connected until the
// connector sync backend lands in Phase 2, and a compliance product must never
// display an invented sync time. The UI shows every provider as "Not connected".
//
// `syncs` describes what the Phase 2 sync will collect from that provider —
// the evidence a SOC 2 auditor asks for. It is a scope statement, not data:
// no counts, no dates, nothing that reads as a result. Where a provider holds
// secrets, the line says "names only", because rule 8 forbids pulling secret
// material into the platform.

export const CONNECTOR_CATEGORIES = [
  "Cloud",
  "Identity",
  "Code & CI/CD",
  "Endpoint",
  "Ticketing",
  "Communication",
  "HR",
  "Data & Monitoring",
] as const;

export type ConnectorCategory = (typeof CONNECTOR_CATEGORIES)[number];

/**
 * Deep link to the catalogue pre-filtered to identity providers. It lives here
 * so the category literal is never retyped at a call site: the page matches the
 * label exactly, and a near-miss (the control library's own "Identity & Access
 * Management") would silently match nothing.
 */
export const IDENTITY_CONNECTORS_PATH = `/connectors?category=${encodeURIComponent(
  "Identity" satisfies ConnectorCategory,
)}`;

export type Connector = {
  id: string;
  name: string;
  categories: ConnectorCategory[];
  /** What Phase 2 will collect as evidence. 2–4 items, no numbers, no dates. */
  syncs: string[];
};

export const CONNECTORS: Connector[] = [
  // Cloud & infrastructure
  {
    id: "aws",
    name: "Amazon Web Services",
    categories: ["Cloud"],
    syncs: [
      "IAM users, roles and attached policies",
      "CloudTrail trail configuration and log file validation",
      "S3 bucket encryption and public-access settings",
      "Security group ingress rules",
    ],
  },
  {
    id: "gcp",
    name: "Google Cloud",
    categories: ["Cloud"],
    syncs: [
      "IAM policy bindings and service accounts",
      "Cloud Audit Logs configuration",
      "Cloud Storage bucket access controls and encryption",
      "VPC firewall rules",
    ],
  },
  {
    id: "azure",
    name: "Microsoft Azure",
    categories: ["Cloud"],
    syncs: [
      "RBAC role assignments across subscriptions",
      "Activity log and diagnostic settings",
      "Storage account encryption and public-access configuration",
      "Network security group rules",
    ],
  },
  {
    id: "digitalocean",
    name: "DigitalOcean",
    categories: ["Cloud"],
    syncs: [
      "Team members and their access level",
      "Cloud firewall rules",
      "Spaces bucket permissions",
      "Managed database backup and encryption settings",
    ],
  },
  {
    id: "heroku",
    name: "Heroku",
    categories: ["Cloud"],
    syncs: [
      "Team members and app collaborators",
      "App, dyno and add-on inventory",
      "TLS certificate and custom domain configuration",
    ],
  },
  {
    id: "cloudflare",
    name: "Cloudflare",
    categories: ["Cloud"],
    syncs: [
      "Account members and API token scopes",
      "WAF and firewall rule configuration",
      "TLS, HSTS and minimum TLS version settings",
      "DNS zone records",
    ],
  },
  {
    id: "kubernetes",
    name: "Kubernetes",
    categories: ["Cloud"],
    syncs: [
      "RBAC roles, cluster roles and bindings",
      "Namespace and pod security standards",
      "Audit policy configuration",
      "Secret inventory · names only, never values",
    ],
  },
  {
    id: "terraform",
    name: "Terraform Cloud",
    categories: ["Cloud"],
    syncs: [
      "Workspace membership and team access",
      "Run, plan and apply history",
      "Policy check results",
      "State version and encryption settings",
    ],
  },

  // Identity & access
  {
    id: "okta",
    name: "Okta",
    categories: ["Identity"],
    syncs: [
      "User and group directory with lifecycle state",
      "Application access assignments",
      "MFA factor enrollment per user",
      "Sign-on and password policies",
    ],
  },
  {
    id: "entra",
    name: "Microsoft Entra ID",
    categories: ["Identity"],
    syncs: [
      "Users, groups and directory role assignments",
      "Conditional access policies",
      "MFA registration state per user",
      "Privileged role activations",
    ],
  },
  {
    id: "gws",
    name: "Google Workspace",
    categories: ["Identity"],
    syncs: [
      "Users, groups and organisational units",
      "2-step verification enrollment per user",
      "Admin role assignments",
      "Third-party OAuth app grants",
    ],
  },
  {
    id: "onelogin",
    name: "OneLogin",
    categories: ["Identity"],
    syncs: [
      "User and role directory",
      "Application access assignments",
      "MFA factor enrollment per user",
      "Security and password policies",
    ],
  },
  {
    id: "jumpcloud",
    name: "JumpCloud",
    categories: ["Identity", "Endpoint"],
    syncs: [
      "User and user-group directory",
      "Device-to-user bindings",
      "MFA enrollment per user",
      "System policies applied to managed devices",
    ],
  },
  {
    id: "auth0",
    name: "Auth0",
    categories: ["Identity"],
    syncs: [
      "Tenant users and role assignments",
      "Connection and MFA configuration",
      "Application grants and API scopes",
      "Tenant log stream configuration",
    ],
  },
  {
    id: "duo",
    name: "Duo Security",
    categories: ["Identity"],
    syncs: [
      "Enrolled users and their registered devices",
      "Authentication policies per application",
      "Protected application inventory",
      "Administrator accounts and roles",
    ],
  },

  // Code & CI/CD
  {
    id: "github",
    name: "GitHub",
    categories: ["Code & CI/CD"],
    syncs: [
      "Organisation members, teams and repository access",
      "Branch protection and required review rules",
      "Pull request review and approval history",
      "Dependabot and code scanning alerts",
    ],
  },
  {
    id: "gitlab",
    name: "GitLab",
    categories: ["Code & CI/CD"],
    syncs: [
      "Group and project membership with access level",
      "Protected branch and merge approval rules",
      "Merge request approval history",
      "Pipeline and security scan results",
    ],
  },
  {
    id: "bitbucket",
    name: "Bitbucket",
    categories: ["Code & CI/CD"],
    syncs: [
      "Workspace members and repository permissions",
      "Branch restrictions and merge checks",
      "Pull request approval history",
      "Repository access keys · names only",
    ],
  },
  {
    id: "circleci",
    name: "CircleCI",
    categories: ["Code & CI/CD"],
    syncs: [
      "Project and context access",
      "Pipeline and workflow run history",
      "Manual approval job records",
      "Environment variable inventory · names only",
    ],
  },
  {
    id: "jenkins",
    name: "Jenkins",
    categories: ["Code & CI/CD"],
    syncs: [
      "User accounts and matrix permissions",
      "Job configuration and build history",
      "Installed plugin inventory and versions",
      "Credential store inventory · names only",
    ],
  },

  // Endpoint & devices
  {
    id: "jamf",
    name: "Jamf",
    categories: ["Endpoint"],
    syncs: [
      "Managed device inventory and assigned user",
      "FileVault disk encryption state per device",
      "OS version and patch level",
      "Configuration profiles applied",
    ],
  },
  {
    id: "kandji",
    name: "Kandji",
    categories: ["Endpoint"],
    syncs: [
      "Managed device inventory and assigned user",
      "FileVault disk encryption state per device",
      "OS patch level against the enforced baseline",
      "Blueprint library items applied",
    ],
  },
  {
    id: "intune",
    name: "Microsoft Intune",
    categories: ["Endpoint"],
    syncs: [
      "Enrolled device inventory and assigned user",
      "BitLocker disk encryption state per device",
      "Compliance policy evaluation per device",
      "Update ring configuration",
    ],
  },
  {
    id: "crowdstrike",
    name: "CrowdStrike",
    categories: ["Endpoint"],
    syncs: [
      "Sensor installation coverage per host",
      "Detection and incident history",
      "Host group prevention policy assignment",
      "Sensor version and update state",
    ],
  },
  {
    id: "sentinelone",
    name: "SentinelOne",
    categories: ["Endpoint"],
    syncs: [
      "Agent installation coverage per endpoint",
      "Threat detection and resolution history",
      "Endpoint policy assignment",
      "Agent version and update state",
    ],
  },

  // Ticketing & project
  {
    id: "jira",
    name: "Jira",
    categories: ["Ticketing"],
    syncs: [
      "Issue records for linked change and incident workflows",
      "Workflow status transitions with actor and timestamp",
      "Approval and resolution history",
      "Project permission schemes",
    ],
  },
  {
    id: "linear",
    name: "Linear",
    categories: ["Ticketing"],
    syncs: [
      "Issue records and their state history",
      "Team and project membership",
      "Workflow state configuration",
      "Cycle start and completion dates",
    ],
  },
  {
    id: "asana",
    name: "Asana",
    categories: ["Ticketing"],
    syncs: [
      "Task records with assignee and completion date",
      "Project and team membership",
      "Approval task outcomes",
      "Custom field values used for tracking",
    ],
  },
  {
    id: "servicenow",
    name: "ServiceNow",
    categories: ["Ticketing"],
    syncs: [
      "Change request records and their approvals",
      "Incident and problem tickets with resolution time",
      "CMDB configuration items",
      "Assignment group membership",
    ],
  },

  // Communication
  {
    id: "slack",
    name: "Slack",
    categories: ["Communication"],
    syncs: [
      "Workspace members and account type",
      "Channel inventory and privacy setting",
      "Retention and export policy configuration",
      "Installed app and integration inventory",
    ],
  },
  {
    id: "teams",
    name: "Microsoft Teams",
    categories: ["Communication"],
    syncs: [
      "Team and channel membership",
      "Guest access and external sharing settings",
      "Meeting recording policy configuration",
      "Retention policy configuration",
    ],
  },
  {
    id: "zoom",
    name: "Zoom",
    categories: ["Communication"],
    syncs: [
      "User accounts and assigned licences",
      "Meeting security and encryption settings",
      "Cloud recording and retention settings",
      "Admin role assignments",
    ],
  },

  // HR & people
  {
    id: "workday",
    name: "Workday",
    categories: ["HR"],
    syncs: [
      "Worker roster with hire and termination dates",
      "Job, department and manager assignments",
      "Onboarding and offboarding task completion",
      "Background check and policy acknowledgement records",
    ],
  },
  {
    id: "bamboohr",
    name: "BambooHR",
    categories: ["HR"],
    syncs: [
      "Employee roster with hire and termination dates",
      "Job title, department and reporting line",
      "Onboarding and offboarding task completion",
      "Training and policy acknowledgement records",
    ],
  },
  {
    id: "rippling",
    name: "Rippling",
    categories: ["HR"],
    syncs: [
      "Employee roster with employment status and dates",
      "Onboarding and offboarding workflow completion",
      "Device and application assignments per employee",
      "Role and department data",
    ],
  },
  {
    id: "gusto",
    name: "Gusto",
    categories: ["HR"],
    syncs: [
      "Employee roster with hire and termination dates",
      "Department and manager assignments",
      "Employment type and status changes",
    ],
  },

  // Data & monitoring
  {
    id: "snowflake",
    name: "Snowflake",
    categories: ["Data & Monitoring"],
    syncs: [
      "Users, roles and grant hierarchy",
      "Network policy and IP allow-list configuration",
      "Login history and MFA enforcement",
      "Retention, masking and encryption settings",
    ],
  },
  {
    id: "datadog",
    name: "Datadog",
    categories: ["Data & Monitoring"],
    syncs: [
      "Monitor and alert rule configuration",
      "Triggered alert and notification history",
      "User accounts and role assignments",
      "Log retention and index configuration",
    ],
  },
  {
    id: "pagerduty",
    name: "PagerDuty",
    categories: ["Data & Monitoring"],
    syncs: [
      "On-call schedules and escalation policies",
      "Incident timeline with acknowledgement and resolution",
      "Service and team ownership",
      "User accounts and contact methods",
    ],
  },
  {
    id: "sentry",
    name: "Sentry",
    categories: ["Data & Monitoring"],
    syncs: [
      "Organisation members and team access",
      "Alert rule configuration and issue ownership",
      "Release and deploy history",
      "Data scrubbing and PII filtering settings",
    ],
  },
];
