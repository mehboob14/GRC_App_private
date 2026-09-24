import { useState } from "react";
import {
  Badge,
  Button,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
  Tooltip,
  type IconName,
  type StatusFamily,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import {
  ago,
  type AutomatedTest,
  type Automation,
  type AutomationStatus,
  type Capability,
  type Outcome,
  type ProviderOption,
  type TestStatus,
} from "../api";
import { useAutomation, useRunConnections } from "../hooks";
import { ConnectGitHubDialog } from "./connect-github-dialog";
import { RequestIntegrationDialog } from "./request-integration-dialog";

const CONTROL_STATE: Record<
  AutomationStatus,
  { label: string; family: StatusFamily; icon: IconName; tone: string }
> = {
  passing: {
    label: "Passing",
    family: "success",
    icon: "check",
    tone: "bg-status-success-base",
  },
  failing: {
    label: "Failing",
    family: "danger",
    icon: "x",
    tone: "bg-status-danger-base",
  },
  error: {
    label: "Could not check",
    family: "warning",
    icon: "alert",
    tone: "bg-status-warning-base",
  },
  pending: {
    label: "First run in progress",
    family: "progress",
    icon: "clock",
    tone: "bg-status-progress-base",
  },
  not_connected: {
    label: "Not connected",
    family: "neutral",
    icon: "plug",
    tone: "bg-status-neutral-base",
  },
  manual: {
    label: "Evidenced manually",
    family: "neutral",
    icon: "users",
    tone: "bg-status-neutral-base",
  },
};

const TEST_STATE: Record<TestStatus, { label: string; family: StatusFamily }> =
  {
    pass: { label: "Pass", family: "success" },
    fail: { label: "Fail", family: "danger" },
    error: { label: "Could not check", family: "warning" },
    not_applicable: { label: "Not applicable", family: "neutral" },
    pending: { label: "Waiting", family: "progress" },
    not_connected: { label: "Not connected", family: "neutral" },
    not_available: { label: "Not automated yet", family: "pending" },
  };

const OUTCOME_ICON: Record<Outcome, { icon: IconName; className: string }> = {
  pass: { icon: "check", className: "text-status-success-text" },
  fail: { icon: "x", className: "text-status-danger-text" },
  error: { icon: "alert", className: "text-status-warning-text" },
  not_applicable: { icon: "info", className: "text-text-faint" },
};

const DAY_TONE: Record<Outcome | "none", string> = {
  pass: "bg-status-success-base",
  fail: "bg-status-danger-base",
  error: "bg-status-warning-base",
  not_applicable: "bg-status-neutral-base",
  none: "bg-surface-sunken",
};

const CONNECTABLE = new Set(["github"]);

function useAutomationActions(controlId: string) {
  const { principal } = useAuth();
  const automation = useAutomation(controlId);
  const run = useRunConnections(automation.kick);
  return {
    automation,
    run,
    canConnect: hasPermission(principal, "connectors:manage"),
    canRequest: hasPermission(principal, "controls:manage"),
  };
}

function RunButton({
  data,
  run,
  canConnect,
  size,
}: {
  data: Automation;
  run: ReturnType<typeof useRunConnections>;
  canConnect: boolean;
  size?: "sm";
}) {
  if (!canConnect || data.connection_ids.length === 0) return null;
  return (
    <Button
      size={size}
      loading={run.isPending || data.running}
      onClick={() => run.mutate(data.connection_ids)}
    >
      <Icon name="activity" className="size-4" />
      {data.running ? "Running" : "Run now"}
    </Button>
  );
}

/** Thirty days, one bar each: the monitoring history an auditor asks about. */
function History({ days }: { days: Automation["history"] }) {
  if (days.length === 0) return null;
  const tested = days.filter((d) => d.status !== "none");
  const clean = tested.filter((d) => d.status === "pass").length;
  return (
    <div>
      <div className="flex h-7 items-end gap-[3px]" aria-hidden>
        {days.map((d) => (
          <Tooltip
            key={d.day}
            content={`${new Date(`${d.day}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })}: ${
              d.status === "none" ? "not tested" : TEST_STATE[d.status].label
            }`}
          >
            <span
              className={cn(
                "block w-full flex-1 rounded-[2px]",
                d.status === "none" ? "h-2" : "h-7",
                DAY_TONE[d.status],
              )}
            />
          </Tooltip>
        ))}
      </div>
      <p className="mt-1.5 text-caption text-text-subtle">
        {tested.length === 0
          ? "No runs in the last 30 days"
          : `${clean} of ${tested.length} tested days fully passing`}
      </p>
    </div>
  );
}

function ProviderChip({
  option,
  canConnect,
  onConnect,
}: {
  option: ProviderOption;
  canConnect: boolean;
  onConnect: () => void;
}) {
  let state: React.ReactNode;
  if (option.connected) {
    state = (
      <span className="inline-flex items-center gap-1 text-caption font-semibold text-status-success-text">
        <Icon name="check" className="size-3.5" />
        Connected
      </span>
    );
  } else if (CONNECTABLE.has(option.key) && canConnect) {
    state = (
      <Button size="sm" variant="accent" onClick={onConnect}>
        Connect
      </Button>
    );
  } else if (option.status === "available") {
    state = <span className="text-caption text-text-subtle">Available</span>;
  } else if (option.status === "planned") {
    state = <Badge variant="neutral">{option.phase ?? "Planned"}</Badge>;
  } else {
    state = <span className="text-caption text-text-faint">Not in plan</span>;
  }
  return (
    <li
      className={cn(
        "flex items-center gap-2.5 rounded-lg border px-3 py-2",
        option.connected
          ? "border-status-success-border bg-status-success-bg"
          : "border-border bg-surface-primary",
      )}
    >
      <ConnectorLogo id={option.key} name={option.name} size={26} />
      <span className="min-w-0 flex-1 truncate text-body-sm font-semibold text-text-primary">
        {option.name}
      </span>
      {state}
    </li>
  );
}

function CapabilityBlock({
  capability,
  canConnect,
  canRequest,
  onConnect,
  onRequest,
}: {
  capability: Capability;
  canConnect: boolean;
  canRequest: boolean;
  onConnect: () => void;
  onRequest: (capability: string) => void;
}) {
  const connected = capability.providers.some((p) => p.connected);
  const connectable = capability.providers.some(
    (p) => p.status === "available",
  );
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-body-md font-semibold text-text-primary">
            {capability.name}
          </p>
          <p className="text-caption text-text-subtle">
            {connected
              ? "Connected. Tests run daily."
              : connectable
                ? "Connect any one of these."
                : "None of these connect yet. Request yours."}
          </p>
        </div>
        {canRequest ? (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => onRequest(capability.key)}
          >
            Use something else?
          </Button>
        ) : null}
      </div>
      <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {capability.providers.map((option) => (
          <ProviderChip
            key={option.key}
            option={option}
            canConnect={canConnect}
            onConnect={onConnect}
          />
        ))}
      </ul>
    </div>
  );
}

function TestRow({ test }: { test: AutomatedTest }) {
  const [open, setOpen] = useState(test.status === "fail");
  const state = TEST_STATE[test.status];
  const failing = test.results.filter((r) => r.outcome === "fail").length;
  const hasResults = test.results.length > 0;
  return (
    <li className="rounded-lg border border-border">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        disabled={!hasResults}
      >
        <StatusPill
          status={state.family}
          label={state.label}
          className="shrink-0"
        />
        <span className="min-w-0 flex-1">
          <span className="block truncate text-body-md font-semibold text-text-primary">
            {test.name}
          </span>
          <span className="block truncate text-caption text-text-subtle">
            {hasResults
              ? `${test.results.length} checked${failing ? `, ${failing} failing` : ""}. ${ago(test.last_run_at)}`
              : test.description}
          </span>
        </span>
        <Badge variant="neutral" className="hidden sm:inline-flex">
          {test.coverage === "full" ? "Full" : "Partial"}
        </Badge>
        {hasResults ? (
          <Icon
            name="chev"
            className={cn(
              "size-4 text-text-subtle transition-transform",
              open && "rotate-180",
            )}
          />
        ) : null}
      </button>
      {open && hasResults ? (
        <div className="border-t border-border px-4 py-3">
          <ul className="divide-y divide-border">
            {test.results.map((r) => {
              const icon = OUTCOME_ICON[r.outcome];
              return (
                <li
                  key={`${r.connection_id}:${r.resource_name}`}
                  className="flex items-start gap-2.5 py-2"
                >
                  <Icon
                    name={icon.icon}
                    className={cn("mt-0.5 size-4 shrink-0", icon.className)}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-body-sm font-semibold text-text-primary">
                      {r.resource_name}
                    </span>
                    <span className="block text-caption text-text-secondary">
                      {r.summary}
                    </span>
                  </span>
                  {r.url ? (
                    <a
                      href={r.url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label={`Open ${r.resource_name}`}
                      className="shrink-0 rounded-sm p-1 text-text-subtle hover:text-action-accent"
                    >
                      <Icon name="export" className="size-4" />
                    </a>
                  ) : null}
                </li>
              );
            })}
          </ul>
          {failing > 0 ? (
            <p className="mt-2 flex items-start gap-2 rounded-md bg-surface-sunken px-3 py-2 text-caption text-text-secondary">
              <Icon
                name="lightning"
                className="mt-0.5 size-3.5 shrink-0 text-action-accent"
              />
              {test.remediation}
            </p>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

/** One line under the status: what is running, or what it takes to start. */
function headline(data: Automation): string {
  const tests = data.tests_total === 1 ? "1 test" : `${data.tests_total} tests`;
  switch (data.status) {
    case "manual":
      return "No connected system can prove this control yet.";
    case "not_connected":
      return data.capabilities.some((c) =>
        c.providers.some((p) => p.status === "available"),
      )
        ? `${tests} ready. Connect any one system below to run ${data.tests_total === 1 ? "it" : "them"}.`
        : "No supported system yet. Request the one you use.";
    case "pending":
      return "Collecting from the connected system now.";
    default:
      return `${data.tests_running} of ${tests} running. Last run ${ago(data.last_run_at)}.`;
  }
}

/** The Automation tab: what proves this control, what to connect, and what the last run found. */
export function AutomationPanel({ controlId }: { controlId: string }) {
  const { automation, run, canConnect, canRequest } =
    useAutomationActions(controlId);
  const [connecting, setConnecting] = useState(false);
  const [requesting, setRequesting] = useState<string | null | false>(false);
  const data = automation.data;

  if (automation.isError) {
    return (
      <ErrorState
        title="Automation could not load"
        onRetry={() => void automation.refetch()}
      />
    );
  }
  if (automation.isLoading || !data) {
    return <Skeleton className="h-72 w-full rounded-lg" />;
  }
  const state = CONTROL_STATE[data.status];
  const capabilities = data.capabilities.map((c) => ({
    key: c.key,
    name: c.name,
  }));

  return (
    <div className="space-y-4">
      <section className="rounded-lg border border-border bg-surface-primary p-5">
        <div className="flex flex-wrap items-start gap-4">
          <span
            className={cn(
              "grid size-11 shrink-0 place-items-center rounded-xl text-white",
              state.tone,
            )}
          >
            <Icon name={state.icon} className="size-5" />
          </span>
          <div className="min-w-0 flex-1">
            <p className="font-display text-title-md text-text-primary">
              {state.label}
            </p>
            <p className="text-body-sm text-text-subtle">{headline(data)}</p>
          </div>
          <div className="flex gap-2">
            {canRequest ? (
              <Button variant="secondary" onClick={() => setRequesting(null)}>
                <Icon name="plus" className="size-4" />
                Request integration
              </Button>
            ) : null}
            <RunButton data={data} run={run} canConnect={canConnect} />
          </div>
        </div>
        {data.history.some((d) => d.status !== "none") ? (
          <div className="mt-4">
            <History days={data.history} />
          </div>
        ) : null}
        {data.requests.length > 0 ? (
          <p className="mt-3 flex flex-wrap items-center gap-1.5 text-caption text-text-subtle">
            Requested:
            {data.requests.map((r) => (
              <Badge key={r.id} variant="role">
                {r.provider_name}
              </Badge>
            ))}
          </p>
        ) : null}
      </section>

      {data.capabilities.map((capability) => (
        <CapabilityBlock
          key={capability.key}
          capability={capability}
          canConnect={canConnect}
          canRequest={canRequest}
          onConnect={() => setConnecting(true)}
          onRequest={(key) => setRequesting(key)}
        />
      ))}

      {data.tests.length > 0 ? (
        <section>
          <h3 className="type-overline mb-2">Tests</h3>
          <ul className="space-y-2">
            {data.tests.map((test) => (
              <TestRow key={test.key} test={test} />
            ))}
          </ul>
        </section>
      ) : null}

      <ConnectGitHubDialog
        open={connecting}
        onOpenChange={setConnecting}
        onConnected={automation.kick}
      />
      <RequestIntegrationDialog
        open={requesting !== false}
        onOpenChange={(open) => (open ? null : setRequesting(false))}
        controlId={controlId}
        capabilities={capabilities}
        defaultCapability={requesting || null}
      />
    </div>
  );
}

/** The control header's action: run the tests when a system is connected,
 *  otherwise open the Automation tab to connect one. */
export function AutomationHeaderButton({
  controlId,
  onOpen,
}: {
  controlId: string;
  onOpen: () => void;
}) {
  const { automation, run, canConnect } = useAutomationActions(controlId);
  const data = automation.data;
  if (!data || data.status === "manual") return null;
  if (canConnect && data.connection_ids.length > 0) {
    return <RunButton data={data} run={run} canConnect={canConnect} />;
  }
  return (
    <Button onClick={onOpen}>
      <Icon name="plug" className="size-4" />
      Automate
    </Button>
  );
}

/** The Overview card: status, what is connected, and the way into the tab. */
export function AutomationSummary({
  controlId,
  onOpen,
}: {
  controlId: string;
  onOpen: () => void;
}) {
  const { automation, run, canConnect } = useAutomationActions(controlId);
  const data = automation.data;
  if (automation.isError) return null;
  if (!data) return <Skeleton className="h-24 w-full rounded-lg" />;
  const state = CONTROL_STATE[data.status];
  const connected = data.capabilities.flatMap((c) =>
    c.providers.filter((p) => p.connected).map((p) => p.name),
  );
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-display text-title-md text-text-primary">
          Automation
        </h2>
        <StatusPill status={state.family} label={state.label} />
        <span className="ml-auto flex gap-2">
          <RunButton data={data} run={run} canConnect={canConnect} size="sm" />
          <Button size="sm" variant="secondary" onClick={onOpen}>
            {data.status === "not_connected" ? "Connect" : "Open"}
            <Icon name="arrowr" className="size-4" />
          </Button>
        </span>
      </div>
      <p className="mt-2 text-body-sm text-text-subtle">
        {data.status === "manual"
          ? "Evidenced by people. Request an integration if a system you use could prove it."
          : connected.length > 0
            ? `${data.tests_running} of ${data.tests_total} tests running on ${connected.join(", ")}. Last run ${ago(data.last_run_at)}.`
            : `${data.tests_total} tests ready. Connect ${data.capabilities.map((c) => c.name.toLowerCase()).join(" or ")} to run them.`}
      </p>
    </section>
  );
}
