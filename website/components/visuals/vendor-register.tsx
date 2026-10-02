import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { Pill, SampleNote, type Family } from "./ui-kit";

/** Third-party risk register, drawn like the reference's agent execution table. */

const rows: { vendor: string; category: string; tier: string; tierTone: Family; stage: string; findings: number; status: string; tone: Family }[] = [
  { vendor: "Harbor Cloud Hosting", category: "Infrastructure", tier: "Critical", tierTone: "danger", stage: "Findings", findings: 2, status: "Under review", tone: "progress" },
  { vendor: "Quillpay Gateway", category: "Payments", tier: "High", tierTone: "warning", stage: "Questionnaire", findings: 0, status: "Under review", tone: "progress" },
  { vendor: "Ledgerline Accounting", category: "Finance", tier: "High", tierTone: "warning", stage: "Monitoring", findings: 0, status: "Active", tone: "success" },
  { vendor: "Brightcall Support", category: "Customer support", tier: "Medium", tierTone: "pending", stage: "Approval", findings: 1, status: "Under review", tone: "progress" },
  { vendor: "Kestrel Couriers", category: "Logistics", tier: "Low", tierTone: "neutral", stage: "Offboarding", findings: 0, status: "Offboarding", tone: "warning" },
  { vendor: "Northgate Payroll", category: "HR", tier: "High", tierTone: "warning", stage: "Contracting", findings: 0, status: "Under review", tone: "progress" },
];

const matrix = [
  [0, 1, 0, 1, 0],
  [0, 2, 3, 1, 1],
  [1, 3, 4, 2, 0],
  [2, 4, 3, 1, 0],
  [3, 2, 1, 0, 0],
];

function heatColor(likelihood: number, impact: number) {
  const score = (likelihood + 1) * (impact + 1);
  if (score >= 15) return "#FDE1E7";
  if (score >= 9) return "#FCE9D7";
  if (score >= 4) return "#FBF1E4";
  return "#EEF6F1";
}

export function VendorRegister() {
  return (
    <figure data-animate className="relative w-full">
      <div className="rounded-2xl border border-[#E3E7EC] bg-white shadow-float">
        <div className="flex items-center gap-2.5 px-5 pb-3 pt-4">
          <Icon name="handshake" size={20} className="text-[#0B0F17]" />
          <span className="text-[15px] font-semibold text-[#0B0F17]">Vendors</span>
          <span className="ms-auto font-mono text-[11px] text-[#8A94A3]">38 vendors · 6 under review</span>
        </div>
        <div className="flex gap-6 border-b border-[#EDF0F3] px-5 text-[13.5px]" role="presentation">
          {["Overview", "Register", "Intake", "Findings"].map((tab) => (
            <span key={tab} className={cn("-mb-px border-b-2 pb-2.5", tab === "Register" ? "border-[#0A6CCB] font-medium text-[#0A6CCB]" : "border-transparent text-[#5D6878]")}>{tab}</span>
          ))}
        </div>
        <div className="px-5 pt-4">
          <div className="flex h-9 items-center gap-2 rounded-lg border border-[#D0D5DD] px-3 text-[13px] text-[#8A94A3] sm:max-w-[60%]">
            <Icon name="search" size={15} />Search vendors
          </div>
        </div>
        <div className="fade-bottom mt-4 overflow-hidden px-5 pb-2">
          <table className="w-full table-fixed text-left text-[13px]">
            <thead>
              <tr className="border-y border-[#EDF0F3] bg-[#F9FAFB] text-[11.5px] text-[#5D6878]">
                <th className="w-[42%] py-2.5 pl-3 font-medium">Vendor</th>
                <th className="w-[18%] py-2.5 font-medium">Tier</th>
                <th className="hidden w-[20%] py-2.5 font-medium sm:table-cell">Stage</th>
                <th className="w-[20%] py-2.5 pr-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.vendor} className="seq border-b border-[#EDF0F3]" style={{ ["--i" as string]: index, ["--step" as string]: "110ms", ["--base" as string]: "200ms" } as CSSProperties}>
                  <td className="py-3 pl-3">
                    <span className="block truncate font-medium text-[#0B0F17]">{row.vendor}</span>
                    <span className="block truncate text-[11.5px] text-[#8A94A3]">{row.category}</span>
                  </td>
                  <td className="py-3"><Pill tone={row.tierTone}>{row.tier}</Pill></td>
                  <td className="hidden py-3 text-[#363F4E] sm:table-cell">{row.stage}{row.findings > 0 && <span className="ms-1.5 rounded bg-[#FDEEF1] px-1 font-mono text-[10px] text-[#C01741]">{row.findings}</span>}</td>
                  <td className="py-3 pr-3"><Pill tone={row.tone}>{row.status}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="seq absolute -bottom-14 -right-2 hidden w-[210px] rounded-xl border border-[#E3E7EC] bg-white p-4 shadow-float sm:block lg:-right-16" style={{ ["--i" as string]: 3, ["--base" as string]: "500ms" } as CSSProperties} aria-hidden="true">
        <p className="text-[12.5px] font-semibold text-[#0B0F17]">Residual risk</p>
        <p className="text-[11px] text-[#8A94A3]">Likelihood × impact</p>
        <div className="mt-3 grid grid-cols-5 gap-1">
          {matrix.map((row, li) =>
            row.map((count, ii) => (
              <span key={`${li}-${ii}`} className="grid aspect-square place-items-center rounded-[4px] font-mono text-[10px] text-[#363F4E]" style={{ background: heatColor(4 - li, ii) }}>{count || ""}</span>
            )),
          )}
        </div>
      </div>
      <SampleNote className="mt-5">Sample vendors · names are fictional</SampleNote>
    </figure>
  );
}
