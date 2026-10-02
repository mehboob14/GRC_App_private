"use client";

import Link from "next/link";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Framework, Region } from "@/content/frameworks";

/** Framework chips grouped by region, with keyboard-operable tabs. */
export function RegionTabs({ regions, frameworks, limit = 8 }: { regions: { id: Region; name: string; short: string }[]; frameworks: Framework[]; limit?: number }) {
  const [active, setActive] = useState<Region>(regions[0].id);
  const inRegion = frameworks.filter((framework) => framework.region === active);
  const shown = inRegion.slice(0, limit);
  return (
    <div>
      <div role="tablist" aria-label="Region" className="scrollbar-none -mx-1 flex gap-1.5 overflow-x-auto px-1 pb-1 sm:flex-wrap sm:overflow-visible">
        {regions.map((region, index) => (
          <button
            key={region.id}
            id={`region-tab-${region.id}`}
            role="tab"
            type="button"
            aria-selected={active === region.id}
            aria-controls="region-panel"
            tabIndex={active === region.id ? 0 : -1}
            onClick={() => setActive(region.id)}
            onKeyDown={(event) => {
              const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
              if (!delta) return;
              event.preventDefault();
              const next = regions[(index + delta + regions.length) % regions.length];
              setActive(next.id);
              document.getElementById(`region-tab-${next.id}`)?.focus();
            }}
            className={cn("whitespace-nowrap rounded-full border px-3.5 py-1.5 text-[13.5px] font-medium transition-colors", active === region.id ? "border-ink bg-ink text-white" : "border-line bg-surface text-body hover:border-line-strong hover:text-ink")}
          >
            {region.name}
          </button>
        ))}
      </div>
      <ul id="region-panel" role="tabpanel" aria-labelledby={`region-tab-${active}`} className="mt-5 grid gap-2 sm:grid-cols-2">
        {shown.map((framework) => (
          <li key={framework.id}>
            <Link href={`/frameworks/?f=${framework.id}`} className="flex h-full items-center justify-between gap-3 rounded-lg border border-line bg-surface px-3.5 py-2.5 transition-colors hover:border-line-strong">
              <span className="min-w-0">
                <span className="block truncate text-[14px] font-medium text-ink">{framework.shortName}</span>
                <span className="block truncate text-[12px] text-dim">{framework.issuer.split("(")[0].trim()}</span>
              </span>
              <StatusBadge status={framework.status} size="xs" hideLive={false} />
            </Link>
          </li>
        ))}
      </ul>
      {inRegion.length > shown.length && (
        <Link href={`/frameworks/?region=${active}`} className="mt-3 inline-block text-[13.5px] font-medium text-accent hover:text-accent-strong">+{inRegion.length - shown.length} more in this region</Link>
      )}
    </div>
  );
}
