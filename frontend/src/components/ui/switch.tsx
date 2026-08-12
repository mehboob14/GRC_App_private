import * as SwitchPrimitive from "@radix-ui/react-switch";
import { cn } from "@/lib/cn";

type SwitchProps = {
  checked?: boolean;
  defaultChecked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  "aria-label"?: string;
  className?: string;
};

/**
 * DS §5.5 — toggle 38×22, instant effect only (never a deferred form input).
 */
export function Switch({
  checked,
  defaultChecked,
  onCheckedChange,
  disabled,
  id,
  "aria-label": ariaLabel,
  className,
}: SwitchProps) {
  return (
    <SwitchPrimitive.Root
      id={id}
      checked={checked}
      defaultChecked={defaultChecked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={ariaLabel}
      className={cn(
        "peer inline-flex h-[22px] w-[38px] shrink-0 cursor-pointer items-center rounded-full border border-transparent",
        "bg-border-strong transition-colors duration-150 ease-state data-[state=checked]:bg-action-accent",
        "disabled:cursor-not-allowed disabled:opacity-45",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        className,
      )}
    >
      <SwitchPrimitive.Thumb
        className={cn(
          "pointer-events-none block size-[18px] rounded-full bg-white shadow-1 transition-transform duration-150 ease-state",
          "translate-x-px data-[state=checked]:translate-x-[17px]",
        )}
      />
    </SwitchPrimitive.Root>
  );
}
