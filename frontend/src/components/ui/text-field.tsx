import * as LabelPrimitive from "@radix-ui/react-label";
import { forwardRef, type InputHTMLAttributes, type ReactNode } from "react";
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
    const fieldId = id ?? props.name;
    const hintId = fieldId ? `${fieldId}-hint` : undefined;
    const errorId = fieldId ? `${fieldId}-error` : undefined;

    return (
      <div className="flex w-full flex-col gap-1.5">
        <LabelPrimitive.Root
          htmlFor={fieldId}
          className="font-sans text-label-sm text-text"
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
              "h-9 w-full rounded-lg border bg-bg-elevated px-3 font-sans text-body-md text-text",
              "placeholder:text-text-faint",
              "disabled:cursor-not-allowed disabled:bg-bg-sunken disabled:text-text-faint",
              error ? "border-fail" : "border-border",
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
          <p id={errorId} className="text-body-sm text-fail-fg">
            {error}
          </p>
        ) : hint ? (
          <p id={hintId} className="text-body-sm text-text-faint">
            {hint}
          </p>
        ) : null}
      </div>
    );
  },
);

TextField.displayName = "TextField";
