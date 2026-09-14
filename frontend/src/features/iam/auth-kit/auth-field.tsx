import * as LabelPrimitive from "@radix-ui/react-label";
import {
  forwardRef,
  useId,
  useState,
  type FocusEvent,
  type InputHTMLAttributes,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { Icon, type IconName } from "@/components/ui";
import { cn } from "@/lib/cn";
import {
  DEFAULT_PASSWORD_RULES,
  passwordStrength,
  type PasswordRule,
} from "./password-rules";

type AuthFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "size"> & {
  label: string;
  icon: IconName;
  error?: string;
  hint?: ReactNode;
  /** Shown once the value is valid, as a quiet confirmation. */
  valid?: boolean;
  /** Right of the label, like "Forgot password?". */
  labelAction?: ReactNode;
  trailing?: ReactNode;
  /** Under the field, above the hint, like a typo suggestion. */
  below?: ReactNode;
};

/**
 * The input for every auth screen: a persistent label, a leading solid icon
 * that lights with focus, a quiet check when the value is valid, and an error
 * that slides in under the field and is wired to it for screen readers.
 */
export const AuthField = forwardRef<HTMLInputElement, AuthFieldProps>(
  function AuthField(
    {
      id,
      label,
      icon,
      error,
      hint,
      valid,
      labelAction,
      trailing,
      below,
      className,
      disabled,
      ...props
    },
    ref,
  ) {
    const generated = useId();
    const fieldId = id ?? props.name ?? generated;
    const errorId = `${fieldId}-error`;
    const hintId = `${fieldId}-hint`;
    const describedBy =
      [error ? errorId : null, hint ? hintId : null]
        .filter(Boolean)
        .join(" ") || undefined;
    const showValid = Boolean(valid) && !error;
    const trailingSlots = (showValid ? 1 : 0) + (trailing ? 1 : 0);

    return (
      <div className="flex w-full flex-col">
        <div className="mb-1.5 flex items-baseline justify-between gap-3">
          <LabelPrimitive.Root
            htmlFor={fieldId}
            className="text-label-sm font-semibold text-text-primary"
          >
            {label}
          </LabelPrimitive.Root>
          {labelAction}
        </div>
        <div
          className={cn(
            "auth-input group relative",
            error && "auth-input-error",
            disabled && "opacity-60",
          )}
        >
          <Icon
            name={icon}
            className={cn(
              "pointer-events-none absolute left-3.5 top-1/2 size-[18px] -translate-y-1/2 transition-colors duration-150",
              error
                ? "text-status-danger-base"
                : "text-text-faint group-focus-within:text-action-accent",
            )}
          />
          <input
            ref={ref}
            id={fieldId}
            disabled={disabled}
            aria-invalid={Boolean(error) || undefined}
            aria-describedby={describedBy}
            className={cn(
              "h-12 w-full rounded-xl border bg-surface-primary pl-11 font-sans text-body-md text-text-primary",
              "transition-[border-color,box-shadow,background-color] duration-150 ease-state placeholder:text-text-faint",
              "focus:outline-none disabled:cursor-not-allowed",
              ["pr-3.5", "pr-12", "pr-20"][trailingSlots],
              error
                ? "border-status-danger-base shadow-[0_0_0_4px_rgb(var(--color-status-danger-base)/0.12)]"
                : "border-border hover:border-border-strong focus:border-action-accent focus:shadow-[0_0_0_4px_rgb(var(--color-action-accent)/0.14)]",
              className,
            )}
            {...props}
          />
          <div className="absolute inset-y-0 right-0 flex items-center gap-1 pr-2">
            {showValid ? (
              <span
                className="auth-valid-in grid size-6 place-items-center rounded-full bg-status-success-base text-white"
                aria-hidden
              >
                <Icon name="check" className="size-3.5" />
              </span>
            ) : null}
            {trailing}
          </div>
        </div>
        {below}
        {error ? (
          <p
            id={errorId}
            className="auth-msg-in mt-1.5 flex items-start gap-1.5 text-body-sm font-medium text-status-danger-text"
          >
            <Icon name="alert" className="mt-0.5 size-3.5 shrink-0" />
            <span>{error}</span>
          </p>
        ) : null}
        {hint ? (
          <div id={hintId} className="mt-1.5 text-body-sm text-text-subtle">
            {hint}
          </div>
        ) : null}
      </div>
    );
  },
);

type PasswordFieldProps = Omit<AuthFieldProps, "icon" | "type" | "trailing"> & {
  /** Show the live rules checklist for a new password. */
  rules?: PasswordRule[] | boolean;
  /** What has been typed so far, for the checklist (react-hook-form holds it, via watch). */
  typed?: string;
};

/**
 * Password input with a show and hide toggle, a Caps Lock warning (the most
 * common reason a correct password is refused), and for new passwords a live
 * checklist and strength bar so the policy is met while typing, not after.
 */
export const AuthPasswordField = forwardRef<
  HTMLInputElement,
  PasswordFieldProps
>(function AuthPasswordField(
  { rules, typed, onKeyDown, onKeyUp, onBlur, onFocus, below, ...props },
  ref,
) {
  const [visible, setVisible] = useState(false);
  const [capsLock, setCapsLock] = useState(false);
  const [focused, setFocused] = useState(false);
  const list = rules === true ? DEFAULT_PASSWORD_RULES : rules || null;
  const password = typed ?? "";

  const readCaps = (event: KeyboardEvent<HTMLInputElement>) => {
    if (typeof event.getModifierState === "function")
      setCapsLock(event.getModifierState("CapsLock"));
  };

  return (
    <AuthField
      {...props}
      ref={ref}
      icon="lock"
      type={visible ? "text" : "password"}
      onKeyDown={(e) => {
        readCaps(e);
        onKeyDown?.(e);
      }}
      onKeyUp={(e) => {
        readCaps(e);
        onKeyUp?.(e);
      }}
      onFocus={(e: FocusEvent<HTMLInputElement>) => {
        setFocused(true);
        onFocus?.(e);
      }}
      onBlur={(e: FocusEvent<HTMLInputElement>) => {
        setFocused(false);
        setCapsLock(false);
        onBlur?.(e);
      }}
      trailing={
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          aria-label={visible ? "Hide password" : "Show password"}
          aria-pressed={visible}
          className="grid size-9 place-items-center rounded-lg text-text-subtle transition-colors hover:bg-surface-hover hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
        >
          <Icon name={visible ? "eyeOff" : "eye"} className="size-[18px]" />
        </button>
      }
      below={
        <>
          {capsLock ? (
            <p
              role="status"
              className="auth-msg-in mt-1.5 inline-flex items-center gap-1.5 self-start rounded-md bg-status-warning-bg px-2 py-1 text-caption font-semibold text-status-warning-text"
            >
              <Icon name="capsLock" className="size-3.5" />
              Caps Lock is on
            </p>
          ) : null}
          {/* Nothing typed yet: the field's own "Choose a password" is enough, no wall of red rules. */}
          {list && (focused || password) ? (
            <PasswordChecklist
              password={password}
              rules={list}
              flagged={Boolean(props.error) && password.length > 0}
            />
          ) : null}
          {below}
        </>
      }
    />
  );
});

const LEVEL_TONE = [
  "bg-border",
  "bg-status-danger-base",
  "bg-status-warning-base",
  "bg-action-accent",
  "bg-status-success-base",
];
const LEVEL_TEXT = [
  "text-text-subtle",
  "text-status-danger-text",
  "text-status-warning-text",
  "text-action-primary",
  "text-status-success-text",
];

export function PasswordChecklist({
  password,
  rules,
  flagged = false,
}: {
  password: string;
  rules: PasswordRule[];
  /** After a refused submit, the rules still unmet turn red. */
  flagged?: boolean;
}) {
  const strength = passwordStrength(password, rules);
  return (
    <div
      className="auth-msg-in mt-2.5 rounded-xl border border-border bg-surface-sunken px-3.5 py-3"
      aria-live="polite"
    >
      <div className="flex items-center gap-3">
        <div className="grid flex-1 grid-cols-4 gap-1.5" aria-hidden>
          {[1, 2, 3, 4].map((step) => (
            <span
              key={step}
              className={cn(
                "h-1.5 rounded-full transition-colors duration-300",
                strength.level >= step
                  ? LEVEL_TONE[strength.level]
                  : "bg-border",
              )}
            />
          ))}
        </div>
        <span
          className={cn(
            "w-16 text-right text-caption font-semibold",
            LEVEL_TEXT[strength.level],
          )}
        >
          {password ? strength.label : ""}
        </span>
      </div>
      <ul className="mt-2.5 grid grid-cols-1 gap-x-4 gap-y-1.5 sm:grid-cols-2">
        {rules.map((rule) => {
          const ok = rule.test(password);
          return (
            <li
              key={rule.key}
              className={cn(
                "flex items-center gap-2 text-caption transition-colors",
                ok
                  ? "text-status-success-text"
                  : flagged
                    ? "font-semibold text-status-danger-text"
                    : "text-text-subtle",
              )}
            >
              <span
                className={cn(
                  "grid size-4 shrink-0 place-items-center rounded-full transition-all duration-200",
                  ok
                    ? "scale-100 bg-status-success-base text-white"
                    : flagged
                      ? "scale-90 bg-status-danger-base text-white"
                      : "scale-90 border border-border-strong bg-surface-primary",
                )}
                aria-hidden
              >
                {ok ? (
                  <Icon name="check" className="size-2.5" />
                ) : flagged ? (
                  <Icon name="x" className="size-2.5" />
                ) : null}
              </span>
              <span>
                {rule.label}
                <span className="sr-only">
                  {ok ? ", met" : ", not met yet"}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
