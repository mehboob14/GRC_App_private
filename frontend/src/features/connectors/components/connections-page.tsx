import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Badge,
  Button,
  Card,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  FilterFacet,
  PageHeader,
  SearchInput,
  StatusPill,
  statusFamilyFor,
  TabStrip,
  Toolbar,
  Tooltip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import {
  CONNECTOR_CATEGORIES,
  CONNECTORS,
  type Connector,
  type ConnectorCategory,
} from "@/features/connectors/connector-catalogue";

const CATEGORY_OPTIONS = CONNECTOR_CATEGORIES.map((category) => ({
  value: category,
  label: category,
}));

/** Every provider reads the same: nothing is connected until connectors go live. */
const NOT_CONNECTED = "Not connected";
const notConnectedFamily = statusFamilyFor(NOT_CONNECTED) ?? "unknown";

type Tab = "active" | "available";

/** Categories are a taxonomy, not a status — neutral chips (DS §1). */
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

/** Available card — brand, name, categories, one action. Nothing else. */
function AvailableCard({
  connector,
  onOpen,
}: {
  connector: Connector;
  onOpen: () => void;
}) {
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
          {/* Two different kinds of fact, so two different shapes: status is a
              dot + word (a live state), categories are chips (a taxonomy).
              Reading them as one row of look-alike pills is the thing to
              avoid — and the inline kind keeps 40 identical statuses quiet. */}
          <StatusPill
            className="mt-1"
            kind="inline"
            status={notConnectedFamily}
            label={NOT_CONNECTED}
          />
        </div>
      </div>
      {/* The chips are self-evidently categories — an overline above them
          would be a label for a label. */}
      <CategoryChips categories={connector.categories} className="mt-3.5" />
      {/* mt-auto pins the action to the bottom edge whatever the chips do,
          so buttons line up across a row of uneven cards. */}
      <div className="mt-auto pt-5">
        <Button variant="accent" className="w-full" onClick={onOpen}>
          View and connect
        </Button>
      </div>
    </Card>
  );
}

export function ConnectionsPage() {
  const [params] = useSearchParams();
  const [tab, setTab] = useState<Tab>("available");
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

  const visible = useMemo(() => {
    const query = search.trim().toLowerCase();
    return CONNECTORS.filter(
      (connector) =>
        (categories.length === 0 ||
          connector.categories.some((c) => categories.includes(c))) &&
        (query === "" || connector.name.toLowerCase().includes(query)),
    );
  }, [search, categories]);

  const activeFilterNames = [
    ...categories.map((category) => `Category: ${category}`),
    ...(search.trim() ? [`Search: ${search.trim()}`] : []),
  ];
  const hasFilters = activeFilterNames.length > 0;

  function clearFilters() {
    setSearch("");
    setCategories([]);
  }

  return (
    <div>
      <PageHeader title="All connections" />

      <TabStrip
        label="Connection sections"
        value={tab}
        onSelect={(id) => setTab(id as Tab)}
        items={[
          // Connecting a provider arrives in a later phase, so Active is
          // honestly nil rather than a number with nothing behind it.
          { id: "active", label: "Active", count: 0 },
          { id: "available", label: "Available", count: CONNECTORS.length },
        ]}
      />

      {tab === "active" ? (
        <EmptyState
          icon="plug"
          title="No active connections yet"
          description="Connect a provider from Available to start collecting evidence. Connecting arrives soon."
        />
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
                    onOpen={() => setSelected(connector)}
                  />
                </li>
              ))}
            </ul>
          )}
        </>
      )}

      {/* Centred modal, not a side drawer: this is a short, self-contained
          read — name, status, scope — with one action at the end. DS §7.1
          reserves the drawer for content you work alongside the list. */}
      <Dialog
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DialogContent size="md" scrollBody>
          {selected ? (
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
                  </div>
                </div>
                <DialogDescription className="mt-4">
                  Verity holds no credential for {selected.name} and has
                  collected nothing from it.
                </DialogDescription>
              </DialogHeader>

              <DialogBody className="space-y-5 pb-1">
                {/* Status and categories are different kinds of fact, so they
                    get different shapes as well as labels: a dot + word for the
                    live state, filled chips for the taxonomy. Rendered as two
                    grey pills they read as one row of the same thing. */}
                <section className="grid grid-cols-1 divide-y divide-border rounded-lg border border-border sm:grid-cols-2 sm:divide-x sm:divide-y-0">
                  <div className="px-4 py-3">
                    <h3 className="type-overline mb-1.5">Status</h3>
                    <StatusPill
                      kind="inline"
                      status={notConnectedFamily}
                      label={NOT_CONNECTED}
                    />
                  </div>
                  <div className="px-4 py-3">
                    <h3 className="type-overline mb-1.5">Categories</h3>
                    <CategoryChips categories={selected.categories} />
                  </div>
                </section>

                <section>
                  <h3 className="type-overline mb-2">What this will sync</h3>
                  <p className="mb-2.5 text-body-sm text-text-subtle">
                    Once connectors go live, Verity will collect the following
                    as control evidence. Nothing is collected today.
                  </p>
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
                <p className="text-body-sm text-text-subtle">
                  Connecting arrives soon.
                </p>
                <Tooltip content="Connecting arrives soon, with the connector sync backend. There is nothing to authorise yet.">
                  <span tabIndex={0} className="rounded-sm">
                    <Button disabled>Connect {selected.name}</Button>
                  </span>
                </Tooltip>
              </DialogFooter>
            </>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}
