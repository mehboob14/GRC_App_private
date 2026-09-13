import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type CheckboxProps = {
  checked?: boolean | "indeterminate";
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
};

/**
 * DS §5.5 — 16×16, radius 4, resting border 1.5 border-strong; checked fill
 * action-accent with white check; indeterminate shows a white 8×2 bar.
 */
export function Checkbox({
  checked,
  defaultChecked,
  onCheckedChange,
  disabled,
  id,
  "aria-label": ariaLabel,
  className,
}: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      id={id}
      checked={checked}
      defaultChecked={defaultChecked}
      onCheckedChange={(value) => onCheckedChange?.(value === true)}
      disabled={disabled}
      aria-label={ariaLabel}
      className={cn(
        "flex size-4 shrink-0 items-center justify-center rounded-2xs border-1.5 border-border-strong bg-surface-primary",
        "transition-colors duration-150 ease-state",
        "data-[state=checked]:border-action-accent data-[state=checked]:bg-action-accent",
        "data-[state=indeterminate]:border-action-accent data-[state=indeterminate]:bg-action-accent",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        "disabled:cursor-not-allowed disabled:opacity-45",
        className,
      )}
    >
      {/* action-primary-fg keeps the glyph legible when the accent fill
          lightens in dark mode. */}
      <CheckboxPrimitive.Indicator className="text-action-primary-fg">
        {checked === "indeterminate" ? (
          <span className="block h-0.5 w-2 rounded-full bg-action-primary-fg" />
        ) : (
          <Icon name="check" className="size-[11px]" />
        )}
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
