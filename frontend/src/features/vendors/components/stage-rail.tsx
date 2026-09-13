import { Icon, Tooltip } from "@/components/ui";
import { cn } from "@/lib/cn";

/** Where one row of the rail stands. `locked` cannot start until tiering is done. */
export type RailState = "done" | "current" | "blocked" | "upcoming" | "skipped" | "locked";

export type RailItem = {
  id: string;
  label: string;
  state: RailState;
  isGate: boolean;
  /** Short right-hand note: a blocker count, a tier, "Skipped". */
  meta?: string;
  /** Why a row is the way it is, on hover. Used for skip reasons. */
  tooltip?: string;
};

/**
 * The lifecycle as a left-hand sub-navigation.
 *
 * Grouped by what the stages are for rather than fenced off with rules:
 * everything before the approval gate assesses the vendor, the gate decides,
 * everything after operates the relationship. The grouping comes from where the
 * gate sits, not from stage names, so a reordered policy still groups honestly.
 *
 * Shape carries the gate as well as position: a diamond, not a circle.
 */
export function StageRail({
  items,
  selectedId,
  onSelect,
}: {
  items: RailItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}) {
  const gateIndex = items.findIndex((i) => i.isGate);
  const groups =
    gateIndex < 0
      ? [{ label: "Stages", rows: items }]
      : [
          { label: "Assess", rows: items.slice(0, gateIndex) },
          { label: "Decide", rows: items.slice(gateIndex, gateIndex + 1) },
          { label: "Operate", rows: items.slice(gateIndex + 1) },
        ].filter((g) => g.rows.length > 0);

  return (
    <nav aria-label="Lifecycle stages" className="space-y-4">
      {groups.map((group) => (
        <div key={group.label}>
          <p className="type-overline px-2 pb-1">{group.label}</p>
          <ol className="space-y-px">
            {group.rows.map((item) => (
              <li key={item.id}>
                <RailRow
                  item={item}
                  selected={item.id === selectedId}
                  onSelect={() => onSelect(item.id)}
                />
              </li>
            ))}
          </ol>
        </div>
      ))}
    </nav>
  );
}

function RailRow({
  item,
  selected,
  onSelect,
}: {
  item: RailItem;
  selected: boolean;
  onSelect: () => void;
}) {
  const locked = item.state === "locked";
  const quiet = locked || item.state === "skipped";
  const active = item.state === "current" || item.state === "blocked";

  const row = (
    <button
      type="button"
      onClick={onSelect}
      disabled={locked}
      aria-current={selected ? "step" : undefined}
      className={cn(
        "flex h-9 w-full items-center gap-2.5 rounded-sm px-2 text-left",
        "transition-colors duration-80 ease-state",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        "disabled:cursor-default",
        selected ? "bg-action-accent-tint" : locked ? null : "hover:bg-surface-hover",
      )}
    >
      <Marker state={item.state} gate={item.isGate} />
      <span
        className={cn(
          "min-w-0 flex-1 truncate text-body-sm",
          quiet
            ? "text-text-faint"
            : selected || active
              ? "font-semibold text-text-primary"
              : "text-text-secondary",
        )}
      >
        {item.label}
      </span>
      {item.meta ? (
        <span
          className={cn(
            "tabular shrink-0 text-caption",
            item.state === "blocked"
              ? "font-semibold text-status-warning-text"
              : item.state === "current"
                ? "font-semibold text-action-accent"
                : "text-text-subtle",
          )}
        >
          {item.meta}
        </span>
      ) : null}
    </button>
  );

  return item.tooltip ? (
    <Tooltip content={item.tooltip}>
      <span className="block">{row}</span>
    </Tooltip>
  ) : (
    row
  );
}

/**
 * Circle for a stage, diamond for the gate, so the gate is still a gate in
 * greyscale and to a reader who does not separate the hues.
 */
function Marker({ state, gate }: { state: RailState; gate: boolean }) {
  const tone =
    state === "done"
      ? "border-status-success-base bg-status-success-base text-white"
      : state === "blocked"
        ? "border-status-warning-base bg-status-warning-base text-white"
        : state === "current"
          ? "border-action-accent bg-surface-primary text-action-accent"
          : state === "locked" || state === "skipped"
            ? "border-border bg-surface-sunken text-text-faint"
            : "border-border-strong bg-surface-primary text-text-faint";

  return (
    <span
      className={cn(
        "flex size-[18px] shrink-0 items-center justify-center border-1.5",
        gate ? "rotate-45 scale-90 rounded-2xs" : "rounded-full",
        tone,
      )}
      aria-hidden
    >
      <span className={cn("flex items-center justify-center", gate && "-rotate-45")}>
        {state === "done" ? (
          <Icon name="check" className="size-2.5" />
        ) : state === "blocked" ? (
          <span className="text-[10px] font-extrabold leading-none">!</span>
        ) : state === "current" ? (
          <span className="size-1.5 rounded-full bg-current" />
        ) : null}
      </span>
    </span>
  );
}
