import type { CSSProperties, ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui/icon";
import { Avatar, CodeChip, OutcomePill, Pill, SampleNote } from "./ui-kit";

/**
 * Requirement → control → evidence, drawn like the reference's delivery
 * pipeline: a success chip above each step card, a note beside it, and a
 * connector that draws as the section scrolls into view. Uses a real control
 * from the shipped SOC 2 library (IAM-02 maps to CC6.3).
 */

function Step({ index, outcome, icon, title, note, noteTitle, children }: { index: number; outcome: string; icon: IconName; title: string; note: string; noteTitle: string; children: ReactNode }) {
  const style = { ["--i" as string]: index } as CSSProperties;
  return (
    <div className="grid grid-cols-1 gap-x-7 gap-y-3 sm:grid-cols-[minmax(0,1.15fr)_minmax(0,0.75fr)]" style={style}>
      <div className="relative">
        <OutcomePill className="seq-pop mb-2" style={style}>{outcome}</OutcomePill>
        <div className="seq rounded-xl border border-[#E3E7EC] bg-white shadow-card" style={style}>
          <div className="flex items-center gap-2.5 px-4 py-3">
            <Icon name={icon} size={18} className="text-[#0B0F17]" />
            <span className="text-[15px] font-semibold text-[#0B0F17]">{title}</span>
          </div>
          <div className="border-t border-[#EDF0F3] px-4 pb-4 pt-3">{children}</div>
        </div>
      </div>
      <div className="seq hidden pt-1 sm:block" style={{ ...style, ["--base" as string]: "350ms" } as CSSProperties}>
        <p className="flex items-center gap-1.5 text-[13px] text-[#6E7787]"><Icon name="caret-down" size={12} weight="bold" />{noteTitle}</p>
        <p className="mt-2 text-[14px] leading-relaxed text-[#363F4E]">{note}</p>
      </div>
    </div>
  );
}

function Connector({ index }: { index: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-[minmax(0,1.15fr)_minmax(0,0.75fr)]" aria-hidden="true">
      <div className="flex justify-center py-1">
        <span className="seq-line relative block h-10 w-px bg-[#CBD2DB]" style={{ ["--i" as string]: index } as CSSProperties}>
          <span className="absolute -bottom-1 left-1/2 h-2 w-2 -translate-x-1/2 rotate-45 border-b border-r border-[#CBD2DB]" />
          <span className="absolute -top-1 left-1/2 h-2 w-2 -translate-x-1/2 rounded-full border border-[#CBD2DB] bg-white" />
        </span>
      </div>
    </div>
  );
}

export function ProofFlow() {
  return (
    <figure data-animate className="w-full" style={{ ["--step" as string]: "420ms" } as CSSProperties}>
      <Step index={0} outcome="Mapped" icon="certificate" title="Requirement" noteTitle="SOC 2 · Trust Services Criteria" note="CC6.3 asks you to authorise, modify and remove access on a least-privilege basis.">
        <p className="text-[13.5px] leading-snug text-[#5D6878]">The entity authorises, modifies or removes access based on roles and responsibilities.</p>
        <div className="mt-3 flex flex-wrap gap-1.5"><CodeChip>SOC 2 · CC6.3</CodeChip><CodeChip>Security</CodeChip></div>
      </Step>
      <Connector index={0} />
      <Step index={1} outcome="Implemented" icon="shield" title="Control" noteTitle="Owned and scheduled" note="One owner, a quarterly cadence, and the same control ready to answer more frameworks as they are added.">
        <div className="rounded-lg border border-[#E3E7EC]">
          <div className="flex items-center justify-between gap-3 px-3 py-2.5">
            <span className="min-w-0">
              <span className="block font-mono text-[10.5px] text-[#6E7787]">IAM-02</span>
              <span className="block text-[13.5px] font-medium leading-snug text-[#0B0F17]">Periodic user access reviews</span>
            </span>
            <Pill tone="success">Implemented</Pill>
          </div>
          <div className="flex items-center justify-between border-t border-[#EDF0F3] px-3 py-2 text-[12px] text-[#5D6878]">
            <span className="inline-flex items-center gap-1.5"><Avatar name="Ayesha Raza" />Ayesha Raza</span>
            <span className="font-mono text-[10.5px]">+2 more ↗</span>
          </div>
        </div>
      </Step>
      <Connector index={1} />
      <Step index={2} outcome="Reviewed" icon="folder" title="Evidence" noteTitle="Fresh until next quarter" note="Approved by a reviewer, linked to the control, and flagged before it goes stale.">
        <div className="rounded-lg border border-[#E3E7EC]">
          <div className="px-3 py-2.5">
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="file" size={16} className="shrink-0 text-[#5D6878]" />
              <span className="text-[13.5px] font-medium leading-snug text-[#0B0F17]">Q3 access review sign-off</span>
            </span>
            <span className="mt-2 flex gap-1.5"><Pill tone="success">Approved</Pill><Pill tone="success">Current</Pill></span>
          </div>
          <div className="flex items-center justify-between border-t border-[#EDF0F3] px-3 py-2 text-[12px] text-[#5D6878]">
            <span>Reviewed by Dana Okafor</span>
            <span className="font-mono text-[10.5px]">+3 more ↗</span>
          </div>
        </div>
      </Step>
      <SampleNote className="mt-5">Sample workspace · names are fictional</SampleNote>
    </figure>
  );
}
