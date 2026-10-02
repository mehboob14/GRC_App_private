"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";
import { Pill, SampleNote, type Family } from "./ui-kit";

/**
 * The "four-hop trace" the platform is built around: a vulnerability on an
 * asset raises a risk, the risk is treated by a control, and the control is
 * proven by a policy and evidence. Each hop is selectable; the selection
 * advances on its own until the visitor interacts or prefers reduced motion.
 */

interface Hop {
  key: string;
  type: string;
  icon: IconName;
  record: string;
  meta: string;
  status: string;
  tone: Family;
  why: string;
}

const hops: Hop[] = [
  { key: "vulnerability", type: "Vulnerability", icon: "bug", record: "Outdated TLS library", meta: "P1 · known exploited", status: "In progress", tone: "progress", why: "A scanner import raised this finding on a production asset, with a remediation window set by its priority." },
  { key: "asset", type: "Asset", icon: "server", record: "Customer portal", meta: "Application · critical", status: "Active", tone: "success", why: "The asset carries its owner, criticality and dependencies, so the finding inherits why it matters." },
  { key: "risk", type: "Risk", icon: "scales", record: "Customer data exposure", meta: "Residual: high", status: "In treatment", tone: "progress", why: "The risk register records the exposure, the treatment plan and who accepted what, and when." },
  { key: "control", type: "Control", icon: "shield", record: "NS-02 · Encryption in transit", meta: "SOC 2 · CC6.7", status: "In progress", tone: "progress", why: "The control that treats the risk shows its status, owner and the criteria it answers." },
  { key: "proof", type: "Policy and evidence", icon: "file", record: "Cryptography standard v2", meta: "+ TLS configuration export", status: "Approved", tone: "success", why: "Policy and evidence prove the control. Every hop above is in the audit log, with before and after." },
];

export function TraceGraph() {
  const [active, setActive] = useState(0);
  const [auto, setAuto] = useState(true);
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!auto) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let visible = false;
    const io = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; }, { threshold: 0.4 });
    if (root.current) io.observe(root.current);
    const timer = window.setInterval(() => {
      if (visible) setActive((current) => (current + 1) % hops.length);
    }, 2600);
    return () => { window.clearInterval(timer); io.disconnect(); };
  }, [auto]);

  const choose = (index: number) => {
    setAuto(false);
    setActive(index);
  };

  return (
    <div ref={root} className="w-full">
      <div role="tablist" aria-label="Linked records" className="relative grid gap-3 lg:grid-cols-5 lg:gap-4">
        <div className="pointer-events-none absolute inset-x-[10%] top-[52px] hidden h-px lg:block" aria-hidden="true">
          <svg width="100%" height="2" preserveAspectRatio="none" className="overflow-visible"><line x1="0" y1="1" x2="100%" y2="1" stroke="#BAE6FD" strokeWidth="2" strokeDasharray="6 6" className="flow-dash" /></svg>
        </div>
        {hops.map((hop, index) => {
          const selected = index === active;
          const done = index < active;
          return (
            <button
              key={hop.key}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls="trace-panel"
              id={`trace-tab-${hop.key}`}
              onClick={() => choose(index)}
              onKeyDown={(event) => {
                if (event.key === "ArrowRight" || event.key === "ArrowDown") { event.preventDefault(); choose((index + 1) % hops.length); (event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=tab]")[(index + 1) % hops.length])?.focus(); }
                if (event.key === "ArrowLeft" || event.key === "ArrowUp") { event.preventDefault(); const prev = (index - 1 + hops.length) % hops.length; choose(prev); (event.currentTarget.parentElement?.querySelectorAll<HTMLButtonElement>("[role=tab]")[prev])?.focus(); }
              }}
              tabIndex={selected ? 0 : -1}
              className={cn(
                "relative z-[1] flex flex-col items-start rounded-xl border bg-white p-4 text-left transition-all duration-300",
                selected ? "border-sky-300 shadow-float ring-4 ring-sky-100" : done ? "border-sky-200 shadow-card" : "border-line shadow-card hover:border-line-strong",
              )}
            >
              <span className="flex w-full items-center justify-between">
                <span className={cn("grid h-9 w-9 place-items-center rounded-lg border transition-colors", selected ? "border-sky-300 bg-sky-50 text-sky-700" : "border-line text-ink")}>
                  <Icon name={hop.icon} size={19} />
                </span>
                <span className="font-mono text-[10.5px] text-faint">{String(index + 1).padStart(2, "0")}</span>
              </span>
              <span className="mt-3 font-mono text-[10.5px] uppercase tracking-[0.12em] text-dim">{hop.type}</span>
              <span className="mt-1 text-[14px] font-semibold leading-snug text-ink">{hop.record}</span>
              <span className="mt-0.5 text-[12px] text-dim">{hop.meta}</span>
              <span className="mt-3"><Pill tone={hop.tone}>{hop.status}</Pill></span>
            </button>
          );
        })}
      </div>
      <div id="trace-panel" role="tabpanel" aria-labelledby={`trace-tab-${hops[active].key}`} className="mt-5 flex flex-col gap-3 rounded-xl border border-line bg-subtle p-5 sm:flex-row sm:items-center sm:justify-between">
        <p key={active} className="max-w-3xl animate-fade-in text-[15px] leading-relaxed text-body"><span className="font-semibold text-ink">{hops[active].type}.</span> {hops[active].why}</p>
        <span className="flex shrink-0 items-center gap-1.5 font-mono text-[11px] text-dim"><Icon name="clock" size={14} />Recorded in the audit log</span>
      </div>
      <SampleNote className="mt-4">Sample records · select a step to follow the trace</SampleNote>
    </div>
  );
}
