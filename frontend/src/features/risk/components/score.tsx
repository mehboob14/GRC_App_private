import { cn } from "@/lib/cn";
import { Tooltip } from "@/components/ui";
import type { Band, BandKey, ScaleLevel } from "../types";
import { BAND_TONE, bandFor } from "../tokens";

/** Where a level sits on its axis, as a severity key, so a scale reads as a ramp. */
function rampKey(level: number, levels: number): BandKey {
  const f = level / levels;
  if (f <= 0.34) return "low";
  if (f <= 0.6) return "medium";
  if (f <= 0.8) return "high";
  return "critical";
}

/** A score in its band colour. Unscored says so in words. */
export function ScoreChip({
  score,
  bands,
  size = "md",
  className,
}: {
  score: number | null | undefined;
  bands: Band[];
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const band = bandFor(bands, score);
  if (score === null || score === undefined || !band) {
    return <span className={cn("text-caption text-text-subtle", className)}>Not scored</span>;
  }
  return (
    <Tooltip content={`${band.label} · score ${score}`}>
      <span
        className={cn(
          "tabular inline-flex items-center justify-center rounded-md font-display font-bold",
          BAND_TONE[band.key].solid,
          size === "sm" && "h-6 min-w-6 px-1.5 text-caption",
          size === "md" && "h-7 min-w-7 px-2 text-body-sm",
          size === "lg" && "h-11 min-w-11 px-2.5 text-title-md",
          className,
        )}
      >
        {score}
      </span>
    </Tooltip>
  );
}

/** Score chip plus the band word, for headers and cards. */
export function BandPill({ score, bands }: { score: number | null | undefined; bands: Band[] }) {
  const band = bandFor(bands, score);
  if (!band || score === null || score === undefined) {
    return <span className="text-caption text-text-subtle">Not scored</span>;
  }
  return (
    <span className="inline-flex items-center gap-1.5">
      <ScoreChip score={score} bands={bands} size="sm" />
      <span className={cn("text-label-sm", BAND_TONE[band.key].text)}>{band.label}</span>
    </span>
  );
}

/**
 * One axis as a row of solid level buttons. The selected level fills with its
 * place on the ramp; the level's name and meaning sit under the row.
 */
export function ScaleInput({
  label,
  scale,
  value,
  onChange,
  disabled,
}: {
  label: string;
  scale: ScaleLevel[];
  value: number | null;
  onChange: (value: number | null) => void;
  disabled?: boolean;
}) {
  const selected = scale.find((s) => s.level === value);
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-label-sm text-text-secondary">{label}</span>
        <span className="truncate text-caption text-text-subtle">{selected ? selected.label : "Not set"}</span>
      </div>
      <div role="radiogroup" aria-label={label} className="grid gap-1" style={{ gridTemplateColumns: `repeat(${scale.length}, minmax(0, 1fr))` }}>
        {scale.map((s) => {
          const active = s.level === value;
          return (
            <Tooltip key={s.level} content={s.description ? `${s.label}: ${s.description}` : s.label}>
              <button
                type="button"
                role="radio"
                aria-checked={active}
                aria-label={`${label} ${s.level} ${s.label}`}
                disabled={disabled}
                onClick={() => onChange(active ? null : s.level)}
                className={cn(
                  "tabular h-9 rounded-md text-body-sm font-semibold transition-colors duration-150",
                  "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-action-accent",
                  active
                    ? BAND_TONE[rampKey(s.level, scale.length)].solid
                    : "bg-surface-sunken text-text-secondary hover:bg-surface-hover hover:text-text-primary",
                  disabled && "cursor-not-allowed opacity-60",
                )}
              >
                {s.level}
              </button>
            </Tooltip>
          );
        })}
      </div>
    </div>
  );
}

/** Likelihood and impact for one assessment, with the live score beside them. */
export function ScorePairInput({
  title,
  likelihoodScale,
  impactScale,
  bands,
  likelihood,
  impact,
  onChange,
}: {
  title: string;
  likelihoodScale: ScaleLevel[];
  impactScale: ScaleLevel[];
  bands: Band[];
  likelihood: number | null;
  impact: number | null;
  onChange: (likelihood: number | null, impact: number | null) => void;
}) {
  const score = likelihood && impact ? likelihood * impact : null;
  const band = bandFor(bands, score);
  return (
    <div className="rounded-lg border border-border bg-surface-primary p-3.5">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-label-md text-text-primary">{title}</p>
        <div className="flex items-center gap-2">
          {band ? <span className={cn("text-label-sm", BAND_TONE[band.key].text)}>{band.label}</span> : null}
          <ScoreChip score={score} bands={bands} />
        </div>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <ScaleInput
          label="Likelihood"
          scale={likelihoodScale}
          value={likelihood}
          onChange={(v) => onChange(v, impact)}
        />
        <ScaleInput label="Impact" scale={impactScale} value={impact} onChange={(v) => onChange(likelihood, v)} />
      </div>
    </div>
  );
}
