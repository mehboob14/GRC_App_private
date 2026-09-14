import { useMemo, useState } from "react";
import * as DropdownMenuPrimitive from "@radix-ui/react-dropdown-menu";
import { useQuery } from "@tanstack/react-query";
import { Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import { listAssets } from "@/features/assets/api";

/**
 * Linked assets on the risk form: a field that opens a searchable checklist and
 * shows what is picked as removable chips. Assets come from the asset module's
 * own list, so a person sees exactly the inventory they can open.
 */
export function AssetPicker({
  value,
  onChange,
}: {
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  const [query, setQuery] = useState("");
  const assetsQuery = useQuery({
    queryKey: ["risk-asset-options"],
    queryFn: () => listAssets({}, 1, 200),
    staleTime: 60_000,
  });
  const assets = useMemo(() => assetsQuery.data?.items ?? [], [assetsQuery.data]);
  const byId = useMemo(() => new Map(assets.map((a) => [a.id, a])), [assets]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return assets.filter(
      (a) => !q || a.name.toLowerCase().includes(q) || (a.hostname ?? "").toLowerCase().includes(q),
    );
  }, [assets, query]);

  const toggle = (id: string, on: boolean) =>
    onChange(on ? [...value, id] : value.filter((v) => v !== id));

  return (
    <div>
      <DropdownMenuPrimitive.Root onOpenChange={(open) => !open && setQuery("")}>
        <DropdownMenuPrimitive.Trigger
          aria-label="Linked assets"
          className={cn(
            "flex h-9 w-full items-center justify-between gap-2 rounded-sm border border-border bg-surface-primary px-3 text-left text-body-md",
            "focus:border-action-accent focus:shadow-input-focus focus:outline-none",
          )}
        >
          <span className={cn("truncate", value.length ? "text-text-primary" : "text-text-subtle")}>
            {value.length
              ? `${value.length} ${value.length === 1 ? "asset" : "assets"} linked`
              : "Select assets"}
          </span>
          <Icon name="chev" className="size-4 shrink-0 text-text-subtle" />
        </DropdownMenuPrimitive.Trigger>
        <DropdownMenuPrimitive.Portal>
          <DropdownMenuPrimitive.Content
            align="start"
            sideOffset={6}
            className="z-[1400] w-[var(--radix-dropdown-menu-trigger-width)] min-w-[260px] overflow-hidden rounded-lg border border-border bg-surface-primary p-1 shadow-2"
          >
            <div className="mb-1 flex items-center gap-2 border-b border-border px-2.5 py-2">
              <Icon name="search" className="size-3.5 shrink-0 text-text-subtle" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => {
                  if (!["ArrowDown", "ArrowUp", "Escape", "Tab"].includes(e.key)) e.stopPropagation();
                }}
                placeholder="Search assets"
                aria-label="Search assets"
                className="w-full bg-transparent text-body-sm text-text-primary outline-none placeholder:text-text-subtle"
              />
            </div>
            <div className="max-h-64 overflow-y-auto">
              {assetsQuery.isLoading ? (
                <p className="px-2.5 py-4 text-center text-caption text-text-subtle">Loading assets</p>
              ) : filtered.length === 0 ? (
                <p className="px-2.5 py-4 text-center text-caption text-text-subtle">
                  {assets.length ? "No matches" : "No assets in the inventory yet"}
                </p>
              ) : (
                filtered.map((a) => (
                  <DropdownMenuPrimitive.CheckboxItem
                    key={a.id}
                    checked={value.includes(a.id)}
                    onCheckedChange={(checked) => toggle(a.id, checked === true)}
                    onSelect={(e) => e.preventDefault()}
                    className="relative flex cursor-pointer select-none items-center rounded-xs py-1.5 pl-7 pr-2.5 outline-none data-[highlighted]:bg-surface-hover"
                  >
                    <DropdownMenuPrimitive.ItemIndicator className="absolute left-2 text-action-accent">
                      <Icon name="check" className="size-3.5" />
                    </DropdownMenuPrimitive.ItemIndicator>
                    <span className="min-w-0">
                      <span className="block truncate text-body-sm text-text-primary">{a.name}</span>
                      <span className="block truncate text-caption text-text-subtle">
                        {[a.asset_type.replace(/_/g, " "), a.hostname].filter(Boolean).join(" · ")}
                      </span>
                    </span>
                  </DropdownMenuPrimitive.CheckboxItem>
                ))
              )}
            </div>
          </DropdownMenuPrimitive.Content>
        </DropdownMenuPrimitive.Portal>
      </DropdownMenuPrimitive.Root>
      {value.length ? (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {value.map((id) => (
            <span
              key={id}
              className="inline-flex max-w-full items-center gap-1 rounded-full bg-surface-sunken py-0.5 pl-2.5 pr-1 text-caption text-text-secondary"
            >
              <Icon name="server" className="size-3 shrink-0 text-text-subtle" />
              <span className="truncate">{byId.get(id)?.name ?? "Asset"}</span>
              <button
                type="button"
                onClick={() => toggle(id, false)}
                aria-label={`Remove ${byId.get(id)?.name ?? "asset"}`}
                className="grid size-4 place-items-center rounded-full hover:bg-surface-hover"
              >
                <Icon name="x" className="size-3" />
              </button>
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}
