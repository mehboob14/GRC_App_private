import { Icon, StatusPill, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";
import type { StageRow } from "../types";
import { fmtDate, STAGE_STATUS_META } from "../tokens";

/**
 * The twelve stages as a vertical rail.
 *
 * Three things the rail has to say that a plain list cannot:
 *
 *  - **A gate is not a step.** The approval gate is fenced off with its own
 *    rule and marked with a diamond rather than a circle, so the eye reads it
 *    as a boundary the review has to be let through rather than one more box.
 *  - **A skipped stage is a decision, not an absence.** Skipped rows stay in
 *    place and carry the policy or the person that skipped them.
 *  - **Where the work is now, separately from what you are reading.** The
 *    current row carries the marker; the selected row carries the highlight.
 *    They are usually the same, and a reader is allowed to click back to a
 *    finished stage without the rail losing track of where the work sits.
 */
export function StageRail({
  stages,
  selectedId,
  currentId,
  onSelect,
}: {
  stages: StageRow[];
  selectedId: string | null;
  /** Where the work is. Not always the row marked `in_progress` — see the
   *  workspace, which explains why a freshly planned cycle has none. */
  currentId: string | null;
  onSelect: (stage: StageRow) => void;
}) {
  return (
    <ol className="relative">
      {stages.map((stage, index) => {
        const previous = stages[index - 1];
        const gateOpens = stage.is_gate && !previous?.is_gate;
        const gateCloses = stage.is_gate && !stages[index + 1]?.is_gate;
        return (
          <li key={stage.id}>
            {gateOpens ? <GateFence label="Approval gate" /> : null}
            <StageRow
              stage={stage}
              selected={stage.id === selectedId}
              current={stage.id === currentId}
              first={index === 0}
              last={index === stages.length - 1}
              onSelect={() => onSelect(stage)}
            />
            {gateCloses ? <GateFence /> : null}
          </li>
        );
      })}
    </ol>
  );
}

function GateFence({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 py-1.5" aria-hidden>
      <span className="h-px flex-1 bg-border-strong" />
      {label ? <span className="type-overline">{label}</span> : null}
      <span className="h-px flex-1 bg-border-strong" />
    </div>
  );
}

function StageRow({
  stage,
  selected,
  current,
  first,
  last,
  onSelect,
}: {
  stage: StageRow;
  selected: boolean;
  current: boolean;
  first: boolean;
  last: boolean;
  onSelect: () => void;
}) {
  const meta = STAGE_STATUS_META[stage.status] ?? {
    label: stage.status,
    family: "neutral" as const,
  };
  const skipped = stage.status === "skipped";
  const blocked = current && stage.blockers.length > 0;

  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? "step" : undefined}
      className={cn(
        "group relative flex w-full items-start gap-3 rounded-md px-2 py-2 text-left",
        "transition-colors duration-80 ease-state hover:bg-surface-hover",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        selected && "bg-action-accent-tint hover:bg-action-accent-tint",
      )}
    >
      {/* The spine. Drawn per row rather than once behind the list so a fence
          between two rows breaks it, which is the point of a fence. */}
      <span className="relative flex w-5 shrink-0 justify-center self-stretch" aria-hidden>
        {!first ? <span className="absolute -top-2 bottom-1/2 w-px bg-border" /> : null}
        {!last ? <span className="absolute bottom-0 top-1/2 w-px bg-border" /> : null}
        <StageMarker stage={stage} current={current} />
      </span>

      <span className="min-w-0 flex-1">
        <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span
            className={cn(
              "text-body-md",
              skipped ? "text-text-subtle line-through" : "font-semibold text-text-primary",
            )}
          >
            {stage.label}
          </span>
          {stage.is_gate ? (
            <Tooltip content="A gate is never skipped, whatever the tier">
              <span className="type-overline shrink-0 rounded-full border border-border px-1.5">
                Gate
              </span>
            </Tooltip>
          ) : null}
        </span>

        <span className="mt-1 flex flex-wrap items-center gap-2">
          <StatusPill
            status={blocked ? "warning" : current ? "progress" : meta.family}
            label={
              blocked
                ? `${stage.blockers.length} blocking`
                : current && stage.status === "not_started"
                  ? "Up next"
                  : meta.label
            }
            kind="inline"
          />
          {stage.exited_at && !skipped ? (
            <span className="text-caption text-text-subtle">{fmtDate(stage.exited_at)}</span>
          ) : null}
        </span>

        {skipped ? (
          <span className="mt-1 block text-caption text-text-subtle">
            {stage.skipped_by_policy
              ? `Skipped by policy: ${stage.skipped_by_policy}`
              : (stage.skipped_reason ?? "Skipped")}
          </span>
        ) : null}
      </span>
    </button>
  );
}

/**
 * Circle for a stage, diamond for a gate. Shape carries the distinction as well
 * as colour, so the gate is still a gate in greyscale and to a reader who does
 * not separate the two hues.
 */
function StageMarker({ stage, current }: { stage: StageRow; current: boolean }) {
  const complete = stage.status === "complete";
  const skipped = stage.status === "skipped";
  const blocked = current && stage.blockers.length > 0;

  const tone = skipped
    ? "border-border bg-surface-page text-text-faint"
    : complete
      ? "border-status-success-base bg-status-success-base text-text-inverse"
      : blocked
        ? "border-status-warning-base bg-status-warning-bg text-status-warning-text"
        : current
          ? "border-action-accent bg-surface-primary text-action-accent"
          : "border-border bg-surface-primary text-text-faint";

  return (
    <span
      className={cn(
        "relative z-[1] flex size-5 items-center justify-center border",
        stage.is_gate ? "rotate-45 rounded-2xs" : "rounded-full",
        tone,
      )}
    >
      <span className={cn("flex items-center justify-center", stage.is_gate && "-rotate-45")}>
        {complete ? (
          <Icon name="check" className="size-3" />
        ) : skipped ? (
          <span className="h-px w-2 bg-current" />
        ) : blocked ? (
          <Icon name="alert" className="size-3" />
        ) : current ? (
          <span className="size-1.5 rounded-full bg-current" />
        ) : null}
      </span>
    </span>
  );
}
