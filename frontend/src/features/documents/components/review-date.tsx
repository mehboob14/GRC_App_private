import { StatusPill } from "@/components/ui";
import { cn } from "@/lib/cn";
import { formatDay, REVIEW_PILL } from "../review";
import type { Document } from "../types";

/**
 * A document's next review: the date, and a pill when it is overdue or close. Colour
 * never carries the meaning alone, so the pill always says the word.
 */
export function ReviewDate({
  doc,
  large = false,
}: {
  doc: Pick<Document, "renewal_date" | "review_status">;
  /** The detail page's own type size, in place of the register's. */
  large?: boolean;
}) {
  if (!doc.renewal_date) {
    return (
      <span className={cn("text-text-subtle", large ? "text-body-md" : "text-body-sm")}>
        Not set
      </span>
    );
  }
  const pill = doc.review_status ? REVIEW_PILL[doc.review_status] : null;
  return (
    <span className="inline-flex flex-wrap items-center gap-x-2 gap-y-1">
      <span
        className={cn(
          "tabular",
          large ? "text-body-md text-text-primary" : "text-body-sm text-text-secondary",
        )}
      >
        {formatDay(doc.renewal_date, large ? "long" : "short")}
      </span>
      {pill ? <StatusPill status={pill.family} label={pill.label} /> : null}
    </span>
  );
}
