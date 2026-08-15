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
  Icon,
  SearchInput,
  StatusPill,
  statusFamilyFor,
  Tooltip,
} from "@/components/ui";
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

/**
 * Categories are a taxonomy, not a status — neutral chips (DS §1). Rendered as
 * a span so the same component is valid inside the card's <button>.
 */
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

function ConnectorCard({
  connector,
  onOpen,
}: {
  connector: Connector;
  onOpen: () => void;
}) {
  return (
    // asChild → a real <button>: Enter/Space, focus ring and tab order come
    // from the platform. Hover is a colour change at 80ms (§7.6); no shadow,
    // because the card is not floating (§4.4).
    <Card
      asChild
      className="transition-colors duration-80 ease-state hover:border-action-accent-border hover:bg-surface-hover"
    >
      <button
        type="button"
        onClick={onOpen}
        className="flex size-full flex-col p-4 text-left"
      >
        {/* DS §6.4 "Source / vendor": 22×22 brand tile + name. The name takes
            text-primary weight here because on a card it is the primary value,
            not a secondary vendor column (§2.3, §3.4). */}
        <span className="flex w-full items-center gap-2">
          <ConnectorLogo size={22} />
          <span className="truncate text-body-md font-semibold text-text-primary">
            {connector.name}
          </span>
          <Icon
            name="chevr"
            className="ml-auto size-4 text-text-faint"
            aria-hidden
          />
        </span>

        <CategoryChips categories={connector.categories} className="mb-3 mt-2.5" />

        <span className="mt-auto flex w-full items-center gap-2 border-t border-border pt-3">
          <StatusPill
            kind="inline"
            status={notConnectedFamily}
            label={NOT_CONNECTED}
          />
          <Badge variant="role" className="ml-auto">
            Phase 2
          </Badge>
        </span>
      </button>
    </Card>
  );
}

/** Connections — the catalogue of integrations Verity will sync from. Phase 1
 *  lists them as honest placeholders; no connector is live yet. */
export function ConnectionsPage() {
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
    <div className="mx-auto max-w-[1200px]">
      <h1 className="font-display text-heading-lg text-text-primary">
        Connections
      </h1>
      <p className="mt-2 max-w-2xl text-body-lg text-text-secondary">
        The <span className="tabular">{CONNECTORS.length}</span> integrations
        Verity will collect evidence from. Connecting them arrives in Phase 2 —
        nothing is syncing yet.
      </p>

      {/* Toolbar stays mounted above every state, so a filtered-empty result
          can still be undone from where it was made (§7.5). */}
      <div
        role="search"
        aria-label="Filter connectors"
        className="mb-4 mt-5 flex flex-wrap items-center gap-2"
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
        <p
          aria-live="polite"
          className="ml-auto text-caption text-text-subtle"
        >
          Showing <span className="tabular">{visible.length}</span> of{" "}
          <span className="tabular">{CONNECTORS.length}</span> connectors
        </p>
      </div>

      {/* The catalogue is a static constant — it never loads, never fails and
          is never empty, so those three states are deliberately absent. */}
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
              <ConnectorCard
                connector={connector}
                onOpen={() => setSelected(connector)}
              />
            </li>
          ))}
        </ul>
      )}

      {/* Peek → drawer (§7.1): read what a connector will do without leaving
          the catalogue. Radix traps focus, restores it and closes on Esc. */}
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
                    Once connector sync ships in Phase 2, Verity will collect
                    the following as control evidence. Nothing is collected
                    today.
                  </p>
                  <ul className="list-disc space-y-1.5 pl-5 text-body-md text-text-secondary marker:text-text-faint">
                    {selected.syncs.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <p className="type-overline mb-1.5">Status</p>
                  <StatusPill
                    status={notConnectedFamily}
                    label={NOT_CONNECTED}
                  />
                </div>
              </DrawerBody>

              <DrawerFooter className="items-center justify-between gap-3">
                <p className="text-body-sm text-text-subtle">
                  Connecting arrives in Phase 2.
                </p>
                <Tooltip content="Connecting arrives in Phase 2, with the connector sync backend. There is nothing to authorise yet.">
                  {/* Disabled buttons take no pointer or focus events, so the
                      tooltip hangs off a focusable wrapper — the reason stays
                      reachable by keyboard (§5.2). */}
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
