import type { ReactNode } from "react";
import Link from "next/link";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";
import { ArrowLink } from "@/components/ui/button-link";
import { StatusBadge } from "@/components/ui/status-badge";
import type { Capability } from "@/content/catalog";

export interface Feature {
  icon: IconName;
  title: string;
  text: string;
}

/** Hairline-separated icon rows, as under each section on the reference site. */
export function FeatureList({ features, className }: { features: Feature[]; className?: string }) {
  return (
    <ul className={cn("hairline-list border-y border-line", className)}>
      {features.map((feature, index) => (
        <li key={feature.title} data-reveal style={{ ["--reveal-delay" as string]: `${index * 90}ms` }} className="flex gap-4 py-5">
          <Icon name={feature.icon} size={21} className="mt-0.5 shrink-0 text-dim" />
          <div>
            <h3 className="text-[16.5px] font-semibold text-ink">{feature.title}</h3>
            <p className="mt-1 text-[15.5px] leading-relaxed text-dim">{feature.text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function CapabilityChips({ items, className }: { items: Capability[]; className?: string }) {
  return (
    <ul className={cn("flex flex-wrap gap-2", className)} aria-label="Capabilities">
      {items.map((item) => (
        <li key={item.name}>
          {item.href ? (
            <Link href={item.href} className="chip">{item.name}<StatusBadge status={item.status} size="xs" /></Link>
          ) : (
            <span className="chip">{item.name}<StatusBadge status={item.status} size="xs" /></span>
          )}
        </li>
      ))}
    </ul>
  );
}

/** The alternating product section: copy column and a product composition. */
export function Pillar({ id, eyebrow, title, titleAddon, lead, link, features, chips, visual, reverse = false, className }: { id: string; eyebrow: string; title: string; titleAddon?: ReactNode; lead: string; link?: { href: string; label: string }; features: Feature[]; chips?: Capability[]; visual: ReactNode; reverse?: boolean; className?: string }) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className={cn("border-t border-line", className)}>
      <div className="frame-ruled">
        <div className="frame grid grid-cols-1 items-center gap-14 py-20 lg:grid-cols-2 lg:gap-20 lg:py-28">
          <div className={cn("min-w-0", reverse && "lg:order-2")}>
            <p className="eyebrow" data-reveal>{eyebrow}</p>
            <h2 id={`${id}-title`} className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 font-serif text-display-lg font-normal" data-reveal>
              {title}
              {titleAddon}
            </h2>
            <p className="mt-5 max-w-xl text-[17px] leading-relaxed text-dim sm:text-lg" data-reveal>{lead}</p>
            {link && <div className="mt-5" data-reveal><ArrowLink href={link.href}>{link.label}</ArrowLink></div>}
            <FeatureList features={features} className="mt-10" />
            {chips && <CapabilityChips items={chips} className="mt-8" />}
          </div>
          <div className={cn("min-w-0", reverse && "lg:order-1")}>{visual}</div>
        </div>
      </div>
    </section>
  );
}

export function SectionShell({ id, labelledBy, children, className, tone = "plain" }: { id?: string; labelledBy?: string; children: ReactNode; className?: string; tone?: "plain" | "subtle" }) {
  return (
    <section id={id} aria-labelledby={labelledBy} className={cn("border-t border-line", tone === "subtle" && "bg-subtle", className)}>
      <div className="frame-ruled">
        <div className="frame py-20 lg:py-28">{children}</div>
      </div>
    </section>
  );
}

export function StatusLegend({ className }: { className?: string }) {
  return (
    <p className={cn("flex flex-wrap items-center gap-2 text-[13px] text-dim", className)}>
      <Icon name="info" size={15} />
      Everything without a badge is live today. Items marked <StatusBadge status="soon" size="xs" /> are on our roadmap.
    </p>
  );
}
