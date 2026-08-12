import { forwardRef, type ReactNode } from "react";
import { cn } from "@/lib/cn";
import { Icon } from "@/components/ui/icon";

type ErrorBannerProps = {
  title: string;
  /** Body copy — say what happened and how to fix it (§5.7). */
  children?: ReactNode;
  className?: string;
};

/**
 * DS §7.2 inline alert — a form-level problem inside a working view.
 * Move focus to it after a rejected submit (it is focusable via ref +
 * tabIndex −1). Never used for transient successes (toast) or ongoing
 * conditions (page banner).
 */
export const ErrorBanner = forwardRef<HTMLDivElement, ErrorBannerProps>(
  function ErrorBanner({ title, children, className }, ref) {
    return (
      <div
        ref={ref}
        role="alert"
        tabIndex={-1}
        className={cn(
          "flex items-start gap-2.5 rounded-md border border-status-danger-border bg-status-danger-bg px-3.5 py-3",
          "focus:outline-none focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent",
          className,
        )}
      >
        <Icon
          name="alert"
          className="mt-px size-4 shrink-0 text-status-danger-base"
        />
        <div className="min-w-0">
          <p className="text-label-md font-bold text-action-danger-hover">
            {title}
          </p>
          {children ? (
            <div className="mt-0.5 text-body-sm text-status-danger-text">
              {children}
            </div>
          ) : null}
        </div>
      </div>
    );
  },
);
