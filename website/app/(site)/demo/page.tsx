import type { Metadata } from "next";
import { Suspense } from "react";
import { getSiteConfig } from "@/lib/site-config";
import { DemoPageForm } from "@/components/site/demo-page-form";
import { Icon, type IconName } from "@/components/ui/icon";

export const metadata: Metadata = {
  title: "Book a demo",
  description: "See Verity with our team: tell us the frameworks you answer to and the work that slows you down.",
  alternates: { canonical: "/demo/" },
};

const expect: { icon: IconName; title: string; text: string }[] = [
  { icon: "chat", title: "A conversation first", text: "We ask what you answer to and what slows your team down, then show the parts of Verity that matter to you." },
  { icon: "desktop", title: "The real product", text: "A walkthrough of the live platform with demonstration data, not slides." },
  { icon: "map", title: "Honest about the roadmap", text: "We show what is live today and tell you plainly what is coming soon." },
];

export default function DemoPage() {
  const { demoEndpoint, trialUrl } = getSiteConfig();
  return (
    <main id="main-content" className="bg-gradient-to-b from-[#E9EEF3] via-[#F3F6F9] to-white">
      <div className="frame grid grid-cols-1 gap-12 py-14 lg:grid-cols-[0.9fr_1.1fr] lg:gap-16 lg:py-20">
        <div>
          <p className="eyebrow">Book a demo</p>
          <h1 className="mt-5 font-serif text-display-lg font-normal">See Verity with our team.</h1>
          <p className="mt-5 text-lg leading-relaxed text-dim">Tell us the frameworks you answer to and where the work gets stuck. We will reply to arrange a time.</p>
          <ul className="mt-10 space-y-6">
            {expect.map((item) => (
              <li key={item.title} className="flex gap-4">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-line bg-surface text-ink"><Icon name={item.icon} size={20} /></span>
                <span>
                  <span className="block text-[16px] font-semibold text-ink">{item.title}</span>
                  <span className="mt-1 block text-[15px] leading-relaxed text-dim">{item.text}</span>
                </span>
              </li>
            ))}
          </ul>
          <p className="mt-10 text-[14.5px] text-dim">Rather explore on your own? <a href={trialUrl} className="font-medium text-accent hover:text-accent-strong">Start a trial</a>.</p>
        </div>
        <div className="rounded-2xl border border-line bg-surface p-6 shadow-float sm:p-8">
          <Suspense fallback={null}>
            <DemoPageForm endpoint={demoEndpoint} />
          </Suspense>
        </div>
      </div>
    </main>
  );
}
