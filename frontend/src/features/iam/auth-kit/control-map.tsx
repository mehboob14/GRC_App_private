import { useEffect, useState, type CSSProperties } from "react";
import { Icon, type IconName } from "@/components/ui";
import { cn } from "@/lib/cn";
import { prefersReducedMotion } from "@/features/iam/auth-motion";
import { FrameworkLogo } from "@/features/iam/components/framework-logo";

const FRAMEWORKS = [
  "SOC 2",
  "ISO 27001",
  "NIST CSF",
  "HIPAA",
  "PCI DSS",
  "GDPR",
] as const;

// Real controls from Verity's library, with the clause each satisfies in every
// framework (SOC 2 matches the library's own mapping; ISO 27001:2022 Annex A,
// NIST CSF 2.0 categories, HIPAA Security Rule, PCI DSS v4.0, GDPR articles).
const CONTROLS: { name: string; icon: IconName; refs: string[] }[] = [
  {
    name: "Periodic user access reviews",
    icon: "users",
    refs: ["CC6.3", "A.5.18", "PR.AA", "164.308(a)(4)", "7.2.4", "Art. 32"],
  },
  {
    name: "Encryption at rest",
    icon: "lock",
    refs: ["CC6.1", "A.8.24", "PR.DS", "164.312(a)(2)(iv)", "3.5.1", "Art. 32"],
  },
  {
    name: "Incident response plan",
    icon: "lightning",
    refs: ["CC7.4", "A.5.24", "RS.MA", "164.308(a)(6)", "12.10.1", "Art. 33"],
  },
  {
    name: "Vendor security due diligence",
    icon: "vendor",
    refs: ["CC9.2", "A.5.19", "GV.SC", "164.308(b)(1)", "12.8", "Art. 28"],
  },
];

const CYCLE_MS = 5600;
const ROW = 40;
const GAP = 7;
const HEIGHT = FRAMEWORKS.length * ROW + (FRAMEWORKS.length - 1) * GAP;
const LINK_W = 64;

/**
 * The idea of the product in one moving picture: one control, proven once,
 * lights up the matching clause in six frameworks. Cycles through four real
 * controls; hovering or focusing pauses it, the dots pick one, and reduced
 * motion shows each mapping complete and still.
 */
export function ControlMap() {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const still = prefersReducedMotion();
  const control = CONTROLS[index];

  useEffect(() => {
    if (paused || still) return;
    const timer = window.setTimeout(
      () => setIndex((i) => (i + 1) % CONTROLS.length),
      CYCLE_MS,
    );
    return () => window.clearTimeout(timer);
  }, [index, paused, still]);

  return (
    <figure
      className="cm w-full"
      data-paused={paused || undefined}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div
        key={index}
        className="grid items-center"
        style={{
          gridTemplateColumns: `minmax(0, 0.9fr) ${LINK_W}px minmax(0, 1.1fr)`,
          height: HEIGHT,
        }}
      >
        <div className="cm-control relative rounded-2xl border border-white bg-surface-primary p-4 shadow-3">
          <span className="grid size-10 place-items-center rounded-xl bg-action-accent text-white shadow-2">
            <Icon name={control.icon} className="size-5" />
          </span>
          <p className="mt-3 text-overline uppercase text-text-subtle">
            Control
          </p>
          <p className="cm-title mt-0.5 font-display text-heading-sm text-text-primary">
            {control.name}
          </p>
          <div className="mt-3 flex items-center gap-2 border-t border-border pt-3">
            <span className="cm-live relative grid size-2.5 place-items-center">
              <span className="size-2.5 rounded-full bg-status-success-base" />
            </span>
            <span className="text-label-sm text-text-secondary">Passing</span>
            <span className="cm-tally ml-auto text-label-sm tabular-nums text-text-primary">
              <span className="cm-count" aria-hidden />
              <span className="sr-only">6</span> frameworks
            </span>
          </div>
        </div>

        <svg
          width={LINK_W}
          height={HEIGHT}
          viewBox={`0 0 ${LINK_W} ${HEIGHT}`}
          className="overflow-visible"
          aria-hidden
        >
          {FRAMEWORKS.map((fw, i) => {
            const y = i * (ROW + GAP) + ROW / 2;
            const mid = HEIGHT / 2;
            const d = `M0 ${mid} C${LINK_W * 0.55} ${mid} ${LINK_W * 0.45} ${y} ${LINK_W} ${y}`;
            return (
              <g key={fw} style={{ "--i": i } as CSSProperties}>
                <path d={d} className="cm-track" />
                <path d={d} pathLength={1} className="cm-line" />
                {still ? null : (
                  <circle r={2.4} className="cm-packet">
                    <animateMotion
                      dur="1.8s"
                      begin={`${0.9 + i * 0.12}s`}
                      repeatCount="indefinite"
                      path={d}
                    />
                  </circle>
                )}
              </g>
            );
          })}
        </svg>

        <ul className="flex flex-col" style={{ gap: GAP }}>
          {FRAMEWORKS.map((fw, i) => (
            <li
              key={fw}
              className="cm-node flex items-center gap-2.5 rounded-xl border border-white bg-surface-primary/90 pl-2 pr-2.5 shadow-1"
              style={{ height: ROW, "--i": i } as CSSProperties}
            >
              <span className="grid size-7 shrink-0 place-items-center overflow-hidden rounded-lg bg-surface-primary ring-1 ring-border">
                <FrameworkLogo name={fw} size={20} eager />
              </span>
              <span className="min-w-0 flex-1 truncate text-label-sm text-text-primary">
                {fw}
              </span>
              <span className="cm-ref whitespace-nowrap rounded-md bg-action-accent-tint px-1.5 py-0.5 text-caption font-semibold tabular-nums text-action-primary">
                {control.refs[i]}
              </span>
              <span className="cm-check grid size-4 shrink-0 place-items-center rounded-full bg-status-success-base text-white">
                <Icon name="check" className="size-2.5" />
              </span>
            </li>
          ))}
        </ul>
      </div>

      <figcaption className="mt-4 flex items-center gap-1.5">
        <span className="sr-only">Example controls</span>
        {CONTROLS.map((c, i) => (
          <button
            key={c.name}
            type="button"
            aria-pressed={i === index}
            aria-label={`Show ${c.name}`}
            onClick={() => setIndex(i)}
            className={cn(
              "relative h-1.5 overflow-hidden rounded-full bg-action-accent/20 transition-[width,background-color] duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
              i === index ? "w-8" : "w-1.5 hover:bg-action-accent/40",
            )}
          >
            {i === index ? (
              // Remounts on every control and every pause, so the bar and the timer restart together.
              <span
                key={`${index}${paused}`}
                className="cm-dot-fill absolute inset-y-0 left-0 rounded-full bg-action-accent"
                style={{ animationDuration: `${CYCLE_MS}ms` }}
              />
            ) : null}
          </button>
        ))}
      </figcaption>
    </figure>
  );
}
