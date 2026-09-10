import * as LabelPrimitive from "@radix-ui/react-label";
import { forwardRef, useId, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & {
  label: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  /** Shows "n / max" under the field. Only meaningful with `maxLength`. */
  showCount?: boolean;
};

/**
 * The multi-line half of `TextField`, with the same anatomy: label 6px above,
 * helper 6px below, error replacing the helper in the same slot.
 *
 * It exists because the same seven-line block had been hand-rolled in eight
 * files, each with slightly different padding and none with an error slot — so
 * a rejected rationale had nowhere to say why it was rejected.
 */
export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ id, label, hint, error, optional = false, showCount = false, className, disabled, rows = 4, ...props }, ref) => {
    const generatedId = useId();
    const fieldId = id ?? props.name ?? generatedId;
    const hintId = `${fieldId}-hint`;
    const errorId = `${fieldId}-error`;
    const length = typeof props.value === "string" ? props.value.length : 0;

    return (
      <div className="flex w-full flex-col gap-1.5">
        <LabelPrimitive.Root htmlFor={fieldId} className="font-sans text-label-sm text-text-secondary">
          {label}
          {optional ? <span className="ml-1 font-normal text-text-faint">(optional)</span> : null}
        </LabelPrimitive.Root>
        <textarea
          ref={ref}
          id={fieldId}
          rows={rows}
          disabled={disabled}
          aria-invalid={Boolean(error) || undefined}
          aria-describedby={error ? errorId : hint ? hintId : undefined}
          className={cn(
            "w-full rounded-sm border bg-surface-primary px-3 py-2 font-sans text-body-md text-text-primary",
            "transition-colors duration-150 ease-state placeholder:text-text-faint",
            "focus:outline-none focus-visible:outline-none",
            "disabled:cursor-not-allowed disabled:bg-surface-sunken disabled:text-text-faint",
            error
              ? "border-status-danger-base shadow-input-error"
              : "border-border focus:border-action-accent focus:shadow-input-focus",
            className,
          )}
          {...props}
        />
        <div className="flex items-start justify-between gap-3">
          {error ? (
            <p id={errorId} className="flex items-start gap-1 text-body-sm text-status-danger-text">
              <Icon name="alert" className="mt-px size-3.5 shrink-0" />
              {error}
            </p>
          ) : hint ? (
            <p id={hintId} className="text-body-sm text-text-subtle">
              {hint}
            </p>
          ) : (
            <span />
          )}
          {showCount && props.maxLength ? (
            <span className="tabular shrink-0 text-caption text-text-subtle">
              {length} / {props.maxLength}
            </span>
          ) : null}
        </div>
      </div>
    );
  },
);

TextArea.displayName = "TextArea";
