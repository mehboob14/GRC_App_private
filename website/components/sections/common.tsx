import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { getSiteConfig } from "@/lib/site-config";
import { Icon } from "@/components/ui/icon";
import { DemoButton } from "@/components/site/demo-button";
import { IsometricHero } from "@/components/visuals/isometric-hero";

/** Primary call-to-action pair: See a demo (outline) and Start trial (dark), as on the reference. */
export function CtaPair({ source, interest, className, size }: { source: string; interest?: string; className?: string; size?: "lg" }) {
  const { trialUrl } = getSiteConfig();
  return (
    <div className={cn("flex flex-wrap items-center gap-3", className)}>
      <DemoButton variant="outline" className={cn(size === "lg" && "btn-lg")} source={source} interest={interest}>See a demo</DemoButton>
      <a href={trialUrl} className={cn("btn btn-dark", size === "lg" && "btn-lg")}>
        Start trial
        <Icon name="arrow-right" size={16} weight="bold" className="btn-arrow" />
      </a>
    </div>
  );
}

export function FaqList({ items, className }: { items: { q: string; a: ReactNode }[]; className?: string }) {
  return (
    <div className={cn("divide-y divide-line border-y border-line", className)}>
      {items.map((item) => (
        <details key={item.q} className="group py-1">
          <summary className="flex items-center justify-between gap-6 py-4 text-left text-[17px] font-medium text-ink">
            {item.q}
            <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-line text-dim transition-transform duration-200 group-open:rotate-45" aria-hidden="true">
              <Icon name="x" size={13} weight="bold" className="rotate-45" />
            </span>
          </summary>
          <div className="pb-5 pr-12 text-[15.5px] leading-relaxed text-dim">{item.a}</div>
        </details>
      ))}
    </div>
  );
}

export function FaqSection({ items, title = "Questions, answered.", lead, id = "faq" }: { items: { q: string; a: ReactNode }[]; title?: string; lead?: string; id?: string }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="border-t border-line">
      <div className="frame-ruled">
        <div className="frame grid grid-cols-1 gap-10 py-20 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20 lg:py-28">
          <div>
            <p className="eyebrow">Common questions</p>
            <h2 id={`${id}-title`} className="mt-4 font-serif text-display-md">{title}</h2>
            {lead && <p className="mt-4 text-[16.5px] leading-relaxed text-dim">{lead}</p>}
          </div>
          <FaqList items={items} />
        </div>
      </div>
    </section>
  );
}

export function FinalCta({ title, lead, source, interest }: { title: string; lead: string; source: string; interest?: string }) {
  return (
    <section aria-labelledby="final-cta-title" className="relative overflow-hidden border-t border-line bg-gradient-to-b from-white via-[#F2F5F8] to-[#E8EDF2]">
      <div className="frame relative grid grid-cols-1 items-center gap-10 py-20 lg:grid-cols-[1.2fr_0.8fr] lg:py-24">
        <div>
          <h2 id="final-cta-title" className="max-w-[18ch] font-serif text-display-lg" data-reveal>{title}</h2>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-dim" data-reveal>{lead}</p>
          <CtaPair source={source} interest={interest} className="mt-8" size="lg" />
        </div>
        <div className="relative hidden lg:block" aria-hidden="true">
          <IsometricHero className="w-full opacity-90" />
        </div>
      </div>
    </section>
  );
}

/** Page hero for inner pages: breadcrumb, eyebrow, serif title, lead, actions and an optional visual. */
export function PageHero({ eyebrow, title, lead, children, visual, breadcrumb, badge, align = "split" }: { eyebrow: string; title: ReactNode; lead: ReactNode; children?: ReactNode; visual?: ReactNode; breadcrumb?: ReactNode; badge?: ReactNode; align?: "split" | "stack" }) {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-[#E9EEF3] via-[#F3F6F9] to-white">
      <div className={cn("frame grid items-center gap-12 pb-16 pt-12 lg:pb-24 lg:pt-16", Boolean(visual) && align === "split" && "lg:grid-cols-[1.02fr_1fr] lg:gap-16")}>
        <div className="min-w-0">
          {breadcrumb}
          <div className="flex flex-wrap items-center gap-3">
            <p className="eyebrow">{eyebrow}</p>
            {badge}
          </div>
          <h1 className="mt-5 max-w-[20ch] font-serif text-display-xl font-normal">{title}</h1>
          <div className="mt-6 max-w-[38rem] text-lg leading-relaxed text-dim sm:text-[19px]">{lead}</div>
          {children}
        </div>
        {visual && <div className="min-w-0">{visual}</div>}
      </div>
    </section>
  );
}
