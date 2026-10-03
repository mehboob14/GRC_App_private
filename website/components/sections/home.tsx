import Link from "next/link";
import type { CSSProperties } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";
import { ArrowLink } from "@/components/ui/button-link";
import { StatusBadge } from "@/components/ui/status-badge";
import { SectionHeading } from "@/components/ui/section-heading";
import { IsometricHero } from "@/components/visuals/isometric-hero";
import { ControlMapping } from "@/components/visuals/control-mapping";
import { TraceGraph } from "@/components/visuals/trace-graph";
import { githubChecks, integrationCapabilities, libraryFacts } from "@/content/catalog";
import { frameworks, regions } from "@/content/frameworks";
import { industries } from "@/content/navigation";
import { docsTeaser, facts, frameworksTeaser, hero, industriesTeaser, integrationsTeaser, problem, securityTeaser, steps, trace } from "@/content/home";
import { CtaPair } from "./common";
import { RegionTabs } from "./region-tabs";
import { SectionShell } from "./pillar";

export function HomeHero() {
  return (
    <section aria-labelledby="hero-title" className="relative overflow-hidden bg-gradient-to-b from-[#E6ECF2] via-[#EFF3F7] to-white">
      <div className="frame grid grid-cols-1 items-center gap-8 pb-12 pt-14 lg:min-h-[620px] lg:grid-cols-[1.08fr_1fr] lg:gap-4 lg:pb-16 lg:pt-8">
        <div className="relative z-[1]">
          <p className="eyebrow">{hero.eyebrow}</p>
          <h1 id="hero-title" className="mt-6 max-w-[17ch] font-serif text-[clamp(2.6rem,1.4rem+3.9vw,4.1rem)] font-normal leading-[1.04] tracking-[-0.022em] text-ink">{hero.title}</h1>
          <p className="mt-7 max-w-[34rem] text-lg leading-relaxed text-body sm:text-[19px]">{hero.lead}</p>
          <CtaPair source="hero" className="mt-9" />
        </div>
        <div className="relative -mx-4 sm:mx-0 lg:-me-24 xl:-me-32">
          <IsometricHero className="h-auto w-full" />
        </div>
      </div>
    </section>
  );
}

export function FactStrip() {
  return (
    <section aria-label={facts.title} className="border-y border-line bg-surface">
      <div className="frame-ruled">
        <div className="frame flex flex-col gap-6 py-10 lg:flex-row lg:items-center lg:justify-between lg:gap-10 lg:py-12">
          <div>
            <h2 className="font-serif text-display-sm">{facts.title}</h2>
            <p className="mt-1 text-[14px] text-dim">{facts.note}</p>
          </div>
          <dl className="grid grid-cols-2 gap-x-8 gap-y-5 sm:flex sm:flex-wrap sm:items-center sm:gap-x-10">
            {libraryFacts.map((fact, index) => (
              <div key={fact.label} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3" data-reveal style={{ ["--reveal-delay" as string]: `${index * 80}ms` } as CSSProperties}>
                <dt className="font-mono text-[11.5px] uppercase tracking-[0.12em] text-dim">{fact.label}</dt>
                <dd className="w-fit rounded-md bg-sky-100 px-2 py-1 font-mono text-[14px] font-semibold text-sky-900">{fact.value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </section>
  );
}

export function Problem() {
  return (
    <SectionShell id="problem" labelledBy="problem-title">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.9fr_1.1fr] lg:gap-20">
        <div>
          <SectionHeading eyebrow={problem.eyebrow} title={problem.title} id="problem-title" lead={problem.lead} />
        </div>
        <div>
          <ul className="grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2">
            {problem.pains.map((pain, index) => (
              <li key={pain.title} className="bg-surface p-6" data-reveal style={{ ["--reveal-delay" as string]: `${index * 90}ms` } as CSSProperties}>
                <span className="grid h-9 w-9 place-items-center rounded-lg border border-line text-ink"><Icon name={pain.icon} size={19} /></span>
                <h3 className="mt-4 text-[16.5px] font-semibold">{pain.title}</h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-dim">{pain.text}</p>
              </li>
            ))}
          </ul>
          <p className="mt-6 flex gap-3 rounded-xl border border-sky-200 bg-sky-50/70 p-5 text-[15.5px] leading-relaxed text-ink" data-reveal>
            <Icon name="check" size={20} weight="fill" className="mt-0.5 shrink-0 text-sky-600" />
            {problem.resolution}
          </p>
        </div>
      </div>
    </SectionShell>
  );
}

export function HowItWorks() {
  return (
    <SectionShell id="how-it-works" labelledBy="how-title" tone="subtle">
      <SectionHeading eyebrow="How it works" title="From first login to audit-ready, in four steps." id="how-title" />
      <ol data-animate className="relative mt-14 grid grid-cols-1 gap-8 md:grid-cols-4 md:gap-6">
        <span className="pointer-events-none absolute left-0 right-0 top-[22px] hidden h-px bg-line md:block" aria-hidden="true">
          <span className="grow-x block h-full bg-sky-400" style={{ ["--base" as string]: "300ms" } as CSSProperties} />
        </span>
        {steps.map((step, index) => (
          <li key={step.title} className="seq relative" style={{ ["--i" as string]: index, ["--step" as string]: "200ms" } as CSSProperties}>
            <span className="relative z-[1] flex h-11 w-11 items-center justify-center rounded-full border border-line bg-surface font-mono text-[13px] font-semibold text-ink shadow-card">{index + 1}</span>
            <Icon name={step.icon} size={22} className="mt-6 text-sky-600" />
            <h3 className="mt-3 text-[17px] font-semibold">{step.title}</h3>
            <p className="mt-1.5 text-[15px] leading-relaxed text-dim">{step.text}</p>
          </li>
        ))}
      </ol>
    </SectionShell>
  );
}

export function TraceSection() {
  return (
    <SectionShell id="connected" labelledBy="trace-title">
      <SectionHeading eyebrow={trace.eyebrow} title={trace.title} id="trace-title" lead={trace.lead} />
      <div className="mt-12">
        <TraceGraph />
      </div>
    </SectionShell>
  );
}

export function FrameworksTeaser() {
  return (
    <SectionShell id="frameworks" labelledBy="frameworks-title" tone="subtle">
      <div className="grid grid-cols-1 gap-14 lg:grid-cols-2 lg:gap-16">
        <div className="min-w-0">
          <SectionHeading eyebrow={frameworksTeaser.eyebrow} title={frameworksTeaser.title} id="frameworks-title" lead={frameworksTeaser.lead} />
          <div className="mt-8">
            <RegionTabs regions={regions} frameworks={frameworks} />
          </div>
          <p className="mt-6 flex gap-2 text-[13.5px] text-dim"><Icon name="info" size={16} className="mt-0.5 shrink-0" />{frameworksTeaser.note}</p>
          <ArrowLink href="/frameworks/" className="mt-5">Browse all {frameworks.length} frameworks</ArrowLink>
        </div>
        <div className="min-w-0 lg:pt-24">
          <p className="eyebrow mb-5">Map once, satisfy many</p>
          <ControlMapping />
        </div>
      </div>
    </SectionShell>
  );
}

export function IndustriesGrid() {
  const highlights: Record<string, string[]> = {
    "banking-financial-services": ["SBP ETGRMF", "CBUAE", "APRA CPS 234", "NYDFS Part 500"],
    "fintech-payments": ["PCI DSS", "SBP TRMF", "SOC 2", "GLBA"],
    healthcare: ["HIPAA", "ADHICS", "Privacy Act", "ISO 27701"],
    "saas-technology": ["SOC 2", "ISO 27001", "IRAP", "GDPR"],
    "government-public-sector": ["NIST 800-53", "Essential Eight", "UAE IAS", "DESC ISR"],
  };
  return (
    <SectionShell id="industries" labelledBy="industries-title">
      <SectionHeading eyebrow={industriesTeaser.eyebrow} title={industriesTeaser.title} id="industries-title" lead={industriesTeaser.lead} />
      <ul className="mt-12 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {industries.map((industry, index) => (
          <li key={industry.slug} data-reveal style={{ ["--reveal-delay" as string]: `${index * 70}ms` } as CSSProperties}>
            <Link href={`/solutions/${industry.slug}/`} className="group flex h-full flex-col rounded-2xl border border-line bg-surface p-5 shadow-card transition hover:-translate-y-0.5 hover:border-line-strong hover:shadow-float">
              <span className="grid h-10 w-10 place-items-center rounded-lg bg-sky-50 text-sky-700"><Icon name={industry.icon} size={21} /></span>
              <h3 className="mt-5 text-[17px] font-semibold leading-snug">{industry.name}</h3>
              <p className="mt-1.5 text-[14px] leading-snug text-dim">{industry.short}</p>
              <span className="mt-4 flex flex-wrap gap-1.5">
                {highlights[industry.slug].map((label) => <span key={label} className="rounded border border-line px-1.5 py-0.5 font-mono text-[10.5px] text-dim">{label}</span>)}
              </span>
              <span className="link-arrow mt-auto pt-6 text-[14px]">Explore<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow" /></span>
            </Link>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}

export function IntegrationsGrid() {
  return (
    <SectionShell id="integrations" labelledBy="integrations-title" tone="subtle">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.85fr_1.15fr] lg:gap-16">
        <div>
          <SectionHeading eyebrow={integrationsTeaser.eyebrow} title={integrationsTeaser.title} id="integrations-title" lead={integrationsTeaser.lead} />
          <div className="mt-8 rounded-xl border border-line bg-surface p-5 shadow-card" data-reveal>
            <p className="flex items-center gap-2 text-[14px] font-semibold text-ink"><Icon name="code" size={18} />GitHub checks, every day</p>
            <ul className="mt-3 grid gap-1.5">
              {githubChecks.map((check) => (
                <li key={check} className="flex items-center gap-2 text-[13.5px] text-body"><Icon name="check" size={15} weight="fill" className="text-emerald-600" />{check}</li>
              ))}
            </ul>
          </div>
          <p className="mt-5 flex gap-2 text-[13.5px] text-dim"><Icon name="info" size={16} className="mt-0.5 shrink-0" />{integrationsTeaser.note}</p>
          <ArrowLink href="/platform/integrations/" className="mt-5">See every integration</ArrowLink>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {integrationCapabilities.map((capability, index) => (
            <div key={capability.name} className="rounded-xl border border-line bg-surface p-5" data-reveal style={{ ["--reveal-delay" as string]: `${index * 70}ms` } as CSSProperties}>
              <p className="flex items-center gap-2 text-[14.5px] font-semibold text-ink"><Icon name={capability.icon} size={18} className="text-dim" />{capability.name}</p>
              <p className="mt-1 text-[13px] text-dim">{capability.description}</p>
              <ul className="mt-4 flex flex-wrap gap-1.5">
                {capability.providers.slice(0, 7).map((provider) => (
                  <li key={provider.name} className={cn("inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[12.5px]", provider.status === "live" ? "border-emerald-200 bg-emerald-50 font-medium text-emerald-800" : "border-line bg-subtle text-body")}>
                    {provider.status === "live" && <span className="relative flex h-1.5 w-1.5"><span className="pulse-ring absolute inset-0 rounded-full bg-emerald-400" /><span className="relative h-1.5 w-1.5 rounded-full bg-emerald-500" /></span>}
                    {provider.name}
                  </li>
                ))}
                {capability.providers.length > 7 && <li className="px-1 py-1 text-[12.5px] text-dim">+{capability.providers.length - 7} more</li>}
              </ul>
              {capability.providers.every((provider) => provider.status === "soon") && <StatusBadge status="soon" size="xs" className="mt-3" />}
            </div>
          ))}
        </div>
      </div>
    </SectionShell>
  );
}

export function SecurityGrid() {
  return (
    <SectionShell id="security" labelledBy="security-title">
      <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
        <SectionHeading eyebrow={securityTeaser.eyebrow} title={securityTeaser.title} id="security-title" lead={securityTeaser.lead} />
        <ArrowLink href="/security/" className="shrink-0">How we protect your workspace</ArrowLink>
      </div>
      <ul className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
        {securityTeaser.items.map((item, index) => (
          <li key={item.title} className="bg-surface p-6 lg:p-7" data-reveal style={{ ["--reveal-delay" as string]: `${index * 70}ms` } as CSSProperties}>
            <Icon name={item.icon} size={22} className="text-sky-600" />
            <h3 className="mt-4 text-[16.5px] font-semibold">{item.title}</h3>
            <p className="mt-1.5 text-[15px] leading-relaxed text-dim">{item.text}</p>
          </li>
        ))}
      </ul>
    </SectionShell>
  );
}

export function DocsTeaser() {
  return (
    <SectionShell id="docs" labelledBy="docs-title" tone="subtle">
      <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-16">
        <div>
          <SectionHeading eyebrow={docsTeaser.eyebrow} title={docsTeaser.title} id="docs-title" lead={docsTeaser.lead} />
          <Link href="/docs/" className="mt-8 flex max-w-sm items-center gap-3 rounded-xl border border-line-strong bg-surface px-4 py-3 text-[15px] text-dim shadow-card transition hover:border-[#b6bdc9]">
            <Icon name="search" size={18} />
            Search the documentation
            <span className="ms-auto flex gap-1 font-mono text-[11px]"><kbd className="rounded border border-line px-1.5 py-0.5">⌘</kbd><kbd className="rounded border border-line px-1.5 py-0.5">K</kbd></span>
          </Link>
        </div>
        <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {docsTeaser.links.map((link, index) => (
            <li key={link.href} data-reveal style={{ ["--reveal-delay" as string]: `${index * 60}ms` } as CSSProperties}>
              <Link href={link.href} className="group flex h-full items-start gap-4 rounded-xl border border-line bg-surface p-5 transition hover:border-line-strong hover:shadow-card">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line text-ink group-hover:border-sky-200 group-hover:text-sky-700"><Icon name={link.icon} size={18} /></span>
                <span>
                  <span className="flex items-center gap-1.5 text-[15.5px] font-semibold text-ink">{link.title}<Icon name="arrow-right" size={14} weight="bold" className="btn-arrow text-dim transition-transform group-hover:translate-x-0.5" /></span>
                  <span className="mt-1 block text-[14px] text-dim">{link.text}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </SectionShell>
  );
}
