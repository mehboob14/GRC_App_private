import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Badge,
  Button,
  Card,
  CodeChip,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  FilterFacet,
  Icon,
  PageHeader,
  SearchInput,
  Skeleton,
  StatusPill,
  TabStrip,
  TextField,
  Toolbar,
  useToast,
  type StatusFamily,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { useAuth } from "@/lib/auth/auth-context";
import { hasPermission } from "@/lib/auth/session";
import { errorToast } from "@/lib/api/describe-error";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import {
  CONNECTOR_CATEGORIES,
  CONNECTORS,
  type Connector,
  type ConnectorCategory,
} from "@/features/connectors/connector-catalogue";
import {
  ago,
  connectorKeys,
  disconnectConnection,
  listProviders,
  type Connection,
  type ControlComposition,
  type Provider,
} from "../api";
import {
  refreshAutomation,
  useConnections,
  useControlComposition,
  useRunConnections,
} from "../hooks";
import { ConnectGitHubDialog } from "./connect-github-dialog";
import { RequestIntegrationDialog } from "./request-integration-dialog";
import { ScopeDialog } from "./scope-dialog";

const CATEGORY_OPTIONS = CONNECTOR_CATEGORIES.map((category) => ({
  value: category,
  label: category,
}));

/** Providers with a live collector. Everything else shows its planned phase. */
const CONNECTABLE = new Set(["github"]);

type Tab = "active" | "available";

type Availability = { label: string; family: StatusFamily | "unknown" };

function availability(
  id: string,
  providers: Map<string, Provider>,
  connected: Set<string>,
): Availability {
  if (connected.has(id)) return { label: "Connected", family: "success" };
  if (CONNECTABLE.has(id))
    return { label: "Ready to connect", family: "progress" };
  const provider = providers.get(id);
  if (provider?.status === "planned") {
    return {
      label: `Arrives in ${provider.phase ?? "a later phase"}`,
      family: "pending",
    };
  }
  return { label: "Not in plan yet", family: "neutral" };
}

/** Categories are a taxonomy, not a status: neutral chips (DS §1). */
function CategoryChips({
  categories,
  className = "",
}: {
  categories: string[];
  className?: string;
}) {
  return (
    <span className={`flex flex-wrap gap-1 ${className}`}>
      {categories.map((category) => (
        <Badge key={category} variant="neutral">
          {category}
        </Badge>
      ))}
    </span>
  );
}

/** Available card: brand, name, what it takes to connect, one action. */
function AvailableCard({
  connector,
  state,
  onOpen,
}: {
  connector: Connector;
  state: Availability;
  onOpen: () => void;
}) {
  const ready = CONNECTABLE.has(connector.id) && state.family !== "success";
  return (
    // h-full so a row of cards shares one height however many category chips
    // each carries; the button then lines up across the row.
    <Card
      className={cn(
        "group flex h-full flex-col p-5",
        "transition-[border-color,box-shadow] duration-150 ease-state",
        "hover:border-border-strong hover:shadow-2",
      )}
    >
      <div className="flex items-start gap-3.5">
        <ConnectorLogo id={connector.id} name={connector.name} size={48} />
        <div className="min-w-0 flex-1 pt-0.5">
          <p className="truncate text-body-lg font-semibold text-text-primary">
            {connector.name}
          </p>
          <StatusPill
            className="mt-1"
            kind="inline"
            status={state.family}
            label={state.label}
          />
        </div>
      </div>
      <CategoryChips categories={connector.categories} className="mt-3.5" />
      {/* mt-auto pins the action to the bottom edge whatever the chips do,
          so buttons line up across a row of uneven cards. */}
      <div className="mt-auto pt-5">
        <Button
          variant={ready ? "accent" : "secondary"}
          className="w-full"
          onClick={onOpen}
        >
          {ready ? "Connect" : "View"}
        </Button>
      </div>
    </Card>
  );
}

function health(connection: Connection): {
  label: string;
  family: StatusFamily;
} {
  if (connection.latest_run?.status === "running")
    return { label: "Running", family: "progress" };
  if (connection.last_error)
    return { label: "Needs attention", family: "warning" };
  if (!connection.last_run_at)
    return { label: "Waiting for first run", family: "pending" };
  return { label: "Healthy", family: "success" };
}

/** The controls a system checks, so a connection answers what it is for. The
 *  ones failing come first: they are why anyone opens this. */
function ControlsChecked({
  provider,
  name,
  items,
}: {
  provider: string;
  name: string;
  items: ControlComposition[];
}) {
  const mine = items
    .filter((item) => item.composition.runs_on.includes(provider))
    .sort(
      (a, b) =>
        Number(b.automation_status === "failing") -
          Number(a.automation_status === "failing") ||
        a.code.localeCompare(b.code, undefined, { numeric: true }),
    );
  if (mine.length === 0) return null;
  const failing = mine.filter((item) => item.automation_status === "failing");
  const shown = mine.slice(0, 10);
  return (
    <div className="mt-3 rounded-md border border-border px-3 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-body-sm text-text-secondary">
          <span className="font-semibold text-text-primary">{mine.length}</span>{" "}
          {mine.length === 1 ? "control is" : "controls are"} checked by {name}
          {failing.length > 0 ? (
            <span className="font-semibold text-status-danger-text">
              , {failing.length} failing
            </span>
          ) : null}
          .
        </p>
        <Link
          to={`/controls?system=${provider}`}
          className="text-body-sm font-semibold text-action-accent hover:underline"
        >
          View in the controls library
        </Link>
      </div>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {shown.map((item) => (
          <li key={item.control_id}>
            <Link
              to={`/controls/${item.control_id}`}
              title={item.name}
              className="rounded-xs hover:opacity-80"
            >
              <CodeChip code={item.code} />
            </Link>
          </li>
        ))}
        {mine.length > shown.length ? (
          <li className="self-center text-caption text-text-subtle">
            +{mine.length - shown.length} more
          </li>
        ) : null}
      </ul>
    </div>
  );
}

function ConnectionCard({
  connection,
  controls,
  canManage,
  onRun,
  running,
  onDisconnect,
  onChooseScope,
}: {
  connection: Connection;
  controls: ControlComposition[];
  canManage: boolean;
  onRun: () => void;
  running: boolean;
  onDisconnect: () => void;
  onChooseScope: () => void;
}) {
  const state = health(connection);
  const run = connection.latest_run;
  const expires = connection.credential_expires_at
    ? new Date(connection.credential_expires_at).toLocaleDateString(undefined, {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;
  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-start gap-4">
        <ConnectorLogo
          id={connection.provider}
          name={connection.provider_name}
          size={48}
        />
        <div className="min-w-0 flex-1">
          <p className="truncate text-body-lg font-semibold text-text-primary">
            {connection.display_name}
          </p>
          <p className="text-caption text-text-subtle">
            {connection.provider_name}{" "}
            {connection.account_type === "organization"
              ? "organisation"
              : "account"}{" "}
            {connection.account_login}
          </p>
        </div>
        <StatusPill status={state.family} label={state.label} />
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { label: "Last run", value: ago(connection.last_run_at) },
          {
            label: "Passed",
            value: run ? String(run.passed) : "0",
            tone: "text-status-success-text",
          },
          {
            label: "Failed",
            value: run ? String(run.failed) : "0",
            tone: run?.failed ? "text-status-danger-text" : undefined,
          },
          {
            label: "Not checked",
            value: run ? String(run.errored) : "0",
            tone: run?.errored ? "text-status-warning-text" : undefined,
          },
        ].map((fact) => (
          <div
            key={fact.label}
            className="rounded-md bg-surface-sunken px-3 py-2"
          >
            <dt className="type-overline">{fact.label}</dt>
            <dd
              className={cn(
                "tabular text-title-sm font-semibold text-text-primary",
                fact.tone,
              )}
            >
              {fact.value}
            </dd>
          </div>
        ))}
      </dl>

      {connection.scope ? (
        <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-md border border-border px-3 py-2">
          <p className="text-body-sm text-text-secondary">
            <span className="font-semibold text-text-primary">{connection.scope.in_scope}</span> of{" "}
            {connection.scope.listed} repositories are checked
            {connection.scope.excluded > 0
              ? `, ${connection.scope.excluded} left out`
              : ""}
            .
          </p>
          {canManage ? (
            <Button size="sm" variant="secondary" onClick={onChooseScope}>
              Choose repositories
            </Button>
          ) : null}
        </div>
      ) : null}

      <ControlsChecked
        provider={connection.provider}
        name={connection.provider_name}
        items={controls}
      />

      {connection.last_error ? (
        <p className="mt-3 flex items-start gap-2 rounded-md border border-status-warning-border bg-status-warning-bg px-3 py-2 text-body-sm text-status-warning-text">
          <Icon name="alert" className="mt-0.5 size-4 shrink-0" />
          {connection.last_error}
        </p>
      ) : null}

      <div className="mt-4 flex items-center justify-between gap-3 border-t border-border pt-3">
        <span className="inline-flex min-w-0 items-center gap-1.5 text-caption text-text-subtle">
          <Icon name="key" className="size-3.5 shrink-0" />
          <span className="truncate">
            Read only token {connection.credential_hint ?? "stored"}
            {expires ? `, expires ${expires}` : ""}
          </span>
        </span>
        {canManage ? (
          <span className="flex shrink-0 gap-2">
            <Button size="sm" variant="ghost" onClick={onDisconnect}>
              Disconnect
            </Button>
            <Button
              size="sm"
              onClick={onRun}
              loading={running || run?.status === "running"}
            >
              <Icon name="activity" className="size-4" />
              Run now
            </Button>
          </span>
        ) : null}
      </div>
    </Card>
  );
}

function DisconnectDialog({
  connection,
  onClose,
}: {
  connection: Connection | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [reason, setReason] = useState("");
  const disconnect = useMutation({
    mutationFn: () => disconnectConnection(connection!.id, reason.trim()),
    onSuccess: () => {
      refreshAutomation(queryClient);
      toast({
        title: `${connection?.account_login} disconnected`,
        tone: "success",
      });
      setReason("");
      onClose();
    },
    onError: (error: unknown) =>
      toast({ title: errorToast(error, "connection"), tone: "danger" }),
  });
  return (
    <Dialog
      open={connection !== null}
      onOpenChange={(open) => (open ? null : onClose())}
    >
      <DialogContent size="sm">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            disconnect.mutate();
          }}
        >
          <DialogHeader>
            <DialogTitle>Disconnect {connection?.account_login}?</DialogTitle>
            <DialogDescription>
              The token is destroyed and daily tests stop. Past results and
              evidence stay.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-4">
            <TextField
              label="Reason"
              placeholder="Moving to GitLab"
              value={reason}
              maxLength={500}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
          <DialogFooter className="mt-5">
            <Button variant="secondary" type="button" onClick={onClose}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="destructive"
              loading={disconnect.isPending}
              disabled={reason.trim().length < 3}
            >
              Disconnect
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function ConnectionsPage() {
  const [params] = useSearchParams();
  const { principal } = useAuth();
  const canRead = hasPermission(principal, "connectors:read");
  const canManage = hasPermission(principal, "connectors:manage");
  const canRequest = hasPermission(principal, "controls:manage");
  const connectionsQuery = useConnections(canRead);
  const providersQuery = useQuery({
    queryKey: connectorKeys.providers,
    queryFn: listProviders,
    enabled: canRead,
    staleTime: 5 * 60_000,
  });
  const run = useRunConnections(connectionsQuery.kick);
  // Which controls each connection checks. A role that cannot read them simply
  // sees no list: the card does not depend on it.
  const compositionQuery = useControlComposition(canRead);
  const controlsChecked = useMemo(
    () => compositionQuery.data ?? [],
    [compositionQuery.data],
  );

  const active = useMemo(
    () => (connectionsQuery.data ?? []).filter((c) => c.status === "active"),
    [connectionsQuery.data],
  );
  const connected = useMemo(
    () => new Set(active.map((c) => c.provider)),
    [active],
  );
  const providers = useMemo(
    () => new Map((providersQuery.data ?? []).map((p) => [p.key, p])),
    [providersQuery.data],
  );

  const [tab, setTab] = useState<Tab>(() =>
    params.get("tab") === "active" ? "active" : "available",
  );
  const [search, setSearch] = useState("");
  // `?category=Identity` deep-links a pre-filtered catalogue (quick start sends
  // you here for your IdP). Read once as the initial value, so the facet stays
  // the owner of the filter afterwards and Clear filters still clears it.
  // Repeatable, and unknown values are dropped rather than filtering to nothing.
  const [categories, setCategories] = useState<string[]>(() =>
    params
      .getAll("category")
      .filter((value): value is ConnectorCategory =>
        (CONNECTOR_CATEGORIES as readonly string[]).includes(value),
      ),
  );
  const [selected, setSelected] = useState<Connector | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [leaving, setLeaving] = useState<Connection | null>(null);
  const [choosing, setChoosing] = useState<Connection | null>(null);

  // What can be connected leads; then by phase; catalogue order breaks ties.
  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    const rank = (id: string) => {
      const label = availability(id, providers, connected).label;
      if (connected.has(id)) return 0;
      if (CONNECTABLE.has(id)) return 1;
      if (label.endsWith("Phase 2")) return 2;
      if (label.endsWith("Phase 3")) return 3;
      return 4;
    };
    return CONNECTORS.filter(
      (connector) =>
        (categories.length === 0 ||
          connector.categories.some((c) => categories.includes(c))) &&
        (query === "" || connector.name.toLowerCase().includes(query)),
    )
      .map((connector, index) => ({ connector, index }))
      .sort(
        (a, b) =>
          rank(a.connector.id) - rank(b.connector.id) || a.index - b.index,
      )
      .map(({ connector }) => connector);
  }, [search, categories, providers, connected]);

  const activeFilterNames = [
    ...categories.map((category) => `Category: ${category}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];
  const hasFilters = activeFilterNames.length > 0;

  function clearFilters() {
    setSearch("");
    setCategories([]);
  }

  function open(connector: Connector) {
    if (
      CONNECTABLE.has(connector.id) &&
      !connected.has(connector.id) &&
      canManage
    ) {
      setConnecting(true);
      return;
    }
    setSelected(connector);
  }

  const selectedState = selected
    ? availability(selected.id, providers, connected)
    : null;

  return (
    <div>
      <PageHeader
        title="All connections"
        actions={
          canRequest ? (
            <Button variant="secondary" onClick={() => setRequesting(true)}>
              <Icon name="plus" className="size-4" />
              Request integration
            </Button>
          ) : null
        }
      />

      <TabStrip
        label="Connection sections"
        value={tab}
        onSelect={(id) => setTab(id as Tab)}
        items={[
          { id: "active", label: "Active", count: active.length },
          { id: "available", label: "Available", count: CONNECTORS.length },
        ]}
      />

      {tab === "active" ? (
        connectionsQuery.isLoading ? (
          <Skeleton className="h-48 w-full rounded-lg" />
        ) : active.length === 0 ? (
          <EmptyState
            icon="plug"
            title="No active connections yet"
            description="Connect GitHub to start testing controls against real repository data."
            action={
              canManage ? (
                <Button variant="accent" onClick={() => setConnecting(true)}>
                  <Icon name="plug" className="size-4" />
                  Connect GitHub
                </Button>
              ) : undefined
            }
          />
        ) : (
          <ul className="grid max-w-4xl grid-cols-1 gap-4">
            {active.map((connection) => (
              <li key={connection.id}>
                <ConnectionCard
                  connection={connection}
                  controls={controlsChecked}
                  canManage={canManage}
                  running={
                    run.isPending &&
                    run.variables?.includes(connection.id) === true
                  }
                  onRun={() => run.mutate([connection.id])}
                  onDisconnect={() => setLeaving(connection)}
                  onChooseScope={() => setChoosing(connection)}
                />
              </li>
            ))}
          </ul>
        )
      ) : (
        <>
          <Toolbar
            searchLabel="Filter connectors"
            search={
              <SearchInput
                value={search}
                onChange={setSearch}
                placeholder="Search connectors…"
                aria-label="Search connectors by name"
              />
            }
            actions={
              <p aria-live="polite" className="text-caption text-text-subtle">
                Showing <span className="tabular">{visible.length}</span> of{" "}
                <span className="tabular">{CONNECTORS.length}</span> connectors
              </p>
            }
          >
            <FilterFacet
              label="Category"
              options={CATEGORY_OPTIONS}
              values={categories}
              onChange={setCategories}
            />
            {hasFilters ? (
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                Clear filters
              </Button>
            ) : null}
          </Toolbar>

          {visible.length === 0 ? (
            <EmptyState
              variant="no-match"
              title="No connectors match your filters"
              description={`Try removing ${activeFilterNames
                .map((name) => `'${name}'`)
                .join(" or ")}.`}
              onClearFilters={clearFilters}
            />
          ) : (
            <ul className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {visible.map((connector) => (
                <li key={connector.id}>
                  <AvailableCard
                    connector={connector}
                    state={availability(connector.id, providers, connected)}
                    onOpen={() => open(connector)}
                  />
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Centred modal, not a side drawer: a short, self-contained read with one
          action at the end. DS §7.1 reserves the drawer for side-by-side work. */}
      <Dialog
        open={selected !== null}
        onOpenChange={(isOpen) => {
          if (!isOpen) setSelected(null);
        }}
      >
        <DialogContent size="md" scrollBody>
          {selected && selectedState ? (
            <>
              <DialogHeader>
                <div className="flex items-start gap-3.5">
                  <ConnectorLogo
                    id={selected.id}
                    name={selected.name}
                    size={48}
                  />
                  <div className="min-w-0 flex-1">
                    <DialogTitle className="truncate">
                      {selected.name}
                    </DialogTitle>
                    <StatusPill
                      className="mt-1"
                      kind="inline"
                      status={selectedState.family}
                      label={selectedState.label}
                    />
                  </div>
                </div>
                <DialogDescription className="mt-4">
                  {connected.has(selected.id)
                    ? `${selected.name} is connected. Tests run daily and file their evidence on the controls they cover.`
                    : `Verity holds no credential for ${selected.name} and has collected nothing from it.`}
                </DialogDescription>
              </DialogHeader>

              <DialogBody className="space-y-5 pb-1">
                <CategoryChips categories={selected.categories} />
                <section>
                  <h3 className="type-overline mb-2">What it will collect</h3>
                  <ul className="divide-y divide-border rounded-lg border border-border">
                    {selected.syncs.map((item) => (
                      <li
                        key={item}
                        className="px-3.5 py-2.5 text-body-md text-text-secondary"
                      >
                        {item}
                      </li>
                    ))}
                  </ul>
                </section>
              </DialogBody>

              <DialogFooter className="items-center justify-between">
                {connected.has(selected.id) ? (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      setSelected(null);
                      setTab("active");
                    }}
                  >
                    See connection
                  </Button>
                ) : (
                  <>
                    <span />
                    {canRequest ? (
                      <Button
                        onClick={() => {
                          setSelected(null);
                          setRequesting(true);
                        }}
                      >
                        <Icon name="mail" className="size-4" />
                        Request it sooner
                      </Button>
                    ) : null}
                  </>
                )}
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>

      <ConnectGitHubDialog
        open={connecting}
        onOpenChange={setConnecting}
        onConnected={() => {
          connectionsQuery.kick();
          setTab("active");
        }}
      />
      <RequestIntegrationDialog
        open={requesting}
        onOpenChange={setRequesting}
      />
      <DisconnectDialog connection={leaving} onClose={() => setLeaving(null)} />
      <ScopeDialog connection={choosing} onClose={() => setChoosing(null)} />
    </div>
  );
}
