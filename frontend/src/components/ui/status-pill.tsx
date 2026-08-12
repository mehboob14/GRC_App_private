import { cn } from "@/lib/cn";

type StatusTone = "pass" | "fail" | "review" | "na";

const toneClass: Record<StatusTone, string> = {
  pass: "bg-status-success-bg text-status-success-text",
  fail: "bg-status-danger-bg text-status-danger-text",
  review: "bg-status-warning-bg text-status-warning-text",
  na: "bg-status-neutral-bg text-text-subtle",
};

const dotClass: Record<StatusTone, string> = {
  pass: "bg-status-success-base",
  fail: "bg-status-danger-base",
  review: "bg-status-warning-base",
  na: "bg-text-faint",
};

export function StatusPill({
  label,
  tone,
  className,
}: {
  label: string;
  tone: StatusTone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-[22px] items-center gap-1.5 rounded-sm px-[7px] text-[12px] font-medium leading-4",
        toneClass[tone],
        className,
      )}
    >
      <span className={cn("size-[5px] rounded-full", dotClass[tone])} />
      {label}
    </span>
  );
}
