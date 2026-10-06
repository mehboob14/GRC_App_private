import type { Metadata } from "next";
import { Suspense } from "react";
import { getSiteConfig } from "@/lib/site-config";
import { demoPage } from "@/content/demo";
import { DemoRequestForm } from "@/components/site/demo-request-form";

export const metadata: Metadata = {
  title: "Book a demo",
  description: "See Verity with our team: tell us who you are and the frameworks you answer to, and we reply by email to find a time.",
  alternates: { canonical: "/demo/" },
};

/** The form's footprint while it loads, so the page does not jump when it arrives. */
function FormPlaceholder() {
  return (
    <div className="min-h-[520px]" aria-hidden="true">
      <div className="h-7 w-44 rounded-md bg-muted" />
      <div className="mt-8 space-y-6">
        {[0, 1, 2].map((row) => (
          <div key={row}>
            <div className="h-4 w-24 rounded bg-muted" />
            <div className="mt-2 h-[46px] rounded-lg bg-subtle ring-1 ring-line" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function DemoPage() {
  const { demoEndpoint, trialUrl, privacyUrl } = getSiteConfig();
  return (
    <main id="main-content" className="bg-gradient-to-b from-[#E9EEF3] via-[#F3F6F9] to-white">
      {/* One column on a phone, in reading order: the ask, the form, then what happens next. Side by side from lg up. */}
      <div className="frame grid grid-cols-1 gap-x-16 gap-y-10 pb-16 pt-12 lg:grid-cols-[0.95fr_1.05fr] lg:grid-rows-[auto_1fr] lg:items-start lg:pb-24 lg:pt-16">
        <header className="lg:col-start-1 lg:row-start-1">
          <p className="eyebrow">{demoPage.eyebrow}</p>
          <h1 className="mt-5 font-serif text-display-lg font-normal">{demoPage.title}</h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-dim">{demoPage.lead}</p>
        </header>

        <div className="rounded-2xl border border-line bg-surface p-6 shadow-float sm:p-8 lg:col-start-2 lg:row-span-2 lg:row-start-1">
          <Suspense fallback={<FormPlaceholder />}>
            <DemoRequestForm endpoint={demoEndpoint} privacyUrl={privacyUrl} />
          </Suspense>
          <noscript>
            <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-[14px] text-amber-900">This form needs JavaScript. Turn it on for this site and reload the page.</p>
          </noscript>
        </div>

        <section aria-labelledby="demo-next-title" className="lg:col-start-1 lg:row-start-2">
          <h2 id="demo-next-title" className="eyebrow">{demoPage.stepsTitle}</h2>
          <ol className="mt-6 space-y-7">
            {demoPage.steps.map((step, index) => (
              <li key={step.title} className="relative flex gap-4 pb-0.5">
                {/* The rule joins each step to the next, so the order reads at a glance. */}
                {index < demoPage.steps.length - 1 && <span aria-hidden="true" className="absolute left-4 top-9 h-[calc(100%-0.25rem)] w-px bg-line-strong" />}
                <span aria-hidden="true" className="tabular relative z-[1] grid h-8 w-8 shrink-0 place-items-center rounded-full border border-line-strong bg-surface text-[13px] font-semibold text-ink">{index + 1}</span>
                <span>
                  <span className="block text-[16px] font-semibold text-ink">{step.title}</span>
                  <span className="mt-1 block max-w-md text-[15px] leading-relaxed text-dim">{step.text}</span>
                </span>
              </li>
            ))}
          </ol>
          <p className="mt-10 text-[14.5px] text-dim">
            Rather explore on your own? <a href={trialUrl} className="font-medium text-accent hover:text-accent-strong">Start a trial</a>.
          </p>
        </section>
      </div>
    </main>
  );
}
