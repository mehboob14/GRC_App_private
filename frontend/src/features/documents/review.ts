import type { StatusFamily } from "@/components/ui/status-pill";
import type { ReviewStatus } from "./types";

/**
 * The pill beside a review date. The server decides which one applies, because it
 * owns the clock the daily reminders run on: the register, the detail page, the
 * dashboard count and the owner's notification then always agree.
 */
export const REVIEW_PILL: Record<ReviewStatus, { label: string; family: StatusFamily }> = {
  overdue: { label: "Overdue", family: "danger" },
  due_soon: { label: "Due soon", family: "warning" },
};

/**
 * Today as the YYYY-MM-DD a date input holds, on the server's calendar. The server
 * refuses a review date before its own (UTC) today, so the picker never offers one
 * it would turn down, whatever timezone the reader is in.
 */
export function todayInputValue(): string {
  return new Date().toISOString().slice(0, 10);
}

/**
 * A review or due date in words. It names a day, not a moment, so it is read as the UTC
 * day it was stored as: parsed as midnight UTC and shown in a western timezone it
 * would land on the day before.
 */
export function formatDay(value: string, style: "short" | "long" = "short"): string {
  return new Date(value).toLocaleDateString(undefined, {
    timeZone: "UTC",
    year: "numeric",
    month: style === "long" ? "long" : "short",
    day: style === "long" ? "numeric" : "2-digit",
  });
}
