import type { Metadata } from "next";
import type { CSSProperties } from "react";
import { FinalCta, PageHero } from "@/components/sections/common";
import { SectionShell } from "@/components/sections/pillar";
import { SectionHeading } from "@/components/ui/section-heading";
import { Icon, type IconName } from "@/components/ui/icon";
import { TraceGraph } from "@/components/visuals/trace-graph";
import { ControlMapping } from "@/components/visuals/control-mapping";
import { Pill } from "@/components/visuals/ui-kit";
import { CtaPair } from "@/components/sections/common";

export const metadata: Metadata = {
  title: "Why Verity",
  description: "One connected record for compliance, risk and security: map once, prove continuously, keep every decision, and never mistake a broken connection for a failed control.",
  alternates: { canonical: "/why-verity/" },
};

const principles: { icon: IconName; title: string; text: string }[] = [
  { icon: "graph", title: "One record, every relationship", text: "Controls, evidence, policies, risks, vendors, assets and vulnerabilities are linked records. Follow any of them to the others in a click, and prove the chain to an auditor." },
  { icon: "tree", title: "Map once, satisfy many", text: "Requirements map to one shared control set, and evidence attaches to controls rather than to frameworks. Work you do for one framework counts for every framework that asks for it." },
  { icon: "warning", title: "An error is never a fail", text: "When a connection breaks, Verity says it could not check. It never shows a broken integration as a failed control, so a red status always means something real." },
  { icon: "user-check", title: "People decide", text: "Wherever AI helps, it drafts and suggests. A person approves, publishes and decides, and AI content stays marked as such." },
  { icon: "scroll", title: "History you cannot rewrite", text: "Every change is written to an append-only audit log with the before and the after. Compliance records are retired with a reason, never deleted." },
  { icon: "lock", title: "Sealed workspaces", text: "Each organisation's data is isolated by the database on every query, with automated tests that prove it on every change." },
];

const comparison: { capability: string; sheets: string; point: string; verity: string }[] = [
  { capability: "Frameworks and controls", sheets: "One sheet per framework", point: "Often one framework per tool", verity: "One control set mapped to every framework" },
  { capability: "Evidence", sheets: "Shared drives, no renewal dates", point: "Separate from risks and vendors", verity: "Linked to controls, with freshness" },
  { capability: "Vendors and risks", sheets: "Email threads and trackers", point: "Separate risk and vendor tools", verity: "Linked records with owners and decisions" },
  { capability: "Assets and vulnerabilities", sheets: "Scanner exports in a folder", point: "A security tool with no compliance view", verity: "Findings tied to assets, risks and controls" },
  { capability: "Accountability", sheets: "Whoever touched it last", point: "Audit trail per tool", verity: "One append-only audit log" },
];

export default function WhyVerityPage() {
  return (
    <main id="main-content">
      <PageHero
        eyebrow="Why Verity"
        title="One source of truth, instead of five places to look."
        lead={<p>Most programmes run on spreadsheets and a handful of point tools that do not talk to each other. Verity puts the whole programme in one connected record, so you can see what is true, prove it, and decide what to do next.</p>}
      >
        <CtaPair source="why-hero" className="mt-8" />
      </PageHero>

      <SectionShell id="principles" labelledBy="principles-title">
        <SectionHeading eyebrow="What makes it different" title="Built on six decisions we will not compromise." id="principles-title" />
        <ul className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {principles.map((item, index) => (
            <li key={item.title} className="bg-surface p-7" data-reveal style={{ ["--reveal-delay" as string]: `${index * 70}ms` } as CSSProperties}>
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-sky-50 text-sky-700"><Icon name={item.icon} size={21} /></span>
              <h3 className="mt-5 text-[18px] font-semibold">{item.title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-dim">{item.text}</p>
            </li>
          ))}
        </ul>
      </SectionShell>

      <SectionShell id="trace" labelledBy="trace-title" tone="subtle">
        <SectionHeading eyebrow="See it" title="From a finding to the proof, in five steps." id="trace-title" lead="Select each step. This is the chain an auditor follows, and in Verity every link is a real record with its own history." />
        <div className="mt-12"><TraceGraph /></div>
      </SectionShell>

      <SectionShell id="map-once" labelledBy="map-title">
        <div className="grid grid-cols-1 items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <SectionHeading eyebrow="Map once" title="The work you do for SOC 2 counts for what comes next." id="map-title" lead="A quarterly access review is one control. When further framework libraries arrive, the same control, with the same evidence, answers their requirements too. Nothing is collected twice." />
          <ControlMapping />
        </div>
      </SectionShell>

      <SectionShell id="compare" labelledBy="compare-title" tone="subtle">
        <SectionHeading eyebrow="Compared" title="Why teams move off spreadsheets and point tools." id="compare-title" />
        <ul className="mt-10 space-y-3 md:hidden">
          {comparison.map((row) => (
            <li key={row.capability} className="rounded-2xl border border-line bg-surface p-5">
              <p className="text-[16px] font-semibold text-ink">{row.capability}</p>
              <dl className="mt-3 space-y-2 text-[14.5px]">
                <div><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Spreadsheets and email</dt><dd className="text-dim">{row.sheets}</dd></div>
                <div><dt className="text-[12px] font-medium uppercase tracking-wide text-faint">Separate point tools</dt><dd className="text-dim">{row.point}</dd></div>
                <div className="rounded-lg bg-sky-50/70 p-2.5"><dt className="text-[12px] font-medium uppercase tracking-wide text-sky-800">Verity</dt><dd className="flex items-start gap-2 text-ink"><Icon name="check" size={16} weight="fill" className="mt-0.5 shrink-0 text-emerald-600" />{row.verity}</dd></div>
              </dl>
            </li>
          ))}
        </ul>
        <div className="mt-10 hidden overflow-x-auto rounded-2xl border border-line bg-surface md:block">
          <table className="w-full min-w-[720px] border-collapse text-left text-[14.5px]">
            <thead>
              <tr className="border-b border-line">
                <th scope="col" className="px-5 py-4 text-[13px] font-medium text-dim">Capability</th>
                <th scope="col" className="px-5 py-4 text-[14px] font-semibold text-ink">Spreadsheets and email</th>
                <th scope="col" className="px-5 py-4 text-[14px] font-semibold text-ink">Separate point tools</th>
                <th scope="col" className="bg-sky-50/70 px-5 py-4 text-[14px] font-semibold text-ink">Verity</th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((row) => (
                <tr key={row.capability} className="border-b border-line last:border-b-0">
                  <th scope="row" className="px-5 py-4 font-medium text-ink">{row.capability}</th>
                  <td className="px-5 py-4 text-dim">{row.sheets}</td>
                  <td className="px-5 py-4 text-dim">{row.point}</td>
                  <td className="bg-sky-50/70 px-5 py-4 text-ink"><span className="flex items-start gap-2"><Icon name="check" size={17} weight="fill" className="mt-0.5 shrink-0 text-emerald-600" />{row.verity}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="mt-8 flex flex-wrap items-center gap-3 text-[14px] text-dim">
          <Pill tone="success">Live</Pill> Everything in the Verity column is available today with the SOC 2 library. Further libraries and connectors are coming soon.
        </div>
      </SectionShell>

      <FinalCta title="See your programme in one place." lead="Bring the frameworks you answer to. We will show you how Verity connects the work behind them." source="why-final" />
    </main>
  );
}
