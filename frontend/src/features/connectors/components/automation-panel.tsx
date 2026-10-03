import {
  Badge,
  Button,
  Icon,
  Skeleton,
  StatusPill,
  Tooltip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import {
  ago,
  type Automation,
  type Capability,
  type ProviderOption,
} from "../api";
import { useRunConnections } from "../hooks";
import {
  CONTROL_STATE,
  DAY_TONE,
  TEST_STATE,
  useAutomationActions,
} from "./automation-meta";
import { ModeBadge, SourceChip } from "./composition-ui";

const CONNECTABLE = new Set(["github"]);

export function RunButton({
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
export function History({ days }: { days: Automation["history"] }) {
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

export function ProviderChip({
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

export function CapabilityBlock({
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

/** The Overview card: how the control is evidenced, its status, and the way into the tab. */
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
  const composition = data.composition;
  const connected = data.capabilities.flatMap((c) =>
    c.providers.filter((p) => p.connected).map((p) => p.name),
  );
  return (
    <section className="rounded-lg border border-border bg-surface-primary p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="font-display text-title-md text-text-primary">Checks</h2>
        {composition ? <ModeBadge mode={composition.mode} /> : null}
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
          ? "People provide the evidence. Request an integration if a system you use could prove it."
          : connected.length > 0
            ? `${data.tests_running} of ${data.tests_total} checks running on ${connected.join(", ")}. Last run ${ago(data.last_run_at)}.`
            : `${data.tests_total} checks ready. Connect ${data.capabilities.map((c) => c.name.toLowerCase()).join(" or ")} to run them.`}
      </p>
      {composition && composition.sources.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-2">
          {composition.sources.map((source) => (
            <li key={source.key}>
              <SourceChip source={source} />
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
