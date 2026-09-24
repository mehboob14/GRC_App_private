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
  Outcome | "pending" | "not_connected" | "not_available";

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
};

export type AutomationStatus =
  "passing" | "failing" | "error" | "pending" | "not_connected" | "manual";

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
};

export const connectorKeys = {
  connections: ["connections"] as const,
  providers: ["connector-providers"] as const,
  requests: ["integration-requests"] as const,
  automation: (controlId: string) => ["control-automation", controlId] as const,
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

export const disconnectConnection = (connectionId: string, reason: string) =>
  apiFetch<Connection>(`/connections/${connectionId}/disconnect`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });

export const getAutomation = (controlId: string) =>
  apiFetch<Automation>(`/controls/${controlId}/automation`);

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
