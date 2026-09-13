import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * The card every chart and dashboard metric sits in: title centred on top, an
 * optional link or control pinned to the right of it, then the chart.
 *
 * One component so a dashboard in any module reads the same way: the title
 * names the question, the legend (drawn by the chart) names the parts, and the
 * chart answers it.
 */
export function ChartCard({
  title,
  action,
  className,
  children,
}: {
  title: string;
  /** A small link or control, e.g. "View all". */
  action?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={cn("rounded-lg border border-border bg-surface-primary p-5", className)}>
      <header className="relative mb-4 flex min-h-6 items-center justify-center">
        <h2 className={cn("text-center font-sans text-title-sm text-text-primary", action ? "px-20" : null)}>
          {title}
        </h2>
        {action ? <div className="absolute right-0 top-1/2 -translate-y-1/2">{action}</div> : null}
      </header>
      {children}
    </section>
  );
}
