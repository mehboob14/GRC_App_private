"use client";

import { Children, useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

/* ----------------------------------------------------------------- Tabs */

export function Tabs({ labels, children }: { labels: string[]; children: ReactNode }) {
  const panels = Children.toArray(children);
  const [active, setActive] = useState(0);
  const id = useId();
  const onKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = event.key === "ArrowRight" ? 1 : event.key === "ArrowLeft" ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + labels.length) % labels.length;
    setActive(next);
    document.getElementById(`${id}-tab-${next}`)?.focus();
  };
  return (
    <div className="my-6 overflow-hidden rounded-xl border border-line">
      <div role="tablist" className="scrollbar-none flex gap-1 overflow-x-auto border-b border-line bg-subtle px-2 pt-2">
        {labels.map((label, index) => (
          <button
            key={label}
            id={`${id}-tab-${index}`}
            role="tab"
            type="button"
            aria-selected={active === index}
            aria-controls={`${id}-panel-${index}`}
            tabIndex={active === index ? 0 : -1}
            onClick={() => setActive(index)}
            onKeyDown={(event) => onKey(event, index)}
            className={cn("-mb-px whitespace-nowrap rounded-t-lg border border-b-0 px-3.5 py-2 text-[14px] font-medium transition-colors", active === index ? "border-line bg-surface text-ink" : "border-transparent text-dim hover:text-ink")}
          >
            {label}
          </button>
        ))}
      </div>
      {panels.map((panel, index) => (
        <div key={index} id={`${id}-panel-${index}`} role="tabpanel" aria-labelledby={`${id}-tab-${index}`} hidden={active !== index} className="px-5 pt-5 [&>*:last-child]:mb-1">
          {panel}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------ Zoomable */

export function ZoomableImage({ src, darkSrc, alt, width, height }: { src: string; darkSrc?: string; alt: string; width: number; height: number }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const image = (className?: string) => (
    <>
      <img src={src} alt={alt} width={width} height={height} loading="lazy" decoding="async" className={cn(darkSrc && "docs-light-only", className)} />
      {darkSrc && <img src={darkSrc} alt={alt} width={width} height={height} loading="lazy" decoding="async" className={cn("docs-dark-only", className)} />}
    </>
  );
  return (
    <>
      <button ref={opener} type="button" onClick={() => dialog.current?.showModal()} className="group relative block w-full cursor-zoom-in text-left" aria-label={`Enlarge screenshot: ${alt}`}>
        {image()}
        <span className="pointer-events-none absolute bottom-3 right-3 inline-flex items-center gap-1.5 rounded-md bg-ink/80 px-2 py-1 text-[12px] font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
          <Icon name="search" size={13} />Enlarge
        </span>
      </button>
      <dialog ref={dialog} className="demo-dialog m-auto max-h-[96dvh] w-[min(1600px,96vw)] overflow-auto rounded-xl border border-line bg-surface p-0 shadow-menu backdrop:bg-black/70" onClick={(event) => { if (event.target === dialog.current) dialog.current?.close(); }} onClose={() => opener.current?.focus()} aria-label={alt}>
        <div className="sticky top-0 z-[1] flex items-center justify-between gap-4 border-b border-line bg-surface px-4 py-2.5">
          <p className="truncate text-[13.5px] text-dim">{alt}</p>
          <button type="button" onClick={() => dialog.current?.close()} className="grid h-8 w-8 place-items-center rounded-md text-dim hover:bg-muted hover:text-ink" aria-label="Close">
            <Icon name="x" size={16} weight="bold" />
          </button>
        </div>
        {image("block h-auto w-full")}
      </dialog>
    </>
  );
}

/* --------------------------------------------------------- Walkthrough */

export interface WalkthroughStep {
  title: string;
  body: string;
  /** Element key from the screenshot manifest, or explicit percentages. */
  box?: { x: number; y: number; w: number; h: number };
}

/**
 * A screenshot with numbered hotspots. Each step spotlights one element of
 * the screen; the reader moves with the buttons, the arrow keys, or by
 * choosing a hotspot.
 */
export function WalkthroughView({ src, alt, width, height, steps }: { src: string; alt: string; width: number; height: number; steps: WalkthroughStep[] }) {
  const [active, setActive] = useState(0);
  const root = useRef<HTMLDivElement>(null);
  const step = steps[active];

  const go = (index: number) => setActive((index + steps.length) % steps.length);
  const pct = (value: number, total: number) => `${(value / total) * 100}%`;

  return (
    <div ref={root} className="not-prose my-7 overflow-hidden rounded-xl border border-line bg-surface shadow-card" tabIndex={0} aria-roledescription="walkthrough" aria-label={`Walkthrough: ${alt}`} onKeyDown={(event) => {
      if (event.key === "ArrowRight") { event.preventDefault(); go(active + 1); }
      if (event.key === "ArrowLeft") { event.preventDefault(); go(active - 1); }
    }}>
      <div className="docs-shot-bar"><i /><i /><i /><span className="ms-2 truncate font-mono text-[11px] text-faint">Demonstration workspace</span></div>
      <div className="relative">
        <img src={src} alt={alt} width={width} height={height} loading="lazy" decoding="async" className="block h-auto w-full" />
        {step.box && (
          <span
            className="pointer-events-none absolute rounded-md ring-2 ring-sky-400 transition-all duration-500 ease-out"
            style={{ left: pct(step.box.x - 4, width), top: pct(step.box.y - 4, height), width: pct(step.box.w + 8, width), height: pct(step.box.h + 8, height), boxShadow: "0 0 0 9999px rgb(11 15 23 / 0.38)" }}
            aria-hidden="true"
          />
        )}
        {steps.map((item, index) => item.box && (
          <button
            key={index}
            type="button"
            onClick={() => setActive(index)}
            className={cn("absolute grid h-7 w-7 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full font-mono text-[12px] font-semibold shadow-float transition-transform", index === active ? "scale-110 bg-sky-500 text-white" : "bg-white text-ink ring-1 ring-line-strong hover:scale-105")}
            style={{ left: pct(item.box.x + item.box.w, width), top: pct(item.box.y, height) }}
            aria-label={`Step ${index + 1}: ${item.title}`}
            aria-current={index === active ? "step" : undefined}
          >
            {index === active && <span className="pulse-ring absolute inset-0 rounded-full bg-sky-400" aria-hidden="true" />}
            <span className="relative">{index + 1}</span>
          </button>
        ))}
      </div>
      <div className="flex flex-col gap-3 border-t border-line p-4 sm:flex-row sm:items-center sm:justify-between">
        <div aria-live="polite" className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-faint">Step {active + 1} of {steps.length}</p>
          <p className="mt-1 text-[15px] font-semibold text-ink">{step.title}</p>
          <p className="mt-0.5 text-[14.5px] leading-relaxed text-dim">{step.body}</p>
        </div>
        <div className="flex shrink-0 gap-2">
          <button type="button" onClick={() => go(active - 1)} className="btn btn-outline btn-sm" aria-label="Previous step"><Icon name="arrow-right" size={15} className="rotate-180" /></button>
          <button type="button" onClick={() => go(active + 1)} className="btn btn-dark btn-sm">{active === steps.length - 1 ? "Start again" : "Next"}<Icon name="arrow-right" size={15} /></button>
        </div>
      </div>
    </div>
  );
}
