import { forwardRef, useState, type ReactNode } from "react";
import { Icon, type IconName } from "@/components/ui";
import { cn } from "@/lib/cn";
import { linkClass } from "./helpers";
import type { AuthFailure } from "./auth-errors";

type Tone = "danger" | "warning" | "info" | "success";

const TONE: Record<
  Tone,
  { box: string; badge: string; title: string; body: string; icon: IconName }
> = {
  danger: {
    box: "border-status-danger-border bg-status-danger-bg",
    badge: "bg-status-danger-base text-white",
    title: "text-action-danger-hover",
    body: "text-status-danger-text",
    icon: "alert",
  },
  warning: {
    box: "border-status-warning-border bg-status-warning-bg",
    badge: "bg-status-warning-base text-white",
    title: "text-status-warning-text",
    body: "text-status-warning-text",
    icon: "alert",
  },
  info: {
    box: "border-action-accent-border bg-action-accent-tint",
    badge: "bg-action-accent text-white",
    title: "text-action-primary",
    body: "text-text-secondary",
    icon: "info",
  },
  success: {
    box: "border-status-success-border bg-status-success-bg",
    badge: "bg-status-success-base text-white",
    title: "text-status-success-text",
    body: "text-status-success-text",
    icon: "check",
  },
};

/**
 * A form level message on the auth card: a solid badge, one bold line saying
 * what happened, one line saying what to do, and the action that does it.
 * Danger and warning interrupt a screen reader; info and success wait politely.
 */
export const AuthAlert = forwardRef<
  HTMLDivElement,
  {
    tone?: Tone;
    title: string;
    children?: ReactNode;
    action?: ReactNode;
    icon?: IconName;
    className?: string;
  }
>(function AuthAlert(
  { tone = "danger", title, children, action, icon, className },
  ref,
) {
  const t = TONE[tone];
  const urgent = tone === "danger" || tone === "warning";
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role={urgent ? "alert" : "status"}
      className={cn(
        "auth-alert-in flex items-start gap-3 rounded-xl border px-3.5 py-3 text-left focus:outline-none",
        t.box,
        className,
      )}
    >
      <span
        className={cn(
          "mt-px grid size-6 shrink-0 place-items-center rounded-full",
          t.badge,
        )}
        aria-hidden
      >
        <Icon name={icon ?? t.icon} className="size-3.5" />
      </span>
      <div className="min-w-0 flex-1">
        <p className={cn("text-label-md font-bold", t.title)}>{title}</p>
        {children ? (
          <div className={cn("mt-0.5 text-body-sm", t.body)}>{children}</div>
        ) : null}
        {action ? (
          <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-body-sm">
            {action}
          </div>
        ) : null}
      </div>
    </div>
  );
});

const FAILURE_ICON: Partial<Record<AuthFailure["kind"], IconName>> = {
  network: "wifiOff",
  timeout: "countdown",
  rateLimit: "countdown",
  expired: "countdown",
  credentials: "lock",
  code: "fingerprint",
};

/**
 * An AuthFailure on screen, with the standard ways out: "Try again" when a retry
 * could work, and a copyable support reference (never printed, it is an id)
 * when the server logged one.
 */
export const FailureAlert = forwardRef<
  HTMLDivElement,
  {
    failure: AuthFailure;
    onRetry?: () => void;
    action?: ReactNode;
    className?: string;
  }
>(function FailureAlert({ failure, onRetry, action, className }, ref) {
  const [copied, setCopied] = useState(false);
  const retry = failure.retryable && onRetry;

  async function copyReference() {
    if (!failure.reference) return;
    try {
      await navigator.clipboard.writeText(failure.reference);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: nothing to recover, the alert still says what to do.
    }
  }

  return (
    <AuthAlert
      ref={ref}
      tone={
        failure.kind === "rateLimit" || failure.kind === "expired"
          ? "warning"
          : "danger"
      }
      icon={FAILURE_ICON[failure.kind]}
      title={failure.title}
      className={className}
      action={
        action || retry || failure.reference ? (
          <>
            {action}
            {retry ? (
              <button type="button" onClick={onRetry} className={linkClass}>
                Try again
              </button>
            ) : null}
            {failure.reference ? (
              <button
                type="button"
                onClick={() => void copyReference()}
                className="inline-flex items-center gap-1 rounded-sm font-medium text-text-subtle hover:text-text-primary focus-visible:outline focus-visible:outline-2 focus-visible:outline-action-accent"
              >
                <Icon name={copied ? "check" : "copy"} className="size-3.5" />
                {copied ? "Reference copied" : "Copy reference for support"}
              </button>
            ) : null}
          </>
        ) : undefined
      }
    >
      {failure.body}
    </AuthAlert>
  );
});
