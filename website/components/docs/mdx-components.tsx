import Link from "next/link";
import type { ComponentPropsWithoutRef, CSSProperties, ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon, isIconName } from "@/components/ui/icon";
import { StatusBadge } from "@/components/ui/status-badge";
import screens from "@/content/docs/screens.json";
import { Tabs, WalkthroughView, ZoomableImage, type WalkthroughStep } from "./mdx-client";

/**
 * Components available inside documentation MDX. Names must stay in step
 * with docComponentNames in lib/docs.ts (the build rejects unknown ones).
 */

type ScreenEntry = { width: number; height: number; title?: string; elements?: { key: string; label: string; x: number; y: number; w: number; h: number }[] };
const manifest = screens as Record<string, ScreenEntry>;

function screen(name: string): ScreenEntry {
  const entry = manifest[name];
  if (!entry) throw new Error(`[docs] screenshot "${name}" is not in content/docs/screens.json`);
  return entry;
}

const calloutStyle = {
  note: { icon: "info", label: "Note", box: "border-sky-200 bg-sky-50/70 [[data-docs-theme=dark]_&]:border-sky-900 [[data-docs-theme=dark]_&]:bg-sky-950/40", tint: "text-sky-700 [[data-docs-theme=dark]_&]:text-sky-300" },
  tip: { icon: "lightbulb", label: "Tip", box: "border-emerald-200 bg-emerald-50/70 [[data-docs-theme=dark]_&]:border-emerald-900 [[data-docs-theme=dark]_&]:bg-emerald-950/40", tint: "text-emerald-700 [[data-docs-theme=dark]_&]:text-emerald-300" },
  warning: { icon: "warning", label: "Before you click", box: "border-amber-200 bg-amber-50/80 [[data-docs-theme=dark]_&]:border-amber-900 [[data-docs-theme=dark]_&]:bg-amber-950/40", tint: "text-amber-700 [[data-docs-theme=dark]_&]:text-amber-300" },
  soon: { icon: "map", label: "Coming soon", box: "border-dashed border-indigo-300 bg-indigo-50/60 [[data-docs-theme=dark]_&]:border-indigo-800 [[data-docs-theme=dark]_&]:bg-indigo-950/40", tint: "text-indigo-700 [[data-docs-theme=dark]_&]:text-indigo-300" },
} as const;

export function Callout({ type = "note", title, children }: { type?: keyof typeof calloutStyle; title?: string; children: ReactNode }) {
  const style = calloutStyle[type] ?? calloutStyle.note;
  return (
    <aside className={cn("my-6 flex gap-3 rounded-xl border px-4 py-3.5", style.box)} aria-label={title ?? style.label}>
      <Icon name={style.icon} size={19} weight="fill" className={cn("mt-[3px] shrink-0", style.tint)} />
      <div className="min-w-0 text-[15px] leading-relaxed [&>*:last-child]:mb-0 [&_p]:mb-2">
        {title && <p className="!mb-1 font-semibold text-ink">{title}</p>}
        {children}
      </div>
    </aside>
  );
}

export function Steps({ children }: { children: ReactNode }) {
  return <ol data-animate className="docs-steps list-none !ps-0">{children}</ol>;
}

export function Step({ title, children }: { title: string; children: ReactNode }) {
  return (
    <li className="docs-step !ps-[46px]">
      <h4>{title}</h4>
      <div>{children}</div>
    </li>
  );
}

export function Screenshot({ name, alt, caption }: { name: string; alt: string; caption?: string }) {
  const entry = screen(name);
  const dark = manifest[`${name}.dark`] ? `/docs/screens/${name}.dark.webp` : undefined;
  return (
    <figure className="docs-shot">
      <div className="docs-shot-frame">
        <div className="docs-shot-bar" aria-hidden="true"><i /><i /><i /><span className="ms-2 truncate font-mono text-[11px] text-faint">Demonstration workspace</span></div>
        <ZoomableImage src={`/docs/screens/${name}.webp`} darkSrc={dark} alt={alt} width={entry.width} height={entry.height} />
      </div>
      {caption && <figcaption className="mt-2.5 text-center text-[13.5px] text-dim">{caption}</figcaption>}
    </figure>
  );
}

export function Walkthrough({ name, alt, steps }: { name: string; alt: string; steps: (Omit<WalkthroughStep, "box"> & { target?: string })[] }) {
  const entry = screen(name);
  const resolved: WalkthroughStep[] = steps.map((step) => {
    const element = step.target ? entry.elements?.find((candidate) => candidate.key === step.target) : undefined;
    if (step.target && !element) throw new Error(`[docs] walkthrough on "${name}" targets unknown element "${step.target}"`);
    return { title: step.title, body: step.body, box: element ? { x: element.x, y: element.y, w: element.w, h: element.h } : undefined };
  });
  return <WalkthroughView src={`/docs/screens/${name}.webp`} alt={alt} width={entry.width} height={entry.height} steps={resolved} />;
}

type Stage = string | { name: string; note?: string };

export function Lifecycle({ title, stages }: { title?: string; stages: Stage[] }) {
  const items = stages.map((stage) => (typeof stage === "string" ? { name: stage, note: undefined } : stage));
  const long = items.length > 6;
  return (
    <figure data-animate className="my-7 rounded-xl border border-line bg-subtle p-5" style={{ ["--lc-step" as string]: `${Math.max(60, 1300 / items.length)}ms` } as CSSProperties}>
      {title && <figcaption className="mb-5 text-[14px] font-semibold text-ink">{title}</figcaption>}
      {long ? (
        <ol className="grid list-none gap-2.5 !ps-0 sm:grid-cols-2 md:grid-cols-3">
          {items.map((item, index) => (
            <li key={item.name} className="docs-lifecycle-dot relative !m-0 flex gap-3 rounded-lg border border-line bg-surface !p-3" style={{ ["--i" as string]: index } as CSSProperties}>
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-sky-300 bg-sky-50 font-mono text-[11.5px] font-semibold text-sky-700 [[data-docs-theme=dark]_&]:bg-sky-950/60 [[data-docs-theme=dark]_&]:text-sky-300">{index + 1}</span>
              <span className="min-w-0 pt-0.5">
                <span className="block text-[14px] font-semibold leading-tight text-ink">{item.name}</span>
                {item.note && <span className="mt-1 block text-[13px] leading-snug text-dim">{item.note}</span>}
              </span>
            </li>
          ))}
        </ol>
      ) : (
        <>
          <ol className="relative hidden list-none gap-2 !ps-0 md:grid" style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}>
            <span className="docs-lifecycle-track" aria-hidden="true"><span className="docs-lifecycle-fill" /></span>
            {items.map((item, index) => (
              <li key={item.name} className="relative !m-0 flex flex-col items-center !p-0 text-center" style={{ ["--i" as string]: index } as CSSProperties}>
                <span className="docs-lifecycle-dot relative z-[1] grid h-8 w-8 place-items-center rounded-full border border-sky-300 bg-surface font-mono text-[11.5px] font-semibold text-sky-700 shadow-card [[data-docs-theme=dark]_&]:text-sky-300">{index + 1}</span>
                <span className="mt-2 text-[13px] font-semibold leading-tight text-ink">{item.name}</span>
                {item.note && <span className="mt-1 text-[12px] leading-snug text-dim">{item.note}</span>}
              </li>
            ))}
          </ol>
          <ol className="relative list-none space-y-3 !ps-0 md:hidden">
            {items.map((item, index) => (
              <li key={item.name} className="relative !m-0 flex gap-3 !p-0" style={{ ["--i" as string]: index } as CSSProperties}>
                <span className="docs-lifecycle-dot grid h-7 w-7 shrink-0 place-items-center rounded-full border border-sky-300 bg-surface font-mono text-[11px] font-semibold text-sky-700 [[data-docs-theme=dark]_&]:text-sky-300">{index + 1}</span>
                <span className="pt-0.5">
                  <span className="block text-[14px] font-semibold leading-tight text-ink">{item.name}</span>
                  {item.note && <span className="mt-0.5 block text-[13px] leading-snug text-dim">{item.note}</span>}
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
    </figure>
  );
}

export function Cards({ children }: { children: ReactNode }) {
  return <div className="my-6 grid gap-3 sm:grid-cols-2">{children}</div>;
}

export function Card({ title, href, icon, children }: { title: string; href: string; icon?: string; children?: ReactNode }) {
  return (
    <Link href={href} className="docs-card group flex gap-3.5 rounded-xl border border-line bg-surface p-4 no-underline transition hover:border-line-strong hover:shadow-card">
      {icon && isIconName(icon) && <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg border border-line text-ink group-hover:border-sky-300 group-hover:text-sky-700"><Icon name={icon} size={18} /></span>}
      <span className="min-w-0">
        <span className="flex items-center gap-1.5 text-[15px] font-semibold text-ink">{title}<Icon name="arrow-right" size={14} weight="bold" className="text-faint transition-transform group-hover:translate-x-0.5" /></span>
        {children && <span className="mt-0.5 block text-[14px] leading-snug text-dim">{children}</span>}
      </span>
    </Link>
  );
}

export function Status({ value }: { value: "live" | "preview" | "soon" }) {
  return <StatusBadge status={value} size="xs" hideLive={false} className="mx-0.5 align-[2px]" />;
}

export function Kbd({ children }: { children: ReactNode }) {
  return <kbd>{children}</kbd>;
}

function Anchor({ href = "", children, ...rest }: ComponentPropsWithoutRef<"a">) {
  if (href.startsWith("/") && !href.startsWith("//")) return <Link href={href} {...rest}>{children}</Link>;
  return <a href={href} {...rest}>{children}</a>;
}

function heading(Tag: "h2" | "h3") {
  return function Heading({ id, children, ...rest }: ComponentPropsWithoutRef<"h2">) {
    return (
      <Tag id={id} {...rest}>
        {children}
        {id && <a href={`#${id}`} className="heading-anchor" aria-label="Link to this section">#</a>}
      </Tag>
    );
  };
}

function Table(props: ComponentPropsWithoutRef<"table">) {
  return <div className="table-wrap" role="region" aria-label="Table" tabIndex={0}><table {...props} /></div>;
}

export const mdxComponents = { Callout, Steps, Step, Tabs, Tab: ({ children }: { children: ReactNode }) => <>{children}</>, Screenshot, Walkthrough, Lifecycle, Cards, Card, Status, Kbd, a: Anchor, h2: heading("h2"), h3: heading("h3"), table: Table };
