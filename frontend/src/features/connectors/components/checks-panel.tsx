import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Badge,
  Button,
  EmptyState,
  ErrorState,
  Icon,
  Skeleton,
  StatusPill,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  ago,
  type AutomatedTest,
  type Automation,
  type ExpectedEvidence,
} from "../api";
import {
  CONTROL_STATE,
  OUTCOME_ICON,
  TEST_STATE,
  useAutomationActions,
} from "./automation-meta";
import {
  CapabilityBlock,
  History,
  ProviderChip,
  RunButton,
} from "./automation-panel";
import {
  AVAILABILITY,
  CADENCE,
  compositionSentence,
  EVIDENCE_STATE,
} from "./composition-meta";
import {
  ModeBadge,
  ModuleLink,
  SourceChip,
  SourceMark,
} from "./composition-ui";
import { ConnectGitHubDialog } from "./connect-github-dialog";
import { RequestIntegrationDialog } from "./request-integration-dialog";
import { ScopeDialog } from "./scope-dialog";

/** The repositories on one connection that the provider does not offer a check on
 *  at the account's plan, which is not something a setting can fix. */
type PlanLimited = { connectionId: string; account: string; names: string[] };

function planLimited(test: AutomatedTest): PlanLimited[] {
  const byConnection = new Map<string, PlanLimited>();
  for (const result of test.results) {
    if (result.detail?.reason !== "plan") continue;
    const group = byConnection.get(result.connection_id) ?? {
      connectionId: result.connection_id,
      account: result.account,
      names: [],
    };
    group.names.push(result.resource_name);
    byConnection.set(result.connection_id, group);
  }
  return [...byConnection.values()];
}

/** Said once for the whole account, in place of the same sentence on every repository. */
function PlanNotice({
  group,
  canExclude,
  onExclude,
}: {
  group: PlanLimited;
  canExclude: boolean;
  onExclude: () => void;
}) {
  const [listing, setListing] = useState(false);
  const count = group.names.length;
  return (
    <div className="mt-3 rounded-md border border-border bg-surface-sunken px-3 py-3">
      <p className="flex items-start gap-2 text-body-sm font-semibold text-text-primary">
        <Icon
          name="info"
          className="mt-0.5 size-4 shrink-0 text-status-warning-text"
        />
        {count === 1 ? "1 repository" : `${count} repositories`} on{" "}
        {group.account} cannot be checked on the current GitHub plan
      </p>
      <p className="mt-1 text-body-sm text-text-secondary">
        GitHub offers this on private repositories only to paid plans. An
        account on Free does not get it, so the control cannot be met there.
        Your options:
      </p>
      <ul className="mt-1.5 list-disc space-y-0.5 pl-9 text-body-sm text-text-secondary">
        <li>Move the owning account to a paid plan.</li>
        <li>Make a repository public, if it can be.</li>
        <li>Leave them out of the checks, with a reason auditors will see.</li>
      </ul>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {canExclude ? (
          <Button size="sm" onClick={onExclude}>
            Leave these out
          </Button>
        ) : null}
        <button
          type="button"
          onClick={() => setListing((v) => !v)}
          aria-expanded={listing}
          className="text-body-sm font-semibold text-action-accent hover:underline"
        >
          {listing ? "Hide" : "Show"} the {count === 1 ? "repository" : `${count} repositories`}
        </button>
      </div>
      {listing ? (
        <ul className="mt-2 columns-1 gap-6 text-caption text-text-secondary sm:columns-2">
          {group.names.map((name) => (
            <li key={name} className="truncate">
              {name}
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** One line under the status: what is running, or what it takes to start. */
function headline(data: Automation): string {
  const checks =
    data.tests_total === 1 ? "1 check" : `${data.tests_total} checks`;
  switch (data.status) {
    case "manual":
      return "Nothing runs on this control, so there is no result to show.";
    case "not_connected":
      return (data.composition?.checks_ready ?? 0) > 0
        ? `${checks} ready. Connect any one system below to run ${data.tests_total === 1 ? "it" : "them"}.`
        : "None of these checks can run yet. They need systems that are planned. Request the one you use.";
    case "pending":
      return "Collecting from the connected system now.";
    case "stale":
      return `The last check was ${ago(data.last_run_at)}. Results older than two days are not counted until the checks run again.`;
    case "not_applicable":
      // Verified by nothing is not the same as passing: say so, and say what to do.
      return "The checks found nothing to check on this account, so none of them proves the control. Provide the evidence yourself.";
    default:
      return `${data.tests_running} of ${checks} running. Last run ${ago(data.last_run_at)}.`;
  }
}

function runningOn(test: AutomatedTest): string[] {
  return test.needs.flatMap((need) =>
    need.providers.filter((p) => p.connected && p.runs_check).map((p) => p.name),
  );
}

/** Where a check runs, in a few words: the software, or what it is waiting for. */
function runsOnLine(test: AutomatedTest): string {
  const needs = test.needs.map((n) => n.name).join(" and ");
  switch (test.availability) {
    case "running":
      return `Running on ${runningOn(test).join(" and ") || needs}`;
    case "ready":
      return `Ready to run on ${test.needs
        .flatMap((n) =>
          n.providers.filter((p) => p.runs_check).map((p) => p.name),
        )
        .join(" or ")}`;
    case "planned":
      return `Planned. Needs ${needs}`;
    default:
      return `Needs ${needs}, which is not in the plan yet`;
  }
}

function CheckRow({
  test,
  canConnect,
  onConnect,
  onExclude,
}: {
  test: AutomatedTest;
  canConnect: boolean;
  onConnect: () => void;
  onExclude: (group: PlanLimited) => void;
}) {
  const [open, setOpen] = useState(test.status === "fail");
  const state = TEST_STATE[test.status];
  // A repository the plan rules out is not a setting to fix, so it is said once
  // below and left out of the per-repository lines and the how-to-fix hint.
  const limited = planLimited(test);
  const limitedCount = limited.reduce((n, g) => n + g.names.length, 0);
  const rest = test.results.filter((r) => r.detail?.reason !== "plan");
  const failing = rest.filter((r) => r.outcome === "fail").length;
  const marks = test.needs.flatMap((n) =>
    n.providers
      .filter((p) =>
        test.availability === "running" ? p.connected && p.runs_check : p.runs_check || p.status !== "not_planned",
      )
      .slice(0, 3),
  );
  return (
    <li className="rounded-lg border border-border bg-surface-primary">
      <button
        type="button"
        className="flex w-full items-center gap-3 px-4 py-3 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
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
          <span className="flex items-center gap-2 text-caption text-text-subtle">
            <span className="flex -space-x-1.5" aria-hidden>
              {marks.slice(0, 3).map((p) => (
                <SourceMark
                  key={p.key}
                  providerKey={p.key}
                  name={p.name}
                  size={16}
                />
              ))}
            </span>
            <span className="truncate">
              {test.results.length > 0
                ? `${test.results.length} checked${failing ? `, ${failing} failing` : ""}${limitedCount ? `, ${limitedCount} not offered on the plan` : ""}. ${ago(test.last_run_at)}`
                : runsOnLine(test)}
            </span>
          </span>
        </span>
        <Badge variant="neutral" className="hidden sm:inline-flex">
          {test.coverage === "full" ? "Whole control" : "Part of the control"}
        </Badge>
        <Icon
          name="chev"
          className={cn(
            "size-4 text-text-subtle transition-transform",
            open && "rotate-180",
          )}
        />
      </button>

      {open ? (
        <div className="space-y-4 border-t border-border px-4 py-4">
          <p className="text-body-sm text-text-secondary">{test.description}</p>

          {test.rationale ? (
            <div>
              <p className="type-overline mb-1">What it proves here</p>
              <p className="text-body-sm text-text-secondary">
                {test.rationale}
              </p>
            </div>
          ) : null}

          {test.evidence_kinds.length > 0 ? (
            <div>
              <p className="type-overline mb-1.5">Evidence it collects</p>
              <ul className="flex flex-wrap gap-1.5">
                {test.evidence_kinds.map((kind) => (
                  <li key={kind}>
                    <Badge variant="neutral">{kind}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div>
            <p className="type-overline mb-1.5">
              {test.source === "platform" ? "Runs in" : "Runs on"}
              <span className="ml-2 font-normal normal-case text-text-subtle">
                {AVAILABILITY[test.availability]}
              </span>
            </p>
            <div className="space-y-2">
              {test.needs.map((need) => (
                <div key={need.key}>
                  <p className="mb-1 text-caption text-text-subtle">
                    {need.name}
                    {test.needs.length > 1 ? " is needed" : null}
                  </p>
                  <ul className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-3">
                    {need.providers.map((option) => (
                      <ProviderChip
                        key={option.key}
                        option={option}
                        canConnect={canConnect}
                        onConnect={onConnect}
                      />
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>

          {test.results.length > 0 ? (
            <div>
              <p className="type-overline mb-1">Last result</p>
              <ul className="divide-y divide-border">
                {rest.map((r) => {
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
              {limited.map((group) => (
                <PlanNotice
                  key={group.connectionId}
                  group={group}
                  canExclude={canConnect}
                  onExclude={() => onExclude(group)}
                />
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
    </li>
  );
}

function evidenceDetail(
  item: ExpectedEvidence,
  onOpenEvidence?: () => void,
): React.ReactNode {
  switch (item.state) {
    case "automatic":
      return "A running check collects this.";
    case "partial":
      return "Running checks collect some of this. Add the rest yourself.";
    case "when_connected":
      return "A check collects this once a system is connected. Until then, add it yourself.";
    case "planned":
      return "A planned check will collect this. Add it yourself for now.";
    case "platform":
      return (
        <>
          Kept in <ModuleLink module={item.module} />. Verity does not check it yet.
        </>
      );
    default:
      return onOpenEvidence ? (
        <>
          Add it on the{" "}
          <button
            type="button"
            onClick={onOpenEvidence}
            className="font-semibold text-action-accent hover:underline"
          >
            Evidence tab
          </button>
          .
        </>
      ) : (
        "Add it on the Evidence tab."
      );
  }
}

function EvidenceRow({
  item,
  onOpenEvidence,
}: {
  item: ExpectedEvidence;
  onOpenEvidence?: () => void;
}) {
  const state = EVIDENCE_STATE[item.state];
  const operating = item.assurance === "operating";
  return (
    <li className="flex items-start gap-3 rounded-lg border border-border bg-surface-primary px-4 py-3">
      <span
        className={cn(
          "mt-0.5 grid size-8 shrink-0 place-items-center rounded-md",
          operating
            ? "bg-action-accent-tint text-action-accent"
            : "bg-surface-sunken text-text-secondary",
        )}
      >
        <Icon name={item.source === "platform" ? "layers" : "doc"} className="size-4" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-body-md font-semibold text-text-primary">
          {item.name}
        </span>
        <span className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-caption text-text-subtle">
          <Badge variant={operating ? "role" : "neutral"}>
            {operating ? "Shows it operates" : "Shows it exists"}
          </Badge>
          <span>{CADENCE[item.cadence]}</span>
        </span>
        <span className="mt-1 block text-body-sm text-text-secondary">
          {evidenceDetail(item, onOpenEvidence)}
        </span>
        {item.automated_by.length > 0 ? (
          <span className="mt-1.5 flex flex-wrap gap-1.5">
            {item.automated_by.map((check) => (
              <Badge key={check.key} variant="neutral">
                {check.name}
              </Badge>
            ))}
          </span>
        ) : null}
      </span>
      <StatusPill
        status={state.family}
        label={state.label}
        className="hidden shrink-0 sm:inline-flex"
      />
    </li>
  );
}

/**
 * The Checks tab: how this control is evidenced, which software runs each check,
 * and what people or Verity modules provide. Written for the question an
 * auditor asks of a control: what proves it, and where does that come from.
 */
export function ChecksPanel({
  controlId,
  onOpenEvidence,
}: {
  controlId: string;
  onOpenEvidence?: () => void;
}) {
  const { automation, run, canConnect, canRequest } =
    useAutomationActions(controlId);
  const [connecting, setConnecting] = useState(false);
  const [requesting, setRequesting] = useState<string | null | false>(false);
  const [excluding, setExcluding] = useState<PlanLimited | null>(null);
  const data = automation.data;

  if (automation.isError) {
    return (
      <ErrorState
        title="Checks could not load"
        onRetry={() => void automation.refetch()}
      />
    );
  }
  if (automation.isLoading || !data) {
    return <Skeleton className="h-72 w-full rounded-lg" />;
  }
  const state = CONTROL_STATE[data.status];
  const composition = data.composition;
  const capabilities = data.capabilities.map((c) => ({
    key: c.key,
    name: c.name,
  }));
  const unconnected = data.capabilities.filter(
    (c) => !c.providers.some((p) => p.connected),
  );

  return (
    <div className="space-y-5">
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
            {data.scopes.length > 0 ? (
              <p className="mt-1 text-caption text-text-subtle">
                {data.scopes
                  .map(
                    (s) =>
                      `Checking ${s.in_scope} of ${s.listed} repositories on ${s.account}`,
                  )
                  .join(". ")}
                .{" "}
                <Link
                  to="/connectors"
                  className="font-semibold text-action-accent hover:underline"
                >
                  Choose which
                </Link>
              </p>
            ) : null}
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

      {composition ? (
        <section className="rounded-lg border border-border bg-surface-primary p-5">
          <div className="flex flex-wrap items-center gap-2">
            <h2 className="font-display text-title-md text-text-primary">
              How it is evidenced
            </h2>
            <ModeBadge mode={composition.mode} />
          </div>
          <p className="mt-1 text-body-sm text-text-subtle">
            {compositionSentence(composition)}
          </p>
          {composition.sources.length > 0 ? (
            <ul className="mt-3 flex flex-wrap gap-2">
              {composition.sources.map((source) => (
                <li key={source.key}>
                  <SourceChip source={source} />
                </li>
              ))}
            </ul>
          ) : null}
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            <Stat
              label="Checks running"
              value={`${composition.checks_running} of ${composition.checks_total}`}
            />
            <Stat
              label="Not running yet"
              value={String(composition.checks_planned + composition.checks_ready)}
              hint={
                composition.checks_ready > 0
                  ? `${composition.checks_ready} ready to connect`
                  : undefined
              }
            />
            <Stat
              label="In Verity modules"
              value={String(composition.items_platform)}
            />
            <Stat
              label="You provide"
              value={String(composition.items_manual + composition.items_planned)}
            />
          </dl>
        </section>
      ) : null}

      <section>
        <h3 className="type-overline mb-2">
          Checks
          <span className="ml-2 tabular font-normal text-text-subtle">
            {data.tests.length}
          </span>
        </h3>
        {data.tests.length === 0 ? (
          <EmptyState
            icon="plug"
            title="No check applies yet"
            description="No connected system or Verity module checks this control. The evidence is provided by people, listed below."
          />
        ) : (
          <ul className="space-y-2">
            {data.tests.map((test) => (
              <CheckRow
                key={test.key}
                test={test}
                canConnect={canConnect}
                onConnect={() => setConnecting(true)}
                onExclude={setExcluding}
              />
            ))}
          </ul>
        )}
      </section>

      {data.evidence.length > 0 ? (
        <section>
          <h3 className="type-overline mb-2">
            Evidence an auditor expects
            <span className="ml-2 tabular font-normal text-text-subtle">
              {data.evidence.length}
            </span>
          </h3>
          <ul className="space-y-2">
            {data.evidence.map((item) => (
              <EvidenceRow
                key={item.key}
                item={item}
                onOpenEvidence={onOpenEvidence}
              />
            ))}
          </ul>
        </section>
      ) : null}

      {unconnected.length > 0 && data.tests.length > 0 ? (
        <section>
          <h3 className="type-overline mb-2">Systems to connect</h3>
          <div className="space-y-3">
            {unconnected.map((capability) => (
              <CapabilityBlock
                key={capability.key}
                capability={capability}
                canConnect={canConnect}
                canRequest={canRequest}
                onConnect={() => setConnecting(true)}
                onRequest={(key) => setRequesting(key)}
              />
            ))}
          </div>
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
      <ScopeDialog
        connection={
          excluding
            ? { id: excluding.connectionId, account_login: excluding.account }
            : null
        }
        leaveOut={excluding?.names}
        onClose={() => setExcluding(null)}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-md bg-surface-sunken px-3 py-2.5">
      <dt className="text-caption text-text-subtle">{label}</dt>
      <dd className="font-display text-title-md tabular text-text-primary">
        {value}
      </dd>
      {hint ? <p className="text-caption text-text-subtle">{hint}</p> : null}
    </div>
  );
}
