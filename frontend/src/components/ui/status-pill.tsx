import { cn } from "@/lib/cn";

type StatusTone = "pass" | "fail" | "review" | "na";

const toneClass: Record<StatusTone, string> = {
  pass: "bg-pass-bg text-pass-fg",
  fail: "bg-fail-bg text-fail-fg",
  review: "bg-review-bg text-review-fg",
  na: "bg-na-bg text-text-faint",
};

const dotClass: Record<StatusTone, string> = {
  pass: "bg-pass",
  fail: "bg-fail",
  review: "bg-review",
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
        "inline-flex h-[22px] items-center gap-1.5 rounded-md px-[7px] text-[12px] font-medium leading-4",
        toneClass[tone],
        className,
      )}
    >
      <span className={cn("size-[5px] rounded-full", dotClass[tone])} />
      {label}
    </span>
  );
}
