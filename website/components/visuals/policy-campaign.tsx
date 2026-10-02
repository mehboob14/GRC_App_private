import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/icon";
import { StackedColumns } from "./charts";
import { Legend, Pill, SampleNote, type Family } from "./ui-kit";

/** Policies list plus an acknowledgement trend, like the reference's cost breakdown and trend card. */

const policies: { name: string; version: string; state: string; tone: Family; ack?: string }[] = [
  { name: "Information security policy", version: "v4", state: "Published", tone: "success", ack: "96%" },
  { name: "Access control policy", version: "v3", state: "Published", tone: "success", ack: "88%" },
  { name: "Incident response plan", version: "v2", state: "In review", tone: "progress" },
  { name: "Vendor management policy", version: "v1", state: "Draft", tone: "pending" },
];

const series = [
  { label: "Engineering", color: "#0A6CCB" },
  { label: "Operations", color: "#38BDF8" },
  { label: "Finance", color: "#F59E0B" },
  { label: "Sales", color: "#F97316" },
];

const weeks = [
  { label: "W1", values: [40, 22, 10, 18] },
  { label: "W2", values: [70, 38, 24, 30] },
  { label: "W3", values: [96, 55, 37, 44] },
  { label: "W4", values: [118, 66, 46, 58] },
  { label: "W5", values: [131, 74, 52, 69], highlight: true },
];

export function PolicyCampaign() {
  return (
    <figure data-animate className="relative mx-auto w-full max-w-[600px]">
      <div className="seq rounded-xl border border-[#E3E7EC] bg-white p-4 shadow-card sm:w-[78%]" style={{ ["--i" as string]: 0 } as CSSProperties}>
        <p className="flex items-center gap-2 text-[13px] text-[#5D6878]"><Icon name="caret-down" size={12} weight="bold" className="rotate-180" />Policies and documents</p>
        <ul className="mt-3 space-y-2.5">
          {policies.map((policy) => (
            <li key={policy.name} className="flex items-center justify-between gap-3 text-[13px]">
              <span className="min-w-0 truncate text-[#0B0F17]">{policy.name} <span className="font-mono text-[10.5px] text-[#8A94A3]">{policy.version}</span></span>
              <span className="flex shrink-0 items-center gap-2">
                {policy.ack && <span className="font-mono text-[11px] text-[#5D6878]">{policy.ack} signed</span>}
                <Pill tone={policy.tone}>{policy.state}</Pill>
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="seq relative mt-4 rounded-xl border border-[#E3E7EC] bg-white p-5 shadow-float sm:-mt-2 sm:ms-[16%]" style={{ ["--i" as string]: 1 } as CSSProperties}>
        <p className="text-[14px] font-semibold text-[#0B0F17]">Acknowledgements, information security policy v4</p>
        <p className="text-[12px] text-[#8A94A3]">Campaign to 340 people · signatures by week</p>
        <StackedColumns className="mt-4" columns={weeks} series={series} max={340} height={180} yTicks={[0, 100, 200, 300]} />
        <Legend className="mt-4 border-t border-[#EDF0F3] pt-3" items={series} />
      </div>
      <SampleNote className="mt-5">Illustrative sample data</SampleNote>
    </figure>
  );
}
