import type { Metadata } from "next";
import { cn } from "@/lib/cn";
import { getSiteConfig } from "@/lib/site-config";
import { comparison, pricingFaqs, tiers } from "@/content/pricing";
import { FaqSection, FinalCta } from "@/components/sections/common";
import { PricingTable } from "@/components/sections/pricing-table";
import { DemoButton } from "@/components/site/demo-button";
import { Icon } from "@/components/ui/icon";

export const metadata: Metadata = {
  title: "Pricing",
  description: "Four plans, from your first SOC 2 audit to a regulated bank's full programme. Talk to our team for a quote.",
  alternates: { canonical: "/pricing/" },
};

export default function PricingPage() {
  const { trialUrl } = getSiteConfig();
  return (
    <main id="main-content">
      <section className="bg-gradient-to-b from-[#E9EEF3] via-[#F3F6F9] to-white">
        <div className="frame pb-14 pt-14 text-center lg:pb-16 lg:pt-20">
          <p className="eyebrow">Pricing</p>
          <h1 className="mx-auto mt-5 max-w-3xl font-serif text-display-xl font-normal">A plan for where your programme is today.</h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-dim">Every plan includes the core platform and the SOC 2 library. Plans differ by module, so moving up adds to the workspace you already have. Talk to our team for a quote.</p>
        </div>
      </section>

      <section aria-label="Plans" className="frame -mt-2 pb-20">
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          {tiers.map((tier, index) => (
            <li key={tier.id} data-reveal style={{ ["--reveal-delay" as string]: `${index * 80}ms` }} className={cn("flex flex-col rounded-2xl border p-6 shadow-card", tier.dark ? "border-[#1d2533] bg-[#0B0F17] text-white" : "border-line bg-surface")}>
              <h2 className={cn("text-[20px] font-semibold", tier.dark ? "text-white" : "text-ink")}>{tier.name}</h2>
              <p className={cn("mt-1 font-serif text-[22px] leading-snug", tier.dark ? "text-white" : "text-ink")}>{tier.tagline}</p>
              <p className={cn("mt-3 text-[14px] leading-snug", tier.dark ? "text-white/70" : "text-dim")}>{tier.bestFor}</p>
              <DemoButton variant={tier.dark ? "light" : "dark"} className="mt-6 w-full" interest={`pricing:${tier.id}`} source={`pricing-${tier.id}`}>Talk to sales</DemoButton>
              <ul className={cn("mt-6 space-y-2.5 border-t pt-5 text-[14px] leading-snug", tier.dark ? "border-white/15 text-white/85" : "border-line text-body")}>
                {tier.highlights.map((item) => {
                  const soon = item.includes("(coming soon)");
                  return (
                    <li key={item} className="flex gap-2.5">
                      <Icon name={soon ? "circle-dashed" : "check-plain"} size={16} weight="bold" className={cn("mt-0.5 shrink-0", soon ? (tier.dark ? "text-indigo-300" : "text-indigo-500") : tier.dark ? "text-sky-300" : "text-emerald-600")} />
                      <span>{item.replace(" (coming soon)", "")}{soon && <span className={cn("ms-1.5 whitespace-nowrap text-[11.5px] font-medium", tier.dark ? "text-indigo-300" : "text-indigo-700")}>Coming soon</span>}</span>
                    </li>
                  );
                })}
              </ul>
            </li>
          ))}
        </ul>
        <p className="mt-6 text-center text-[14px] text-dim">
          Prefer to explore first? <a href={trialUrl} className="font-medium text-accent hover:text-accent-strong">Start a trial</a> and follow the Get Started checklist.
        </p>
      </section>

      <section aria-labelledby="compare-title" className="border-t border-line">
        <div className="frame py-20">
          <div className="mb-10 max-w-2xl">
            <p className="eyebrow">Compare plans</p>
            <h2 id="compare-title" className="mt-4 font-serif text-display-md">What each plan includes.</h2>
            <p className="mt-4 text-[16.5px] leading-relaxed text-dim">Live features are marked with a tick. Items marked coming soon are on our roadmap and join the plans shown when they ship.</p>
          </div>
          <PricingTable tiers={tiers} groups={comparison} />
        </div>
      </section>

      <FaqSection items={pricingFaqs} title="Pricing questions." />
      <FinalCta title="Get a quote for your programme." lead="Tell us the frameworks you answer to and the size of your organisation. We will recommend a plan and send a proposal." source="pricing-final" interest="pricing" />
    </main>
  );
}
