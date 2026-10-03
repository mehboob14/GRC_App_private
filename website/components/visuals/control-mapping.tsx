import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Status } from "@/content/catalog";
import { Avatar, CodeChip, Pill, SampleNote } from "./ui-kit";

/**
 * Map once, satisfy many: one control (from the shipped SOC 2 library) linked
 * to the requirement it answers today and the ones planned libraries will add.
 */
const targets: { framework: string; ref: string; status: Status }[] = [
  { framework: "SOC 2", ref: "CC6.3", status: "live" },
  { framework: "ISO/IEC 27001:2022", ref: "A.5.18 Access rights", status: "soon" },
  { framework: "PCI DSS v4.0.1", ref: "Req. 7.2.4", status: "soon" },
  { framework: "NIST CSF 2.0", ref: "PR.AA-05", status: "soon" },
  { framework: "SBP ETGRMF", ref: "Information security · access control", status: "soon" },
  { framework: "APRA CPS 234", ref: "Information security controls", status: "soon" },
];

export function ControlMapping() {
  const rowHeight = 58;
  const height = targets.length * rowHeight;
  return (
    <figure data-animate className="w-full">
      <div className="grid grid-cols-1 items-center gap-6 md:grid-cols-[minmax(0,0.9fr)_88px_minmax(0,1.1fr)] md:gap-0">
        <div className="seq rounded-xl border border-line bg-white p-4 shadow-float" style={{ ["--i" as string]: 0 } as CSSProperties}>
          <p className="font-mono text-[10.5px] text-faint">IAM-02 · Hybrid</p>
          <p className="mt-1 text-[15px] font-semibold text-ink">Periodic user access reviews</p>
          <p className="mt-2 text-[13px] leading-snug text-dim">Review who can reach production systems and customer data every quarter; remove what is no longer needed.</p>
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-line pt-3 text-[12px] text-dim">
            <Avatar name="Ayesha Raza" /><span>Ayesha Raza</span>
            <span className="ms-auto"><Pill tone="success">Implemented</Pill></span>
          </div>
          <div className="mt-3 flex items-center gap-2 rounded-lg bg-subtle px-3 py-2 text-[12px] text-body">
            <Icon name="folder" size={15} className="text-dim" />4 evidence items · collected once
          </div>
        </div>

        <svg className="hidden md:block" viewBox={`0 0 88 ${height}`} width="88" height={height} aria-hidden="true">
          {targets.map((target, index) => {
            const y = index * rowHeight + rowHeight / 2;
            const d = `M0 ${height / 2} C 44 ${height / 2}, 44 ${y}, 88 ${y}`;
            return <path key={target.ref} d={d} fill="none" stroke={target.status === "live" ? "#0EA5E9" : "#C7D2FE"} strokeWidth="1.6" strokeDasharray={target.status === "live" ? undefined : "4 4"} className={target.status === "live" ? "draw" : undefined} style={{ ["--len" as string]: 140, ["--i" as string]: index } as CSSProperties} />;
          })}
          <circle cx="2" cy={height / 2} r="4" fill="#0EA5E9" />
        </svg>

        <ul className="space-y-2">
          {targets.map((target, index) => (
            <li key={target.ref} className="seq flex h-[50px] items-center justify-between gap-3 rounded-lg border border-line bg-white px-3.5 shadow-card" style={{ ["--i" as string]: index + 1, ["--step" as string]: "120ms", ["--base" as string]: "250ms" } as CSSProperties}>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium text-ink">{target.framework}</span>
                <span className="block truncate"><CodeChip className="!border-0 !bg-transparent !p-0 !text-[11px] !text-dim">{target.ref}</CodeChip></span>
              </span>
              <StatusBadge status={target.status} size="xs" hideLive={false} />
            </li>
          ))}
        </ul>
      </div>
      <SampleNote className="mt-5">The SOC 2 mapping ships today; other libraries are coming soon</SampleNote>
    </figure>
  );
}
