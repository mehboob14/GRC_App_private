import * as LabelPrimitive from "@radix-ui/react-label";
import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type TextFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  trailing?: ReactNode;
  /** md = 36 default · lg = 44 auth screens (DS §4.6). */
  size?: "md" | "lg";
};

/**
 * DS §5.4 form control anatomy: label 6px above, control h36/h44 radius sm,
 * helper 6px below. Never floating labels; placeholders are example values.
 */
export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  (
    {
      id,
      label,
      hint,
      error,
      optional = false,
      trailing,
      className,
      disabled,
      size = "md",
      ...props
    },
    ref,
  ) => {
    // The label must always point at the input: fall back to a generated id
    // when the caller provides neither id nor name.
    const generatedId = useId();
    const fieldId = id ?? props.name ?? generatedId;
    const hintId = `${fieldId}-hint`;
    const errorId = `${fieldId}-error`;

    return (
      <div className="flex w-full flex-col gap-1.5">
        <LabelPrimitive.Root
          htmlFor={fieldId}
          className="font-sans text-label-sm text-text-secondary"
        >
          {label}
          {optional ? (
            <span className="ml-1 font-normal text-text-faint">(optional)</span>
          ) : null}
        </LabelPrimitive.Root>
        <div className="relative">
          <input
            ref={ref}
            id={fieldId}
            disabled={disabled}
            aria-invalid={Boolean(error) || undefined}
            aria-describedby={error ? errorId : hint ? hintId : undefined}
            className={cn(
              "w-full rounded-sm border bg-surface-primary px-3 font-sans text-body-md text-text-primary",
              "transition-colors duration-150 ease-state placeholder:text-text-faint",
              size === "lg" ? "h-11" : "h-9",
              "focus:outline-none focus-visible:outline-none",
              "disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-text-faint",
              error
                ? "border-status-danger-base shadow-input-error"
                : "border-border focus:border-action-accent focus:shadow-input-focus",
              trailing && "pr-10",
              className,
            )}
            {...props}
          />
          {trailing ? (
            <div className="absolute inset-y-0 right-0 flex items-center pr-2">
              {trailing}
            </div>
          ) : null}
        </div>
        {error ? (
          <p
            id={errorId}
            className="flex items-start gap-1 text-body-sm text-status-danger-text"
          >
            <Icon name="alert" className="mt-px size-3.5 shrink-0" />
            {error}
          </p>
        ) : hint ? (
          <p id={hintId} className="text-body-sm text-text-subtle">
            {hint}
          </p>
        ) : null}
      </div>
    );
  },
);

TextField.displayName = "TextField";
