import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { CSSProperties } from "react";
import { moduleBySlug } from "@/content/catalog";
import { frameworks, regions } from "@/content/frameworks";
import { industryPages } from "@/content/industries";
import { industries } from "@/content/navigation";
import { CtaPair, FaqSection, FinalCta, PageHero } from "@/components/sections/common";
import { SectionShell } from "@/components/sections/pillar";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { SectionHeading } from "@/components/ui/section-heading";
import { Panel } from "@/components/visuals/ui-kit";

export const dynamicParams = false;

export function generateStaticParams() {
  return industries.map((item) => ({ industry: item.slug }));
}

type Params = { params: Promise<{ industry: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { industry } = await params;
  const page = industryPages.find((item) => item.slug === industry);
  const meta = industries.find((item) => item.slug === industry);
  if (!page || !meta) return {};
  return { title: meta.name, description: page.lead, alternates: { canonical: `/solutions/${industry}/` } };
}

const regionName = (id: string) => regions.find((region) => region.id === id)?.name ?? "International";

export default async function IndustryPage({ params }: Params) {
  const { industry } = await params;
  const page = industryPages.find((item) => item.slug === industry);
  const meta = industries.find((item) => item.slug === industry);
  if (!page || !meta) notFound();
  const relevant = page.frameworks.map((id) => frameworks.find((item) => item.id === id)).filter((value): value is NonNullable<typeof value> => !!value);

  return (
    <main id="main-content">
      <PageHero
        eyebrow={page.eyebrow}
        title={page.headline}
        lead={<p>{page.lead}</p>}
        visual={
          <Panel title="Frameworks you answer to" icon={meta.icon} meta={<span className="font-mono text-[11px] text-faint">{relevant.length} in the library</span>} className="mx-auto w-full max-w-[520px]" bodyClassName="p-0">
            <ul className="divide-y divide-line">
              {relevant.slice(0, 7).map((item, index) => (
                <li key={item.id} className="flex items-center justify-between gap-3 px-4 py-3" data-reveal style={{ ["--reveal-delay" as string]: `${index * 60}ms` } as CSSProperties}>
                  <span className="min-w-0">
                    <span className="block truncate text-[14px] font-medium text-ink">{item.shortName}</span>
                    <span className="block truncate text-[12px] text-dim">{regionName(item.region)} · {item.issuer.split("(")[0].trim()}</span>
                  </span>
                  <StatusBadge status={item.status} size="xs" hideLive={false} />
                </li>
              ))}
            </ul>
          </Panel>
        }
      >
        <CtaPair source={`industry-${industry}`} className="mt-8" />
        <ul className="mt-8 flex flex-wrap gap-2" aria-label="Who this is for">
          {page.audiences.map((audience) => <li key={audience} className="chip">{audience}</li>)}
        </ul>
      </PageHero>

      <SectionShell labelledBy="obligations-title">
        <SectionHeading eyebrow="What you answer to" title="The obligations behind the work." id="obligations-title" lead="A sample of what organisations like yours are required to do in our markets. Requirements change; always confirm them with your regulator or advisers." />
        <ul className="mt-12 grid grid-cols-1 gap-4 md:grid-cols-2">
          {page.obligations.map((obligation, index) => (
            <li key={obligation.title} className="flex flex-col rounded-2xl border border-line bg-surface p-6 shadow-card" data-reveal style={{ ["--reveal-delay" as string]: `${(index % 2) * 80}ms` } as CSSProperties}>
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{regionName(obligation.region)}</span>
              <h3 className="mt-3 text-[17px] font-semibold leading-snug">{obligation.title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-dim">{obligation.text}</p>
              <p className="mt-auto flex items-center gap-1.5 pt-4 text-[12.5px] text-faint"><Icon name="scroll" size={14} />{obligation.source}</p>
            </li>
          ))}
        </ul>
      </SectionShell>

      <SectionShell labelledBy="helps-title" tone="subtle">
        <SectionHeading eyebrow="How Verity helps" title="One place to do the work, and prove it." id="helps-title" />
        <ul className="mt-12 grid grid-cols-1 gap-5 md:grid-cols-2">
          {page.helps.map((help, index) => (
            <li key={help.title} className="flex flex-col rounded-2xl border border-line bg-surface p-7" data-reveal style={{ ["--reveal-delay" as string]: `${(index % 2) * 80}ms` } as CSSProperties}>
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-sky-50 text-sky-700"><Icon name={help.icon} size={21} /></span>
              <h3 className="mt-5 text-[18px] font-semibold">{help.title}</h3>
              <p className="mt-2 text-[15px] leading-relaxed text-dim">{help.text}</p>
              <ul className="mt-auto flex flex-wrap gap-2 pt-5">
                {help.modules.map((slug) => {
                  const mod = moduleBySlug(slug);
                  if (!mod) return null;
                  return <li key={slug}><Link href={`/platform/${slug}/`} className="chip">{mod.name}<StatusBadge status={mod.status} size="xs" /></Link></li>;
                })}
              </ul>
            </li>
          ))}
        </ul>
      </SectionShell>

      <SectionShell labelledBy="workflow-title">
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
          <SectionHeading eyebrow="An example" title={page.workflow.title} id="workflow-title" lead={page.workflow.intro} />
          <ol data-animate className="relative space-y-4">
            <span className="absolute bottom-6 start-[19px] top-6 w-px bg-line" aria-hidden="true" />
            {page.workflow.steps.map((step, index) => (
              <li key={step.title} className="seq relative flex gap-5" style={{ ["--i" as string]: index, ["--step" as string]: "160ms" } as CSSProperties}>
                <span className="relative z-[1] grid h-10 w-10 shrink-0 place-items-center rounded-full border border-line bg-surface font-mono text-[13px] font-semibold text-ink shadow-card">{index + 1}</span>
                <span className="rounded-xl border border-line bg-surface p-4 shadow-card">
                  <span className="block text-[16px] font-semibold text-ink">{step.title}</span>
                  <span className="mt-1 block text-[14.5px] leading-relaxed text-dim">{step.text}</span>
                </span>
              </li>
            ))}
          </ol>
        </div>
      </SectionShell>

      <SectionShell labelledBy="frameworks-title" tone="subtle">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <SectionHeading eyebrow="Framework library" title="Frameworks for your industry." id="frameworks-title" size="md" />
          <Link href="/frameworks/" className="link-arrow shrink-0 text-[15px]">Browse the full library<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></Link>
        </div>
        <ul className="mt-10 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {relevant.map((item) => (
            <li key={item.id}>
              <Link href={`/frameworks/?f=${item.id}`} className="flex h-full flex-col rounded-xl border border-line bg-surface p-4 transition hover:border-line-strong hover:shadow-card">
                <span className="flex items-start justify-between gap-3">
                  <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{regionName(item.region)}</span>
                  <StatusBadge status={item.status} size="xs" hideLive={false} />
                </span>
                <span className="mt-2 text-[15.5px] font-semibold text-ink">{item.shortName}</span>
                <span className="mt-1 line-clamp-2 text-[13.5px] leading-snug text-dim">{item.summary}</span>
              </Link>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-[13.5px] text-dim">Only the SOC 2 library ships today; the others are coming soon. Until then you can add your own controls for any framework and link evidence to them.</p>
      </SectionShell>

      <SectionShell labelledBy="roles-title">
        <SectionHeading eyebrow="Who uses it" title="Built for the people who answer for the programme." id="roles-title" size="md" />
        <ul className="mt-8 flex flex-wrap gap-2">
          {page.roles.map((role) => <li key={role} className="rounded-full border border-line bg-surface px-3.5 py-2 text-[14.5px] text-body">{role}</li>)}
        </ul>
      </SectionShell>

      <FaqSection items={page.faqs} title={`${meta.name}, answered.`} />
      <FinalCta title="See Verity with your frameworks." lead="Tell us your regulator and the frameworks you answer to. We will show you how the work fits together." source={`industry-${industry}-final`} />
    </main>
  );
}
