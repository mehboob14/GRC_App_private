import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import { useId, type ComponentPropsWithoutRef } from "react";
import { cn } from "@/lib/cn";

export function RadioGroup({
  className,
  ...props
}: ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>) {
  return (
    <RadioGroupPrimitive.Root
      className={cn("flex flex-col gap-2", className)}
      {...props}
    />
  );
}

type RadioGroupItemProps = ComponentPropsWithoutRef<
  typeof RadioGroupPrimitive.Item
> & {
  label: string;
  description?: string;
};

/**
 * DS §5.5 — radio 16×16 round, resting 1.5 border-strong; selected is a
 * 4.5px action-accent ring. Label Inter 600 13, description Inter 400 11.
 */
export function RadioGroupItem({
  className,
  label,
  description,
  id,
  ...props
}: RadioGroupItemProps) {
  const generatedId = useId();
  const itemId = id ?? generatedId;
  const descriptionId = `${itemId}-description`;

  return (
    <div className="flex items-start gap-2">
      <RadioGroupPrimitive.Item
        id={itemId}
        aria-describedby={description ? descriptionId : undefined}
        className={cn(
          "mt-0.5 size-4 shrink-0 rounded-full border-1.5 border-border-strong bg-surface-primary",
          "transition-colors duration-150 ease-state",
          "data-[state=checked]:border-4.5 data-[state=checked]:border-action-accent",
          "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
          "disabled:cursor-not-allowed disabled:opacity-45",
          className,
        )}
        {...props}
      />
      <label htmlFor={itemId} className="flex min-w-0 flex-col gap-0.5">
        <span className="font-sans text-label-md text-text-primary">
          {label}
        </span>
        {description ? (
          <span id={descriptionId} className="text-caption text-text-subtle">
            {description}
          </span>
        ) : null}
      </label>
    </div>
  );
}
