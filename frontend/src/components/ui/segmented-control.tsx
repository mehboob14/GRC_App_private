import { cn } from "@/lib/cn";
import { Icon, type IconName } from "@/components/ui/icon";

export type SegmentedItem<T extends string> = {
  id: T;
  label: string;
  /** When set, the label becomes the accessible name and is visually hidden. */
  icon?: IconName;
};

/**
 * A local view switch that sits inside a Toolbar: open/all/accepted, list/board,
 * Live/Weekly. It changes how the current data is shown; it does not navigate.
 * For switching page sections, use TabStrip instead.
 *
 * Four copies of this existed with four different radii, paddings and type
 * sizes. This is the one, modelled on the vulnerabilities register's version
 * (the densest and closest to the token scale).
 */
export function SegmentedControl<T extends string>({
  items,
  value,
  onChange,
  label,
  className,
}: {
  items: readonly SegmentedItem<T>[];
  value: T;
  onChange: (id: T) => void;
  /** aria-label for the group, e.g. "Vulnerability scope". */
  label: string;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={label}
      className={cn("flex shrink-0 rounded-md border border-border p-0.5", className)}
    >
      {items.map((item) => {
        const isActive = item.id === value;
        return (
          <button
            key={item.id}
            type="button"
            aria-pressed={isActive}
            title={item.icon ? item.label : undefined}
            onClick={() => onChange(item.id)}
            className={cn(
              "inline-flex items-center gap-1.5 whitespace-nowrap rounded-sm px-2.5 py-1 text-caption font-semibold transition-colors duration-80 ease-state",
              isActive
                ? "bg-surface-hover text-text-primary"
                : "text-text-subtle hover:text-text-primary",
            )}
          >
            {item.icon ? (
              <>
                <Icon name={item.icon} className="size-4" aria-hidden />
                <span className="sr-only">{item.label}</span>
              </>
            ) : (
              item.label
            )}
          </button>
        );
      })}
    </div>
  );
}
