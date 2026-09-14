import { Fragment } from "react";
import { cn } from "@/lib/cn";
import { Tooltip } from "@/components/ui";
import type { Band, ScaleLevel } from "../types";
import { BAND_TONE, bandFor } from "../tokens";

type Marker = { likelihood: number; impact: number; label: string };

/**
 * Likelihood (rows, highest at the top) by impact (columns, highest on the
 * right). Every cell carries its band's hue: a pale tint marks the zone, and a
 * cell holding risks fills solid with the count, so exposure reads at a glance.
 */
export function Heatmap({
  grid,
  likelihoodScale,
  impactScale,
  bands,
  onCell,
  markers = [],
  compact = false,
}: {
  /** counts[likelihood - 1][impact - 1] */
  grid?: number[][];
  likelihoodScale: ScaleLevel[];
  impactScale: ScaleLevel[];
  bands: Band[];
  onCell?: (likelihood: number, impact: number) => void;
  /** Positions to ring, such as a single risk's inherent and residual scores. */
  markers?: Marker[];
  compact?: boolean;
}) {
  const rows = [...likelihoodScale].reverse();
  const cell = compact ? "h-9" : "h-12";
  return (
    <div className="flex gap-2">
      <div className="flex items-center">
        <span className="-rotate-180 text-caption font-semibold uppercase tracking-wide text-text-subtle [writing-mode:vertical-rl]">
          Likelihood
        </span>
      </div>
      <div className="min-w-0 flex-1">
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `${compact ? "1.25rem" : "5.5rem"} repeat(${impactScale.length}, minmax(0, 1fr))` }}
        >
          {rows.map((l) => (
            <Fragment key={l.level}>
              <div className="flex items-center justify-end pr-1.5 text-right">
                {compact ? (
                  <span className="tabular text-caption text-text-subtle">{l.level}</span>
                ) : (
                  <span className="truncate text-caption text-text-secondary" title={l.label}>
                    {l.label}
                  </span>
                )}
              </div>
              {impactScale.map((i) => {
                const count = grid?.[l.level - 1]?.[i.level - 1] ?? 0;
                const score = l.level * i.level;
                const band = bandFor(bands, score);
                const tone = band ? BAND_TONE[band.key] : BAND_TONE.low;
                const here = markers.filter((m) => m.likelihood === l.level && m.impact === i.level);
                const clickable = Boolean(onCell) && count > 0;
                const body = (
                  <button
                    type="button"
                    aria-disabled={!clickable}
                    onClick={() => {
                      if (clickable) onCell?.(l.level, i.level);
                    }}
                    aria-label={`${l.label} likelihood, ${i.label} impact: ${count} risks`}
                    className={cn(
                      "tabular relative flex w-full items-center justify-center rounded-md font-display font-bold transition-transform duration-150",
                      cell,
                      count > 0 || here.length ? tone.solid : tone.tint,
                      compact ? "text-caption" : "text-body-md",
                      clickable && "cursor-pointer hover:scale-[1.04] hover:shadow-sm",
                      !clickable && "cursor-default",
                    )}
                  >
                    {here.length ? (
                      <span className="flex gap-0.5">
                        {here.map((m) => (
                          <span
                            key={m.label}
                            className="grid size-5 place-items-center rounded-full bg-white text-[10px] font-extrabold text-text-primary"
                          >
                            {m.label}
                          </span>
                        ))}
                      </span>
                    ) : count > 0 ? (
                      count
                    ) : grid ? null : (
                      <span className={cn("text-caption font-semibold opacity-80", tone.text)}>{score}</span>
                    )}
                  </button>
                );
                return (
                  <Tooltip
                    key={i.level}
                    content={`${l.label} × ${i.label} · score ${score}${band ? ` · ${band.label}` : ""}${grid ? ` · ${count} ${count === 1 ? "risk" : "risks"}` : ""}`}
                  >
                    {body}
                  </Tooltip>
                );
              })}
            </Fragment>
          ))}
          <div />
          {impactScale.map((i) => (
            <div key={i.level} className="truncate pt-1 text-center text-caption text-text-secondary" title={i.label}>
              {compact ? i.level : i.label}
            </div>
          ))}
        </div>
        <p className="mt-1 text-center text-caption font-semibold uppercase tracking-wide text-text-subtle">Impact</p>
      </div>
    </div>
  );
}

/** The band legend under a heatmap. */
export function BandLegend({ bands, counts }: { bands: Band[]; counts?: Record<string, number> }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {bands.map((b) => (
        <span key={b.key} className="inline-flex items-center gap-1.5 text-caption text-text-secondary">
          <span className={cn("h-2.5 w-4 rounded-2xs", BAND_TONE[b.key].dot)} />
          {b.label}
          {counts ? <span className="tabular font-semibold text-text-primary">{counts[b.key] ?? 0}</span> : null}
        </span>
      ))}
    </div>
  );
}
