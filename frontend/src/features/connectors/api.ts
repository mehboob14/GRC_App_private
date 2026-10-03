import { apiFetch } from "@/lib/api/client";

export type RunStatus = "running" | "completed" | "failed";

export type Run = {
  id: string;
  trigger: "manual" | "schedule";
  status: RunStatus;
  started_at: string;
  finished_at: string | null;
  resources: number;
  passed: number;
  failed: number;
  errored: number;
  error: string | null;
  evidence_id: string | null;
};

/** How much of a connection's inventory the checks look at. */
export type Scope = { listed: number; in_scope: number; excluded: number };

export type ConnectionScope = Scope & {
  connection_id: string;
  account: string;
};

/** One repository a connection can see, and whether it is checked. */
export type ConnectionResource = {
  external_id: string;
  name: string;
  url: string | null;
  private: boolean;
  fork: boolean;
  archived: boolean;
  empty: boolean;
  scope: "in_scope" | "excluded";
  reason: string | null;
  /** A system decision is re-derived every run; a person's is kept. */
  decided_by: "system" | "person";
  decided_by_name: string | null;
  decided_at: string | null;
};

export type Connection = {
  id: string;
  provider: string;
  provider_name: string;
  account_login: string;
  account_type: "organization" | "user";
  display_name: string;
  status: "active" | "disconnected";
  credential_hint: string | null;
  credential_expires_at: string | null;
  last_run_at: string | null;
  last_success_at: string | null;
  last_error: string | null;
  error_streak: number;
  created_at: string;
  disconnected_at: string | null;
  latest_run: Run | null;
  scope: Scope | null;
};

export type ProviderStatus = "available" | "planned" | "not_planned";

export type Provider = {
  key: string;
  name: string;
  status: ProviderStatus;
  phase: string | null;
  capabilities: string[];
};

export type ProviderOption = {
  key: string;
  name: string;
  status: ProviderStatus;
  phase: string | null;
  connected: boolean;
  runs_check: boolean;
};

export type Capability = {
  key: string;
  name: string;
  description: string;
  providers: ProviderOption[];
};

export type Outcome = "pass" | "fail" | "error" | "not_applicable";

export type TestResult = {
  connection_id: string;
  account: string;
  resource_type: string;
  resource_name: string;
  outcome: Outcome;
  summary: string;
  url: string | null;
  observed_at: string;
};

export type TestStatus =
  Outcome | "pending" | "stale" | "not_connected" | "not_available";

/** Whether a workspace can have a check run: a connected system runs it, a
 *  collector ships and only the connection is missing, or it is still planned. */
export type Availability = "running" | "ready" | "planned" | "not_planned";

/** A connected system (`connector`) or Verity's own modules (`platform`). */
export type CheckSource = "connector" | "platform";

export type SourceState = "connected" | "available" | "planned" | "not_planned";

export type AutomatedTest = {
  key: string;
  name: string;
  description: string;
  remediation: string;
  frequency: "daily" | "weekly";
  coverage: "full" | "partial";
  capabilities: string[];
  status: TestStatus;
  results: TestResult[];
  counts: Record<Outcome, number>;
  last_run_at: string | null;
  /** Why this check is evidence for this control, and what it does not prove. */
  rationale: string | null;
  /** The artifacts the check collects. */
  evidence_kinds: string[];
  source: CheckSource;
  availability: Availability;
  /** The capabilities the check needs, each with the providers that supply it. */
  needs: Capability[];
};

export type ComposeMode = "automated" | "hybrid" | "manual";

/** One capability a control's checks need, with the best state any provider is in. */
export type CompositionSource = {
  key: string;
  name: string;
  kind: CheckSource;
  state: SourceState;
  providers: string[];
  provider_keys: string[];
  checks: number;
};

export type Composition = {
  /** By design, once every planned system ships. */
  mode: ComposeMode;
  checks_total: number;
  checks_running: number;
  checks_ready: number;
  checks_planned: number;
  sources: CompositionSource[];
  items_total: number;
  items_automatic: number;
  items_planned: number;
  items_platform: number;
  items_manual: number;
};

/** How an expected piece of evidence reaches the control right now. */
export type EvidenceState =
  | "automatic"
  | "partial"
  | "when_connected"
  | "planned"
  | "platform"
  | "manual";

export type ExpectedEvidence = {
  key: string;
  name: string;
  assurance: "design" | "operating";
  cadence:
    | "annual"
    | "quarterly"
    | "monthly"
    | "on_change"
    | "per_event"
    | "once"
    | "ongoing";
  source: "upload" | "platform";
  module: string | null;
  state: EvidenceState;
  automated_by: { key: string; name: string; availability: Availability }[];
};

/** One criterion a control answers, with the shipped coverage and why. */
export type CriterionMapping = {
  requirement_id: string;
  requirement_key: string;
  code: string;
  name: string;
  trust_services_category: string;
  coverage: "full" | "partial" | null;
  rationale: string | null;
  /** `workspace` is a link this workspace added itself: nobody wrote a reason. */
  origin: "library" | "workspace";
};

export type AutomationStatus =
  | "passing"
  | "failing"
  | "error"
  | "stale"
  | "not_applicable"
  | "pending"
  | "not_connected"
  | "manual";

export type IntegrationRequest = {
  id: string;
  provider_name: string;
  capability_key: string | null;
  control_id: string | null;
  note: string | null;
  status: "open" | "planned" | "available" | "declined";
  created_at: string;
};

export type Automation = {
  control_id: string;
  mode: "automated" | "hybrid" | "manual";
  status: AutomationStatus;
  tests_total: number;
  tests_running: number;
  last_run_at: string | null;
  running: boolean;
  connection_ids: string[];
  capabilities: Capability[];
  tests: AutomatedTest[];
  history: { day: string; status: Outcome | "none" }[];
  requests: IntegrationRequest[];
  scopes: ConnectionScope[];
  composition: Composition | null;
  evidence: ExpectedEvidence[];
  mappings: CriterionMapping[];
};

/** What evidences each control, for the register. */
export type ControlComposition = {
  control_id: string;
  composition: Composition;
  automation_status: AutomationStatus | null;
};

export type ChainCheck = {
  key: string;
  name: string;
  source: CheckSource;
  availability: Availability;
  status: TestStatus;
  coverage: "full" | "partial";
  rationale: string | null;
  evidence_kinds: string[];
  capabilities: string[];
};

export type ControlChain = {
  control_id: string;
  composition: Composition;
  automation_status: AutomationStatus | null;
  checks: ChainCheck[];
  evidence: ExpectedEvidence[];
};

export type RequirementChain = {
  requirement: {
    id: string;
    requirement_key: string;
    code: string;
    name: string;
    description: string | null;
    category: string;
    trust_services_category: string;
  };
  /** Decided by the same rules as the dashboard. */
  state: "met" | "partly" | "not_started" | "no_controls";
  controls: {
    control_id: string;
    code: string;
    name: string;
    status: string;
    owner_name: string | null;
    coverage: "full" | "partial" | null;
    rationale: string | null;
    origin: "library" | "workspace";
    ready: boolean;
    chain: ControlChain | null;
  }[];
};

export const connectorKeys = {
  connections: ["connections"] as const,
  resources: (connectionId: string) => ["connection-resources", connectionId] as const,
  providers: ["connector-providers"] as const,
  requests: ["integration-requests"] as const,
  automation: (controlId: string) => ["control-automation", controlId] as const,
  composition: ["control-composition"] as const,
  chain: (requirementId: string) => ["requirement-chain", requirementId] as const,
};

export const listConnections = () => apiFetch<Connection[]>("/connections");

export const listProviders = () =>
  apiFetch<Provider[]>("/connectors/providers");

export const connectGitHub = (token: string, account: string) =>
  apiFetch<Connection>("/connections", {
    method: "POST",
    body: JSON.stringify({
      provider: "github",
      token,
      account: account.trim() || null,
    }),
  });

export const runConnection = (connectionId: string) =>
  apiFetch<{ accepted: boolean }>(`/connections/${connectionId}/runs`, {
    method: "POST",
  });

export const listConnectionResources = (connectionId: string) =>
  apiFetch<ConnectionResource[]>(`/connections/${connectionId}/resources`);

/** Choose what the checks look at. One reason covers every exclusion in the call. */
export const setConnectionScope = (
  connectionId: string,
  decisions: { external_id: string; scope: "in_scope" | "excluded" }[],
  reason: string | null,
) =>
  apiFetch<ConnectionResource[]>(`/connections/${connectionId}/scope`, {
    method: "PUT",
    body: JSON.stringify({ decisions, reason }),
  });

export const disconnectConnection = (connectionId: string, reason: string) =>
  apiFetch<Connection>(`/connections/${connectionId}/disconnect`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

export const getAutomation = (controlId: string) =>
  apiFetch<Automation>(`/controls/${controlId}/automation`);

export const getControlComposition = () =>
  apiFetch<ControlComposition[]>("/control-composition");

export const getRequirementChain = (requirementId: string) =>
  apiFetch<RequirementChain>(`/requirements/${requirementId}/chain`);

export const listIntegrationRequests = () =>
  apiFetch<IntegrationRequest[]>("/integration-requests");

export const requestIntegration = (body: {
  provider_name: string;
  capability_key: string | null;
  control_id: string | null;
  note: string | null;
}) =>
  apiFetch<IntegrationRequest>("/integration-requests", {
    method: "POST",
    body: JSON.stringify(body),
  });

/** "just now", "12 min ago", "3 h ago", "2 d ago". */
export function ago(iso: string | null): string {
  if (!iso) return "Never";
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60_000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
}
