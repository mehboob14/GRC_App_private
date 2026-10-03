import type { Metadata } from "next";
import Link from "next/link";
import type { CSSProperties } from "react";
import { libraryFacts, moduleGroups, modules } from "@/content/catalog";
import { CtaPair, FinalCta, PageHero } from "@/components/sections/common";
import { SectionShell, StatusLegend } from "@/components/sections/pillar";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { SectionHeading } from "@/components/ui/section-heading";
import { TraceGraph } from "@/components/visuals/trace-graph";
import { PlatformMap } from "@/components/visuals/platform-map";
import { groupIcon } from "@/content/navigation";

export const metadata: Metadata = {
  title: "Platform overview",
  description: "Every Verity module in one view: compliance, risk, security and the platform that connects them, with what is live today and what is coming soon.",
  alternates: { canonical: "/platform/" },
};

export default function PlatformPage() {
  const live = modules.filter((item) => item.status === "live").length;
  return (
    <main id="main-content">
      <PageHero
        eyebrow="The Verity platform"
        title="Compliance, risk and security, in one connected platform."
        lead={<p>Eighteen modules share one record of your programme: the same people, controls, evidence and history. {live} are live today; the rest are on our roadmap and marked as coming soon.</p>}
        visual={<PlatformMap />}
      >
        <CtaPair source="platform-hero" className="mt-8" />
        <dl className="mt-10 flex flex-wrap gap-x-8 gap-y-4 border-t border-line pt-6">
          {libraryFacts.map((fact) => (
            <div key={fact.label}>
              <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{fact.label}</dt>
              <dd className="mt-1 font-serif text-[30px] leading-none text-ink">{fact.value}</dd>
            </div>
          ))}
        </dl>
      </PageHero>

      {moduleGroups.map((group, groupIndex) => (
        <section key={group.id} id={group.id} aria-labelledby={`group-${group.id}`} className={groupIndex % 2 === 1 ? "border-t border-line bg-subtle" : "border-t border-line"}>
          <div className="frame-ruled">
            <div className="frame grid grid-cols-1 gap-10 py-16 lg:grid-cols-[0.75fr_2fr] lg:gap-14 lg:py-20">
              <div>
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-sky-50 text-sky-700"><Icon name={groupIcon[group.id]} size={23} /></span>
                <h2 id={`group-${group.id}`} className="mt-5 font-serif text-display-md font-normal">{group.name}</h2>
                <p className="mt-3 text-[16px] leading-relaxed text-dim">{group.description}</p>
              </div>
              <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {modules.filter((item) => item.group === group.id).map((item, index) => (
                  <li key={item.slug} data-reveal style={{ ["--reveal-delay" as string]: `${index * 60}ms` } as CSSProperties}>
                    <Link href={`/platform/${item.slug}/`} className="group flex h-full items-start gap-4 rounded-2xl border border-line bg-surface p-5 shadow-card transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-float">
                      <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-line text-ink transition-colors group-hover:border-sky-200 group-hover:text-sky-700"><Icon name={item.icon} size={20} /></span>
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-2 text-[16.5px] font-semibold text-ink">{item.name}<StatusBadge status={item.status} size="xs" /></span>
                        <span className="mt-1 block text-[14.5px] leading-snug text-dim">{item.summary}</span>
                      </span>
                      <Icon name="arrow-right" size={16} weight="bold" className="mt-1 shrink-0 text-faint transition-transform group-hover:translate-x-0.5" />
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>
      ))}

      <SectionShell labelledBy="connected-title">
        <SectionHeading eyebrow="Why one platform" title="Every module shares one connected record." id="connected-title" lead="Follow a finding through the asset it sits on, the risk it creates, the control that treats it and the proof behind it. Every step is a real record, and every change is in the audit log." />
        <div className="mt-12"><TraceGraph /></div>
        <StatusLegend className="mt-10" />
      </SectionShell>

      <FinalCta title="Start with what you need today." lead="Most teams begin with frameworks, evidence and policies, then add risk, vendors and security as the programme grows." source="platform-final" />
    </main>
  );
}
