import { cn } from "@/lib/cn";
import type { Status } from "@/content/catalog";

const labels: Record<Status, string> = { live: "Live", preview: "Preview", soon: "Coming soon" };

/**
 * The one way the site marks availability. Text, not colour alone, so it is
 * announced to assistive technology and survives greyscale printing.
 */
export function StatusBadge({ status, size = "sm", className, hideLive = true }: { status: Status; size?: "xs" | "sm"; className?: string; hideLive?: boolean }) {
  if (status === "live" && hideLive) return null;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 whitespace-nowrap rounded-full border font-sans font-medium normal-case leading-none tracking-normal",
        size === "xs" ? "px-1.5 py-[3px] text-[10.5px]" : "px-2 py-1 text-[11.5px]",
        `status-badge status-${status}`,
        status === "soon" && "border-dashed border-indigo-300 bg-indigo-50/70 text-indigo-700",
        status === "preview" && "border-sky-200 bg-sky-50 text-sky-800",
        status === "live" && "border-emerald-200 bg-emerald-50 text-emerald-700",
        className,
      )}
    >
      {status === "live" && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" aria-hidden="true" />}
      {labels[status]}
    </span>
  );
}

export function statusLabel(status: Status): string {
  return labels[status];
}
