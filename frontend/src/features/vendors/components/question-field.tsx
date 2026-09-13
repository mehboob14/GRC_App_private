import { useEffect, useState, type ReactNode } from "react";
import { Icon } from "@/components/ui";
import { cn } from "@/lib/cn";
import { pickedKeys } from "../questionnaire-logic";
import type { AnswerValue, QuestionType } from "../types";

type FieldOption = { key: string; label: string };

/**
 * One answer control for any question type, shared by the vendor portal, the
 * tiering dialog and the builder's preview, so all three ask a question the
 * same way.
 *
 * Choices report every change at once. Text, numbers and dates are typed, so
 * they report on `onCommit` (blur or Enter) and the caller decides when to save.
 * A file question has no control here: the caller owns uploading.
 */
export function QuestionField({
  label,
  type,
  options,
  value,
  onCommit,
  disabled,
  layout = "auto",
  optionMeta,
}: {
  /** Accessible name, usually the question itself. */
  label: string;
  type: QuestionType;
  options: FieldOption[];
  value: AnswerValue | undefined;
  onCommit: (value: AnswerValue) => void;
  disabled?: boolean;
  /** `chips` for short answers in a row, `cards` for longer ones stacked. */
  layout?: "auto" | "chips" | "cards";
  /** Extra text at the end of an option, e.g. the points it adds. */
  optionMeta?: (option: FieldOption) => ReactNode;
}) {
  if (type === "single_choice" || type === "multi_choice") {
    const multi = type === "multi_choice";
    const picked = pickedKeys(value ?? null);
    const chips =
      layout === "chips" ||
      (layout === "auto" &&
        !optionMeta &&
        options.length <= 5 &&
        options.every((o) => o.label.length <= 24));
    const toggle = (key: string) => {
      if (!multi) return onCommit(key);
      const next = picked.includes(key) ? picked.filter((k) => k !== key) : [...picked, key];
      onCommit(options.map((o) => o.key).filter((k) => next.includes(k)));
    };
    return (
      <div
        role={multi ? "group" : "radiogroup"}
        aria-label={label}
        className={chips ? "flex flex-wrap gap-2" : "grid gap-1.5"}
      >
        {options.map((option) => {
          const on = picked.includes(option.key);
          return (
            <button
              key={option.key}
              type="button"
              role={multi ? "checkbox" : "radio"}
              aria-checked={on}
              disabled={disabled}
              onClick={() => toggle(option.key)}
              className={cn(
                "flex items-center gap-2.5 border text-left transition-colors duration-80 ease-state",
                "focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
                "disabled:cursor-not-allowed disabled:opacity-60",
                chips ? "rounded-sm px-3 py-1.5 text-label-md" : "rounded-md px-3 py-2.5 text-body-md",
                on
                  ? "border-action-accent bg-action-accent-tint text-action-accent"
                  : "border-border bg-surface-primary text-text-primary hover:bg-surface-hover",
              )}
            >
              {chips && !multi ? null : (
                <span
                  aria-hidden
                  className={cn(
                    "grid size-4 shrink-0 place-items-center border-1.5",
                    multi ? "rounded-2xs" : "rounded-full",
                    on ? "border-action-accent bg-action-accent text-white" : "border-border-strong",
                  )}
                >
                  {on ? (
                    multi ? (
                      <Icon name="check" className="size-2.5" />
                    ) : (
                      <span className="size-1.5 rounded-full bg-white" />
                    )
                  ) : null}
                </span>
              )}
              <span className={cn("min-w-0", chips ? "" : "flex-1")}>{option.label}</span>
              {optionMeta ? (
                <span className="tabular shrink-0 text-caption text-text-subtle">
                  {optionMeta(option)}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>
    );
  }

  if (type === "file") return null;
  return (
    <TypedInput label={label} type={type} value={value} onCommit={onCommit} disabled={disabled} />
  );
}

const INPUT =
  "w-full rounded-sm border border-border bg-surface-primary px-3 font-sans text-body-md text-text-primary transition-colors duration-150 ease-state placeholder:text-text-faint focus:border-action-accent focus:shadow-input-focus focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-sunken";

function TypedInput({
  label,
  type,
  value,
  onCommit,
  disabled,
}: {
  label: string;
  type: Exclude<QuestionType, "single_choice" | "multi_choice" | "file">;
  value: AnswerValue | undefined;
  onCommit: (value: AnswerValue) => void;
  disabled?: boolean;
}) {
  const shown = value === null || value === undefined ? "" : String(value);
  const [draft, setDraft] = useState(shown);
  // Follow the saved value when it changes from outside, without fighting typing.
  useEffect(() => setDraft(shown), [shown]);

  const commit = () => {
    const text = draft.trim();
    if (text === shown) return;
    if (type === "number") {
      const parsed = text === "" ? null : Number(text);
      onCommit(parsed === null || Number.isNaN(parsed) ? null : parsed);
      return;
    }
    onCommit(text === "" ? null : text);
  };

  if (type === "paragraph") {
    return (
      <textarea
        aria-label={label}
        value={draft}
        disabled={disabled}
        rows={3}
        maxLength={8000}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        className={cn(INPUT, "py-2")}
      />
    );
  }
  return (
    <input
      aria-label={label}
      type={type === "number" ? "number" : type === "date" ? "date" : "text"}
      inputMode={type === "number" ? "decimal" : undefined}
      value={draft}
      disabled={disabled}
      maxLength={type === "text" ? 500 : undefined}
      onChange={(e) => {
        setDraft(e.target.value);
        // A date is picked, not typed: the pick is the answer.
        if (type === "date" && e.target.value !== shown) onCommit(e.target.value || null);
      }}
      onBlur={type === "date" ? undefined : commit}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          commit();
        }
      }}
      className={cn(INPUT, "h-9", type === "text" ? "" : "max-w-56")}
    />
  );
}
