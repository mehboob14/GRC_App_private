import {
  useEffect,
  useRef,
  type ClipboardEvent,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/cn";

/**
 * A six box code entry: typing advances, Backspace steps back, arrow keys move,
 * and pasting the whole code (or an autofilled one time code) fills every box
 * at once. `onComplete` fires the moment the last digit lands, so nobody has to
 * reach for a button.
 */
export function OtpInput({
  value,
  onChange,
  onComplete,
  length = 6,
  disabled,
  invalid,
  autoFocus,
  label = "Authentication code",
}: {
  value: string;
  onChange: (value: string) => void;
  onComplete?: (value: string) => void;
  length?: number;
  disabled?: boolean;
  invalid?: boolean;
  autoFocus?: boolean;
  label?: string;
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length }, (_, i) => value[i] ?? "");

  useEffect(() => {
    if (autoFocus) refs.current[Math.min(value.length, length - 1)]?.focus();
    // Focus once, on mount; later focus follows typing.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A refused code clears, so the next attempt starts at the first box.
  useEffect(() => {
    if (invalid && value === "") refs.current[0]?.focus();
  }, [invalid, value]);

  const commit = (next: string) => {
    const clean = next.replace(/\D/g, "").slice(0, length);
    onChange(clean);
    if (clean.length === length) onComplete?.(clean);
    return clean;
  };

  const setAt = (index: number, digit: string) => {
    const chars = digits.slice();
    chars[index] = digit;
    return chars.join("").replace(/\s/g, "");
  };

  const onKey = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace") {
      event.preventDefault();
      if (digits[index]) {
        commit(value.slice(0, index) + value.slice(index + 1));
      } else if (index > 0) {
        commit(value.slice(0, index - 1) + value.slice(index));
        refs.current[index - 1]?.focus();
      }
    } else if (event.key === "ArrowLeft" && index > 0) {
      refs.current[index - 1]?.focus();
    } else if (event.key === "ArrowRight" && index < length - 1) {
      refs.current[index + 1]?.focus();
    }
  };

  const onPaste = (event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "");
    if (!pasted) return;
    event.preventDefault();
    const clean = commit(pasted);
    refs.current[Math.min(clean.length, length - 1)]?.focus();
  };

  return (
    <div
      role="group"
      aria-label={label}
      className={cn("flex justify-between gap-2", invalid && "otp-shake")}
    >
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(node) => {
            refs.current[index] = node;
          }}
          value={digit}
          disabled={disabled}
          inputMode="numeric"
          pattern="[0-9]*"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          aria-label={`Digit ${index + 1} of ${length}`}
          aria-invalid={invalid || undefined}
          maxLength={length}
          onPaste={onPaste}
          onKeyDown={(e) => onKey(index, e)}
          onFocus={(e) => e.currentTarget.select()}
          onChange={(e) => {
            const typed = e.target.value.replace(/\D/g, "");
            if (!typed) return;
            if (typed.length > 1) {
              // Autofill or a fast paste into one box: treat it as the whole code.
              const clean = commit(typed);
              refs.current[Math.min(clean.length, length - 1)]?.focus();
              return;
            }
            // Digits pack left: focus the first empty box, or the next one when
            // the code is full and a digit was just replaced.
            const clean = commit(setAt(index, typed));
            const nextBox =
              clean.length < length
                ? clean.length
                : Math.min(index + 1, length - 1);
            refs.current[nextBox]?.focus();
          }}
          className={cn(
            "otp-box h-14 w-full min-w-0 rounded-xl border bg-surface-primary text-center font-display text-title-md font-bold text-text-primary tabular-nums",
            "transition-[border-color,box-shadow,transform] duration-150 focus:outline-none",
            invalid
              ? "border-status-danger-base shadow-[0_0_0_4px_rgb(var(--color-status-danger-base)/0.12)]"
              : digit
                ? "border-action-accent/60"
                : "border-border hover:border-border-strong",
            "focus:border-action-accent focus:shadow-[0_0_0_4px_rgb(var(--color-action-accent)/0.14)]",
            disabled && "opacity-60",
          )}
        />
      ))}
    </div>
  );
}
