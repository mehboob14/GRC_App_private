import { useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Button,
  Dialog,
  DialogBody,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  Icon,
  SearchInput,
  StatusPill,
  statusFamilyFor,
} from "@/components/ui";
import { cn } from "@/lib/cn";
import { describeError } from "@/lib/api/describe-error";
import { SEARCH, type LinkType } from "../api";
import { humanize, LINK_META } from "../meta";

/**
 * Find a record in another module and link it. Type pills across the top,
 * search below, and each result links in place, so several records can be
 * linked without reopening the dialog.
 */
export function LinkPickerDialog({
  open,
  onOpenChange,
  types,
  initialType,
  linkedIds,
  pendingId,
  onLink,
  context,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** The types the person may link, in the order the page shows them. */
  types: LinkType[];
  initialType: LinkType;
  /** Already linked, per type, so they show as done rather than addable. */
  linkedIds: (type: LinkType) => Set<string>;
  pendingId: string | null;
  onLink: (type: LinkType, id: string) => void;
  /** "this asset", "this finding": finishes the description line. */
  context: string;
}) {
  const [type, setType] = useState<LinkType>(initialType);
  const [search, setSearch] = useState("");
  const query = useDeferredValue(search);

  useEffect(() => {
    if (open) {
      setType(initialType);
      setSearch("");
    }
  }, [open, initialType]);

  const results = useQuery({
    queryKey: ["link-picker", type, query],
    queryFn: () => SEARCH[type](query),
    enabled: open,
  });
  const linked = linkedIds(type);
  const meta = LINK_META[type];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="lg" scrollBody className="max-h-[86vh]">
        <DialogHeader>
          <DialogTitle>Link records</DialogTitle>
          <DialogDescription>
            Connect {context} to the rest of the platform.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          {types.length > 1 ? (
            <div
              className="flex flex-wrap gap-1.5"
              role="tablist"
              aria-label="Record type"
            >
              {types.map((t) => (
                <button
                  key={t}
                  type="button"
                  role="tab"
                  aria-selected={t === type}
                  onClick={() => setType(t)}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-label-sm transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                    t === type
                      ? "border-action-accent bg-action-accent text-white"
                      : "border-border bg-surface-primary text-text-secondary hover:bg-surface-hover",
                  )}
                >
                  <Icon name={LINK_META[t].icon} className="size-3.5" />
                  {LINK_META[t].plural}
                </button>
              ))}
            </div>
          ) : null}
          <SearchInput
            value={search}
            onChange={setSearch}
            placeholder={`Search ${meta.plural.toLowerCase()}`}
            aria-label={`Search ${meta.plural.toLowerCase()}`}
          />
        </div>
        <DialogBody className="mt-3">
          {results.isLoading ? (
            <ul
              className="divide-y divide-border rounded-lg border border-border"
              aria-busy
            >
              {[0, 1, 2, 3].map((i) => (
                <li key={i} className="flex items-center gap-3 px-3 py-3">
                  <span className="size-8 animate-pulse rounded-md bg-surface-sunken" />
                  <span className="h-3 flex-1 animate-pulse rounded bg-surface-sunken" />
                </li>
              ))}
            </ul>
          ) : results.isError ? (
            <p className="py-8 text-center text-body-sm text-text-subtle">
              {describeError(results.error, meta.plural.toLowerCase()).message}
            </p>
          ) : !results.data?.length ? (
            <div className="flex flex-col items-center gap-2 py-10 text-center">
              <span className="grid size-10 place-items-center rounded-xl bg-surface-sunken text-text-subtle">
                <Icon name={meta.icon} className="size-5" />
              </span>
              <p className="text-body-sm text-text-subtle">
                {query.trim()
                  ? `No ${meta.plural.toLowerCase()} match "${query.trim()}".`
                  : `No ${meta.plural.toLowerCase()} yet.`}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {results.data.map((c) => {
                const done = linked.has(c.id);
                const family = statusFamilyFor(c.status) ?? "neutral";
                return (
                  <li
                    key={c.id}
                    className="flex items-center gap-3 px-3 py-2.5"
                  >
                    <span className="grid size-8 shrink-0 place-items-center rounded-md bg-surface-sunken text-text-subtle">
                      <Icon name={meta.icon} className="size-4" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-body-sm font-medium text-text-primary">
                        {c.code ? (
                          <span className="mr-1.5 font-mono text-caption font-semibold text-text-subtle">
                            {c.code}
                          </span>
                        ) : null}
                        {c.title}
                      </span>
                    </span>
                    <StatusPill
                      status={family}
                      label={humanize(c.status)}
                      kind="inline"
                    />
                    <Button
                      size="sm"
                      variant={done ? "ghost" : "secondary"}
                      disabled={done || pendingId !== null}
                      loading={pendingId === c.id}
                      onClick={() => onLink(type, c.id)}
                      className="w-20"
                    >
                      {done ? (
                        <>
                          <Icon name="check" className="size-3.5" />
                          Linked
                        </>
                      ) : (
                        "Link"
                      )}
                    </Button>
                  </li>
                );
              })}
            </ul>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={() => onOpenChange(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
