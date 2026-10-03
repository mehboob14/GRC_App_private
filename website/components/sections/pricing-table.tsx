"use client";

import { Fragment, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import type { Tier, TierId, FeatureRow } from "@/content/pricing";

function CellMark({ value }: { value: "yes" | "soon" | "no" }) {
  if (value === "yes") return <span className="inline-flex items-center gap-1 text-emerald-700"><Icon name="check" size={18} weight="fill" /><span className="sr-only">Included</span></span>;
  if (value === "soon") return <span className="inline-flex rounded-full border border-dashed border-indigo-300 bg-indigo-50/70 px-2 py-0.5 text-[11.5px] font-medium text-indigo-700">Coming soon</span>;
  return <span className="text-faint" aria-label="Not included">—</span>;
}

/** Plan comparison: all columns on wide screens, one chosen plan at a time on phones. */
export function PricingTable({ tiers, groups }: { tiers: Tier[]; groups: { group: string; rows: FeatureRow[] }[] }) {
  const [mobileTier, setMobileTier] = useState<TierId>("growth");
  return (
    <div>
      <div role="tablist" aria-label="Choose a plan to compare" className="mb-4 flex gap-1 overflow-x-auto md:hidden">
        {tiers.map((tier) => (
          <button key={tier.id} type="button" role="tab" aria-selected={mobileTier === tier.id} onClick={() => setMobileTier(tier.id)} className={cn("whitespace-nowrap rounded-full border px-3.5 py-1.5 text-[13.5px] font-medium", mobileTier === tier.id ? "border-ink bg-ink text-white" : "border-line text-body")}>
            {tier.name}
          </button>
        ))}
      </div>
      <div className="overflow-hidden rounded-2xl border border-line">
        <table className="w-full border-collapse text-left text-[14.5px]">
          <caption className="sr-only">Features included in each plan</caption>
          <thead className="bg-surface">
            <tr className="border-b border-line">
              <th scope="col" className="w-[44%] px-5 py-4 text-[13px] font-medium text-dim">Feature</th>
              {tiers.map((tier) => (
                <th key={tier.id} scope="col" className={cn("px-3 py-4 text-center text-[15px] font-semibold text-ink", mobileTier !== tier.id && "hidden md:table-cell")}>{tier.name}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {groups.map((group) => (
              <Fragment key={group.group}>
                <tr className="border-b border-line bg-subtle">
                  <th scope="colgroup" colSpan={tiers.length + 1} className="px-5 py-2.5 font-mono text-[11.5px] font-medium uppercase tracking-[0.12em] text-dim">{group.group}</th>
                </tr>
                {group.rows.map((row) => (
                  <tr key={row.name} className="border-b border-line last:border-b-0">
                    <th scope="row" className="px-5 py-3 font-normal text-body">{row.name}</th>
                    {tiers.map((tier) => (
                      <td key={tier.id} className={cn("px-3 py-3 text-center", mobileTier !== tier.id && "hidden md:table-cell")}><CellMark value={row.tiers[tier.id]} /></td>
                    ))}
                  </tr>
                ))}
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
