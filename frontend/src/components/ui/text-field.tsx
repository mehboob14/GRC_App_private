import * as LabelPrimitive from "@radix-ui/react-label";
import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/cn";

type TextFieldProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  trailing?: ReactNode;
};

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
          className="font-sans text-label-sm text-text-primary"
        >
          {label}
          {optional ? (
            <span className="ml-1 font-normal text-text-subtle">(optional)</span>
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
              "h-9 w-full rounded-md border bg-surface-primary px-3 font-sans text-body-md text-text-primary",
              "placeholder:text-text-subtle",
              "disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-text-subtle",
              error ? "border-status-danger-base" : "border-border",
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
          <p id={errorId} className="text-body-sm text-status-danger-text">
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
