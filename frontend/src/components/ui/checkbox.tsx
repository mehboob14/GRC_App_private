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
        "flex size-4 shrink-0 items-center justify-center rounded border border-border bg-surface-primary",
        "data-[state=checked]:border-action-accent data-[state=checked]:bg-action-primary data-[state=checked]:text-action-primary-fg",
        "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    >
      <CheckboxPrimitive.Indicator>
        <Icon name="check" className="size-3" strokeWidth={2.5} />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
