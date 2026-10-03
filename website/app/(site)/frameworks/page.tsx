import type { Metadata } from "next";
import { Suspense } from "react";
import { categoryNames, frameworks, regions } from "@/content/frameworks";
import { PageHero, FaqSection, FinalCta } from "@/components/sections/common";
import { FrameworkLibrary } from "@/components/sections/framework-library";
import { ControlMapping } from "@/components/visuals/control-mapping";
import { StatusBadge } from "@/components/ui/status-badge";

export const metadata: Metadata = {
  title: "Framework library",
  description: "SOC 2 today; ISO 27001, PCI DSS, NIST, HIPAA, GDPR and regional frameworks for Pakistan, the UAE, Australia and the US coming to the same control set.",
  alternates: { canonical: "/frameworks/" },
};

const faqs = [
  { q: "What does “coming soon” mean for a framework?", a: "The library is on our roadmap but not in the product yet. Until it arrives you can add your own controls for that framework, link evidence to them and track their status, then map them to the library when it ships." },
  { q: "Will we have to redo our work when a new library arrives?", a: "No. Libraries map to one shared control set. A control you already operate, and the evidence behind it, counts toward every framework that asks for it." },
  { q: "Does Verity certify us against these frameworks?", a: "No. Certifications and attestation reports are issued by accredited certification bodies and independent auditors. Verity organises the controls, evidence and decisions they review." },
  { q: "Our regulator is not listed. Can you add it?", a: "Tell us which framework you answer to. We prioritise the libraries our customers need, and the platform is built so a new framework is new content rather than new software." },
];

export default function FrameworksPage() {
  const live = frameworks.filter((item) => item.status === "live").length;
  return (
    <main id="main-content">
      <PageHero
        eyebrow="Framework library"
        title="Every framework you answer to, on one set of controls."
        lead={<p>Map a control once and let it count everywhere it applies. SOC 2 ships today; libraries for international standards and the regulators in Pakistan, the UAE, Australia, the United States and Europe are on the way.</p>}
        visual={<ControlMapping />}
      >
        <p className="mt-6 flex flex-wrap items-center gap-2 text-[14px] text-dim">
          <StatusBadge status="live" hideLive={false} /> SOC 2 available now
          <span className="mx-1 text-faint">·</span>
          <StatusBadge status="soon" /> {frameworks.length - live} more coming soon
        </p>
      </PageHero>
      <section aria-label="Frameworks" className="border-t border-line">
        <div className="frame py-12 lg:py-16">
          <Suspense fallback={null}>
            <FrameworkLibrary frameworks={frameworks} regions={regions} categories={categoryNames} />
          </Suspense>
          <p className="mt-10 max-w-3xl text-[13px] leading-relaxed text-faint">Names, issuers and versions were checked against official sources in October 2026 and are for orientation only. Regulations change; always confirm current requirements with the issuer or your advisers.</p>
        </div>
      </section>
      <FaqSection items={faqs} title="About the library." />
      <FinalCta title="Tell us what you answer to." lead="We will show you how Verity organises the work for your frameworks today, and what is coming next." source="frameworks-final" interest="compliance-automation" />
    </main>
  );
}
