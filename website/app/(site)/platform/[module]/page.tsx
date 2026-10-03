import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";
import { moduleBySlug, moduleGroups, modules } from "@/content/catalog";
import { modulePages } from "@/content/modules";
import { CtaPair, FaqSection, FinalCta, PageHero } from "@/components/sections/common";
import { ModuleVisual } from "@/components/sections/module-visual";
import { SectionShell } from "@/components/sections/pillar";
import { DemoButton } from "@/components/site/demo-provider";
import { Icon } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import { SectionHeading } from "@/components/ui/section-heading";

export const dynamicParams = false;

export function generateStaticParams() {
  return modules.map((item) => ({ module: item.slug }));
}

type Params = { params: Promise<{ module: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { module } = await params;
  const item = moduleBySlug(module);
  const page = modulePages.find((candidate) => candidate.slug === module);
  if (!item || !page) return {};
  return { title: item.status === "soon" ? `${item.name} (coming soon)` : item.name, description: page.lead, alternates: { canonical: `/platform/${item.slug}/` } };
}

export default async function ModulePage({ params }: Params) {
  const { module } = await params;
  const item = moduleBySlug(module);
  const page = modulePages.find((candidate) => candidate.slug === module);
  if (!item || !page) notFound();
  const soon = item.status === "soon";
  const group = moduleGroups.find((candidate) => candidate.id === item.group)!;
  const related = page.related.map((slug) => moduleBySlug(slug)).filter((value): value is NonNullable<typeof value> => !!value);

  return (
    <main id="main-content">
      <PageHero
        breadcrumb={
          <nav aria-label="Breadcrumb" className="mb-6 flex items-center gap-1.5 text-[13px] text-dim">
            <Link href="/platform/" className="hover:text-ink">Platform</Link>
            <Icon name="caret-right" size={11} weight="bold" className="text-faint" />
            <span>{group.name}</span>
            <Icon name="caret-right" size={11} weight="bold" className="text-faint" />
            <span className="text-ink" aria-current="page">{item.name}</span>
          </nav>
        }
        eyebrow={`${item.name}`}
        badge={<StatusBadge status={item.status} hideLive={false} />}
        title={page.headline}
        lead={<p>{page.lead}</p>}
        visual={<ModuleVisual visual={page.heroVisual} priority />}
      >
        {soon ? (
          <div className="mt-8 flex flex-wrap items-center gap-3">
            <DemoButton variant="dark" interest={item.slug} source={`module-${item.slug}`}>Tell us what you need<Icon name="arrow-right" size={16} weight="bold" className="btn-arrow" /></DemoButton>
            {item.docs && <Link href={`/docs/${item.docs}/`} className="btn btn-outline">Read the roadmap page</Link>}
          </div>
        ) : (
          <CtaPair source={`module-${item.slug}`} interest={item.slug} className="mt-8" />
        )}
        {page.facts && page.facts.length > 0 && (
          <dl className="mt-10 flex flex-wrap gap-x-8 gap-y-4 border-t border-line pt-6">
            {page.facts.map((fact) => (
              <div key={fact.label}>
                <dt className="font-mono text-[11px] uppercase tracking-[0.12em] text-dim">{fact.label}</dt>
                <dd className="mt-1 font-serif text-[30px] leading-none text-ink">{fact.value}</dd>
              </div>
            ))}
          </dl>
        )}
      </PageHero>

      {soon && (
        <div className="border-y border-dashed border-indigo-300 bg-indigo-50/60">
          <div className="frame flex flex-col gap-3 py-5 sm:flex-row sm:items-center">
            <Icon name="map" size={20} className="shrink-0 text-indigo-600" />
            <p className="text-[15px] text-ink"><strong className="font-semibold">{item.name} is coming soon.</strong> It is on our roadmap and not available in Verity yet. Here is what it will do, and what you can use today.</p>
          </div>
        </div>
      )}

      {page.sections.map((section, index) => (
        <section key={section.title} aria-labelledby={`section-${index}`} className={cn("border-t border-line", index % 2 === 1 && "bg-subtle")}>
          <div className="frame-ruled">
            <div className="frame grid grid-cols-1 items-center gap-12 py-20 lg:grid-cols-2 lg:gap-16 lg:py-24">
              <div className={cn("min-w-0", index % 2 === 1 && "lg:order-2")}>
                <p className="eyebrow" data-reveal>{section.eyebrow}</p>
                <h2 id={`section-${index}`} className="mt-4 font-serif text-display-md font-normal" data-reveal>{section.title}</h2>
                <p className="mt-4 text-[17px] leading-relaxed text-dim" data-reveal>{section.text}</p>
                <ul className="mt-6 space-y-2.5">
                  {section.bullets.map((bullet, bulletIndex) => (
                    <li key={bullet} className="flex gap-3 text-[15.5px] text-body" data-reveal style={{ ["--reveal-delay" as string]: `${bulletIndex * 70}ms` } as CSSProperties}>
                      <Icon name={soon ? "circle-dashed" : "check-plain"} size={17} weight="bold" className={cn("mt-0.5 shrink-0", soon ? "text-indigo-500" : "text-emerald-600")} />
                      {bullet}
                    </li>
                  ))}
                </ul>
              </div>
              <div className={cn("min-w-0", index % 2 === 1 && "lg:order-1")}>
                <ModuleVisual visual={section.visual} />
              </div>
            </div>
          </div>
        </section>
      ))}

      <SectionShell labelledBy="capabilities-title">
        <SectionHeading eyebrow={soon ? "Planned capabilities" : "Capabilities"} title={soon ? "What it will include." : "Everything it includes."} id="capabilities-title" />
        <ul className="mt-10 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
          {page.capabilities.map((capability, index) => (
            <li key={capability.title} className="bg-surface p-6" data-reveal style={{ ["--reveal-delay" as string]: `${(index % 3) * 70}ms` } as CSSProperties}>
              <div className="flex items-start justify-between gap-3">
                <Icon name={capability.icon} size={22} className={capability.status === "soon" ? "text-indigo-500" : "text-sky-600"} />
                <StatusBadge status={capability.status} size="xs" />
              </div>
              <h3 className="mt-4 text-[16.5px] font-semibold">{capability.title}</h3>
              <p className="mt-1.5 text-[14.5px] leading-relaxed text-dim">{capability.text}</p>
            </li>
          ))}
        </ul>
      </SectionShell>

      {page.today && page.today.length > 0 && (
        <SectionShell labelledBy="today-title" tone="subtle">
          <SectionHeading eyebrow="Available today" title="What you can use right now." id="today-title" />
          <ul className="mt-10 grid grid-cols-1 gap-4 md:grid-cols-3">
            {page.today.map((entry) => (
              <li key={entry.href}>
                <Link href={entry.href} className="group flex h-full flex-col rounded-2xl border border-line bg-surface p-6 shadow-card transition hover:-translate-y-0.5 hover:shadow-float">
                  <span className="flex items-center gap-2"><StatusBadge status="live" hideLive={false} size="xs" /></span>
                  <span className="mt-3 text-[17px] font-semibold text-ink">{entry.title}</span>
                  <span className="mt-1.5 text-[14.5px] leading-relaxed text-dim">{entry.text}</span>
                  <span className="link-arrow mt-auto pt-5 text-[14px]">Open<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></span>
                </Link>
              </li>
            ))}
          </ul>
        </SectionShell>
      )}

      <SectionShell labelledBy="connected-title" tone={page.today ? "plain" : "subtle"}>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionHeading eyebrow="Works with" title="Connected to the rest of Verity." id="connected-title" size="md" />
            <ul className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
              {related.map((other) => (
                <li key={other.slug}>
                  <Link href={`/platform/${other.slug}/`} className="flex h-full items-start gap-3 rounded-xl border border-line bg-surface p-4 transition hover:border-line-strong hover:shadow-card">
                    <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line text-ink"><Icon name={other.icon} size={18} /></span>
                    <span className="min-w-0">
                      <span className="flex flex-wrap items-center gap-2 text-[15px] font-semibold text-ink">{other.name}<StatusBadge status={other.status} size="xs" /></span>
                      <span className="mt-0.5 block text-[13.5px] leading-snug text-dim">{other.summary}</span>
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </div>
          <div>
            <SectionHeading eyebrow="Documentation" title="Learn how it works." id="docs-links-title" size="md" />
            <ul className="mt-8 divide-y divide-line rounded-xl border border-line bg-surface">
              {page.docs.map((doc) => (
                <li key={doc.href}>
                  <Link href={doc.href} className="group flex items-center gap-3 px-5 py-4 transition hover:bg-subtle">
                    <Icon name="book" size={18} className="text-dim" />
                    <span className="flex-1 text-[15px] font-medium text-ink">{doc.title}</span>
                    <Icon name="arrow-right" size={15} weight="bold" className="text-faint transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </SectionShell>

      <FaqSection items={page.faqs} title={`${item.name}, answered.`} />
      <FinalCta
        title={soon ? `Help shape ${item.name}.` : "See it with your own frameworks."}
        lead={soon ? "Tell us what you need from it. We prioritise the roadmap with the teams who will use it." : "Book a demo and we will walk through this module with the frameworks and regulators you answer to."}
        source={`module-${item.slug}-final`}
        interest={item.slug}
      />
    </main>
  );
}
