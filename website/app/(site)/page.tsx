import type { Metadata } from "next";
import { Pillar } from "@/components/sections/pillar";
import { FaqSection, FinalCta } from "@/components/sections/common";
import { DocsTeaser, FactStrip, FrameworksTeaser, HomeHero, HowItWorks, IndustriesGrid, IntegrationsGrid, Problem, SecurityGrid, TraceSection } from "@/components/sections/home";
import { StatusBadge } from "@/components/ui/status-badge";
import { ProofFlow } from "@/components/visuals/proof-flow";
import { VendorRegister } from "@/components/visuals/vendor-register";
import { EstateDashboard } from "@/components/visuals/estate-dashboard";
import { PolicyCampaign } from "@/components/visuals/policy-campaign";
import { AssistantDraft } from "@/components/visuals/assistant-draft";
import { ai, faqs, finalCta, pillars } from "@/content/home";

export const metadata: Metadata = { alternates: { canonical: "/" } };

const visuals = [<ProofFlow key="proof" />, <VendorRegister key="vendors" />, <EstateDashboard key="estate" />, <PolicyCampaign key="policies" />];

export default function HomePage() {
  return (
    <main id="main-content">
      <HomeHero />
      <FactStrip />
      <Problem />
      {pillars.map((pillar, index) => (
        <Pillar key={pillar.id} {...pillar} visual={visuals[index]} reverse={index % 2 === 1} />
      ))}
      <Pillar
        id={ai.id}
        eyebrow={ai.eyebrow}
        title={ai.title}
        titleAddon={<StatusBadge status="soon" />}
        lead={ai.lead}
        link={ai.link}
        features={ai.features}
        visual={<AssistantDraft />}
        className="bg-subtle"
      />
      <HowItWorks />
      <TraceSection />
      <FrameworksTeaser />
      <IndustriesGrid />
      <IntegrationsGrid />
      <SecurityGrid />
      <DocsTeaser />
      <FaqSection items={faqs} lead="What buyers and the people who will use Verity ask us most." />
      <FinalCta title={finalCta.title} lead={finalCta.lead} source="home-final" />
    </main>
  );
}
