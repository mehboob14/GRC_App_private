import type { CSSProperties } from "react";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { CodeChip, Pill, SampleNote } from "./ui-kit";

/** The AI assistant (coming soon): a prompt, the "thinking" note, and a draft that waits for a person. */
export function AssistantDraft() {
  return (
    <figure data-animate className="relative mx-auto w-full max-w-[560px]" style={{ ["--step" as string]: "380ms" } as CSSProperties}>
      <div className="seq ms-auto w-[86%] rounded-2xl rounded-br-md border border-[#DCE3EC] bg-[#EEF2F7] px-4 py-3 text-[14px] leading-snug text-[#0B0F17]" style={{ ["--i" as string]: 0 } as CSSProperties}>
        Draft an access control policy for a 400-person bank, and map it to our access controls.
      </div>
      <div className="seq mt-4 rounded-2xl border border-[#E3E7EC] bg-white p-5 shadow-float" style={{ ["--i" as string]: 1 } as CSSProperties}>
        <div className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-1.5 text-[13px] text-[#8A94A3]"><Icon name="caret-down" size={12} weight="bold" className="rotate-180" />Thought for 6 seconds</p>
          <StatusBadge status="soon" size="xs" />
        </div>
        <p className="mt-3 text-[14px] leading-relaxed text-[#363F4E]">Here is a first draft from your template library. It is marked as an <strong className="font-semibold text-[#0B0F17]">AI draft</strong> and cannot be approved or published until a reviewer signs it off.</p>
        <div className="seq mt-4 rounded-xl border border-[#E3E7EC]" style={{ ["--i" as string]: 2 } as CSSProperties}>
          <div className="flex items-center justify-between gap-3 border-b border-[#EDF0F3] px-4 py-3">
            <span className="flex min-w-0 items-center gap-2">
              <Icon name="file" size={17} className="shrink-0 text-[#5D6878]" />
              <span className="truncate text-[14px] font-medium text-[#0B0F17]">Access control policy</span>
            </span>
            <span className="flex shrink-0 gap-1.5"><Pill tone="pending" icon="sparkle">AI draft</Pill><Pill tone="warning">Needs review</Pill></span>
          </div>
          <ol className="space-y-1.5 px-4 py-3 text-[13px] text-[#363F4E]">
            {["Purpose and scope", "Joiners, movers and leavers", "Privileged access", "Quarterly access reviews", "Exceptions and approvals"].map((item, index) => (
              <li key={item} className="flex gap-2"><span className="font-mono text-[11px] leading-5 text-[#8A94A3]">{String(index + 1).padStart(2, "0")}</span>{item}</li>
            ))}
          </ol>
          <div className="flex flex-wrap items-center gap-1.5 border-t border-[#EDF0F3] px-4 py-3">
            <span className="me-1 text-[12px] text-[#5D6878]">Mapped to</span>
            <CodeChip>IAM-02</CodeChip><CodeChip>IAM-07</CodeChip><CodeChip>HR-05</CodeChip><CodeChip>CC6.3</CodeChip>
          </div>
        </div>
        <div className="mt-4 flex gap-2">
          <span className="btn btn-dark btn-sm pointer-events-none">Send for review</span>
          <span className="btn btn-outline btn-sm pointer-events-none">Open draft</span>
        </div>
      </div>
      <SampleNote className="mt-5">Coming soon · concept shown with sample content</SampleNote>
    </figure>
  );
}
