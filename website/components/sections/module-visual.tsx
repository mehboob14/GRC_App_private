import { cn } from "@/lib/cn";
import screens from "@/content/docs/screens.json";
import type { SectionVisual } from "@/content/modules";
import { Icon } from "@/components/ui/icon";
import { Pill, SampleNote } from "@/components/visuals/ui-kit";
import { ProofFlow } from "@/components/visuals/proof-flow";
import { VendorRegister } from "@/components/visuals/vendor-register";
import { EstateDashboard } from "@/components/visuals/estate-dashboard";
import { PolicyCampaign } from "@/components/visuals/policy-campaign";
import { AssistantDraft } from "@/components/visuals/assistant-draft";
import { ControlMapping } from "@/components/visuals/control-mapping";

const compositions = {
  "proof-flow": ProofFlow,
  "vendor-register": VendorRegister,
  "estate-dashboard": EstateDashboard,
  "policy-campaign": PolicyCampaign,
  "assistant-draft": AssistantDraft,
  "control-mapping": ControlMapping,
} as const;

const manifest = screens as Record<string, { width: number; height: number }>;

/** Renders whichever visual a module section asks for: a framed product screenshot, a composition, or a concept card. */
export function ModuleVisual({ visual, priority = false, className }: { visual: SectionVisual; priority?: boolean; className?: string }) {
  if (visual.kind === "composition") {
    const Composition = compositions[visual.name];
    return <div className={className}><Composition /></div>;
  }
  if (visual.kind === "screenshot") {
    const size = manifest[visual.name] ?? { width: 1440, height: 900 };
    return (
      <figure className={cn("relative", className)} data-reveal="scale">
        <div className="overflow-hidden rounded-xl border border-line bg-surface shadow-float">
          <div className="flex h-8 items-center gap-1.5 border-b border-line bg-subtle px-3" aria-hidden="true">
            <i className="h-2.5 w-2.5 rounded-full bg-line-strong" /><i className="h-2.5 w-2.5 rounded-full bg-line-strong" /><i className="h-2.5 w-2.5 rounded-full bg-line-strong" />
            <span className="ms-2 truncate font-mono text-[10.5px] text-faint">Demonstration workspace</span>
          </div>
          <img src={`/docs/screens/${visual.name}.webp`} alt={visual.alt} width={size.width} height={size.height} loading={priority ? "eager" : "lazy"} decoding="async" className="block h-auto w-full" />
        </div>
        <SampleNote className="mt-3">Product screen · demonstration data</SampleNote>
      </figure>
    );
  }
  return (
    <figure data-animate className={cn("mx-auto w-full max-w-[560px]", className)}>
      <div className="seq overflow-hidden rounded-2xl border border-line bg-surface shadow-float">
        <div className="flex items-center justify-between gap-3 border-b border-line px-5 py-4">
          <span className="flex items-center gap-2.5 text-[15px] font-semibold text-ink"><span className="grid h-8 w-8 place-items-center rounded-md border border-line"><Icon name={visual.icon} size={17} /></span>{visual.title}</span>
        </div>
        <ul className="divide-y divide-line">
          {visual.rows.map((row, index) => (
            <li key={`${row.label}-${index}`} className="seq flex items-center justify-between gap-4 px-5 py-3.5" style={{ ["--i" as string]: index + 1, ["--step" as string]: "110ms" }}>
              <span className="min-w-0">
                <span className="block truncate text-[14px] font-medium text-ink">{row.label}</span>
                {row.meta && <span className="block truncate text-[12.5px] text-dim">{row.meta}</span>}
              </span>
              <Pill tone={row.tone}>{row.status}</Pill>
            </li>
          ))}
        </ul>
      </div>
      <SampleNote className="mt-4">{visual.note ?? "Concept · coming soon"}</SampleNote>
    </figure>
  );
}
