import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  EmptyState,
  FilterFacet,
  SearchInput,
  StatusPill,
  statusFamilyFor,
  Tooltip,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { ConnectorLogo } from "@/features/connectors/connector-logo";
import {
  CONNECTOR_CATEGORIES,
  CONNECTORS,
  type Connector,
} from "@/features/connectors/connector-catalogue";

const CATEGORY_OPTIONS = CONNECTOR_CATEGORIES.map((category) => ({
  value: category,
  label: category,
}));

/** Every provider reads the same: nothing is connected until Phase 2. */
const NOT_CONNECTED = "Not connected";
const notConnectedFamily = statusFamilyFor(NOT_CONNECTED) ?? "unknown";

type Tab = "active" | "available";
const TABS: Tab[] = ["active", "available"];

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
    <Card className="flex flex-col p-4">
      <div className="flex items-center gap-2.5">
        <ConnectorLogo size={28} />
        <span className="truncate text-body-md font-semibold text-text-primary">
          {connector.name}
        </span>
      </div>
      <div className="mt-3">
        <p className="type-overline mb-1.5">Categories</p>
        <CategoryChips categories={connector.categories} />
      </div>
      <Button
        variant="secondary"
        size="sm"
        className="mt-4 w-full"
        onClick={onOpen}
      >
        View and connect
      </Button>
    </Card>
  );
}

export function ConnectionsPage() {
  const [tab, setTab] = useState<Tab>("available");
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState<string[]>([]);
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
      <h1 className="font-display text-heading-lg text-text-primary">
        All Connections
      </h1>

      <nav
        className="mb-6 mt-4 flex gap-1 border-b border-border"
        aria-label="Connections sections"
      >
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            aria-current={tab === t ? "page" : undefined}
            className={cn(
              "relative -mb-px px-3 py-2.5 text-label-md capitalize transition-colors duration-150 ease-state",
              tab === t
                ? "text-action-accent"
                : "text-text-secondary hover:text-text-primary",
            )}
          >
            {t}
            {tab === t ? (
              <span className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-action-accent" />
            ) : null}
          </button>
        ))}
      </nav>

      {tab === "active" ? (
        <EmptyState
          icon="plug"
          title="No active connections yet"
          description="Connect a provider from Available to start collecting evidence. Connecting arrives in Phase 2."
        />
      ) : (
        <>
          <div
            role="search"
            aria-label="Filter connectors"
            className="mb-4 flex flex-wrap items-center gap-2"
          >
            <SearchInput
              value={search}
              onChange={setSearch}
              placeholder="Search connectors…"
              aria-label="Search connectors by name"
              className="w-full sm:w-64"
            />
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
            <p aria-live="polite" className="ml-auto text-caption text-text-subtle">
              Showing <span className="tabular">{visible.length}</span> of{" "}
              <span className="tabular">{CONNECTORS.length}</span> connectors
            </p>
          </div>

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
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
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

      {/* Peek → drawer: read what a connector will do without leaving the page. */}
      <Drawer
        open={selected !== null}
        onOpenChange={(open) => {
          if (!open) setSelected(null);
        }}
      >
        <DrawerContent size="md">
          {selected ? (
            <>
              <DrawerHeader>
                <DrawerTitle className="flex items-center gap-2.5">
                  <ConnectorLogo size={28} />
                  {selected.name}
                </DrawerTitle>
                <DrawerDescription>
                  Not connected. Verity holds no credential for {selected.name}{" "}
                  and has collected nothing from it.
                </DrawerDescription>
              </DrawerHeader>

              <DrawerBody className="space-y-5">
                <div>
                  <p className="type-overline mb-1.5">Categories</p>
                  <CategoryChips categories={selected.categories} />
                </div>

                <div>
                  <p className="type-overline mb-1.5">What this will sync</p>
                  <p className="mb-2 text-body-sm text-text-subtle">
                    Once connector sync ships in Phase 2, Verity will collect the
                    following as control evidence. Nothing is collected today.
                  </p>
                  <ul className="list-disc space-y-1.5 pl-5 text-body-md text-text-secondary marker:text-text-faint">
                    {selected.syncs.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="type-overline mb-1.5">Status</p>
                  <StatusPill status={notConnectedFamily} label={NOT_CONNECTED} />
                </div>
              </DrawerBody>

              <DrawerFooter className="items-center justify-between gap-3">
                <p className="text-body-sm text-text-subtle">
                  Connecting arrives in Phase 2.
                </p>
                <Tooltip content="Connecting arrives in Phase 2, with the connector sync backend. There is nothing to authorise yet.">
                  <span tabIndex={0} className="rounded-sm">
                    <Button disabled>Connect {selected.name}</Button>
                  </span>
                </Tooltip>
              </DrawerFooter>
            </>
          ) : null}
        </DrawerContent>
      </Drawer>
    </div>
  );
}
