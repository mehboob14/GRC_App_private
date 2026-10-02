import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/icon";
import { Donut, StackedBar } from "./charts";
import { Legend, Panel, SampleNote } from "./ui-kit";

/** Floating overview cards for assets and vulnerabilities, like the reference's runtime dashboard. */

const severity = [
  { label: "Critical", value: 3, color: "#E11D48" },
  { label: "High", value: 11, color: "#F97316" },
  { label: "Medium", value: 24, color: "#F59E0B" },
  { label: "Low", value: 9, color: "#10B981" },
];

const assets = [
  { label: "Application", value: 18, color: "#0A6CCB" },
  { label: "Infrastructure", value: 14, color: "#38BDF8" },
  { label: "Data store", value: 9, color: "#F59E0B" },
  { label: "Cloud resource", value: 7, color: "#F97316" },
  { label: "Other", value: 4, color: "#B6BFCC" },
];

const priority = [
  { label: "P1", value: 5, color: "#E11D48" },
  { label: "P2", value: 12, color: "#F97316" },
  { label: "P3", value: 19, color: "#F59E0B" },
  { label: "P4", value: 11, color: "#94A3B8" },
];

export function EstateDashboard() {
  return (
    <figure data-animate className="relative mx-auto w-full max-w-[600px] pb-6 pt-2">
      <div className="grid gap-4 sm:block">
        <Panel className="seq sm:w-[64%]" style={{ ["--i" as string]: 0 } as CSSProperties} bodyClassName="p-5">
          <p className="text-[14px] font-semibold text-[#0B0F17]">Open findings by severity</p>
          <p className="text-[12px] text-[#8A94A3]">Across every asset in scope</p>
          <div className="mt-4 flex items-center gap-5">
            <Donut segments={severity} total="47" caption="Open" size={132} thickness={18} />
            <Legend className="flex-col !gap-y-2" items={severity} />
          </div>
        </Panel>
        <Panel className="seq sm:absolute sm:right-0 sm:top-[33%] sm:w-[54%]" style={{ ["--i" as string]: 1 } as CSSProperties} bodyClassName="p-5">
          <p className="flex items-center gap-1.5 text-[14px] font-semibold text-[#0B0F17]">Assets by type <Icon name="info" size={14} className="text-[#8A94A3]" /></p>
          <p className="text-[12px] text-[#8A94A3]">Owned, tiered and reviewed on a cadence</p>
          <div className="mt-4 flex items-center gap-5">
            <Donut segments={assets} total="52" caption="Total" size={124} thickness={18} />
            <Legend className="flex-col !gap-y-2" items={assets.slice(0, 4)} />
          </div>
        </Panel>
        <Panel className="seq sm:relative sm:mt-[150px] sm:w-[86%]" style={{ ["--i" as string]: 2 } as CSSProperties} bodyClassName="p-5">
          <p className="flex items-center gap-1.5 text-[14px] font-semibold text-[#0B0F17]">Open findings by priority <Icon name="info" size={14} className="text-[#8A94A3]" /></p>
          <StackedBar className="mt-4" segments={priority} />
          <Legend className="mt-3" items={priority} />
          <p className="mt-3 flex items-center gap-1.5 text-[12px] text-[#5D6878]"><span className="h-1.5 w-1.5 rounded-full bg-[#059669]" />92% inside their remediation window</p>
        </Panel>
      </div>
      <SampleNote className="mt-5">Illustrative sample data</SampleNote>
    </figure>
  );
}
