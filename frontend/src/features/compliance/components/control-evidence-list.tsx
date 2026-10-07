import { useState } from "react";
import { Link } from "react-router-dom";
import { Icon, StatusPill } from "@/components/ui";
import type { Evidence, EvidenceFreshness } from "@/lib/api/types";

const FRESHNESS: Record<
  EvidenceFreshness,
  { label: string; family: "success" | "warning" | "danger" | "neutral" }
> = {
  current: { label: "Current", family: "success" },
  aging: { label: "Aging", family: "warning" },
  stale: { label: "Stale", family: "danger" },
  no_expiry: { label: "No expiry", family: "neutral" },
};

/** A connector files its results again each time they change. Titles carry the
 *  moment (`, 6 Oct 2026 14:05 UTC`); older ones do not. */
const FILED_AT = /,\s\d{1,2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2} UTC$/;

const filedByConnector = (item: Evidence) =>
  Boolean(item.source_label?.endsWith(" connector"));

/** The same results filed on other days read as one item with a history, not as
 *  copies. The list arrives newest first, so the first of a group is the latest. */
function grouped(items: Evidence[]): { latest: Evidence; earlier: Evidence[] }[] {
  const groups = new Map<string, Evidence[]>();
  for (const item of items) {
    const key = filedByConnector(item)
      ? `${item.source_label}|${item.title.replace(FILED_AT, "")}`
      : item.id;
    groups.set(key, [...(groups.get(key) ?? []), item]);
  }
  return [...groups.values()].map(([latest, ...earlier]) => ({ latest, earlier }));
}

/** `collected_at` is a day, so it is read at noon to stay on that day in any zone. */
function day(iso: string): string {
  const date = new Date(iso.length === 10 ? `${iso}T12:00:00` : iso);
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
}

/** What the file says, in a line: for a connector, what it found. */
function detail(item: Evidence): string {
  const parts = [item.source_label ?? item.evidence_type.replace(/_/g, " "), day(item.collected_at)];
  if (filedByConnector(item) && item.description) {
    parts.push(item.description.split(". ")[0].replace(/\.$/, ""));
  }
  return parts.join(" · ");
}

function Row({ item, small = false }: { item: Evidence; small?: boolean }) {
  const freshness = FRESHNESS[item.freshness];
  return (
    <Link
      to={`/evidence/${item.id}`}
      className="flex items-center gap-3 rounded-sm py-2.5 hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-accent"
    >
      <Icon
        name={item.kind === "file" ? "doc" : "globe"}
        className="size-4 shrink-0 text-text-subtle"
        aria-hidden
      />
      <span className="min-w-0 flex-1">
        <span
          className={`block truncate text-text-primary ${small ? "text-body-sm" : "text-body-md"}`}
        >
          {item.title}
        </span>
        <span className="block truncate text-caption text-text-subtle">{detail(item)}</span>
      </span>
      <StatusPill kind="inline" status={freshness.family} label={freshness.label} />
      <Icon name="chevr" className="size-4 shrink-0 text-text-faint" aria-hidden />
    </Link>
  );
}

/**
 * The evidence on a control, each a way into the item itself. What a connector
 * keeps filing is folded under its latest, with the earlier results a click away.
 */
export function ControlEvidenceList({
  items,
  limit,
}: {
  items: Evidence[];
  /** Show only this many items (or groups of them), as the overview does. */
  limit?: number;
}) {
  const [open, setOpen] = useState<string[]>([]);
  const groups = grouped(items).slice(0, limit);
  return (
    <ul className="divide-y divide-border">
      {groups.map(({ latest, earlier }) => (
        <li key={latest.id}>
          <Row item={latest} />
          {earlier.length > 0 ? (
            <>
              <button
                type="button"
                aria-expanded={open.includes(latest.id)}
                onClick={() =>
                  setOpen((now) =>
                    now.includes(latest.id)
                      ? now.filter((id) => id !== latest.id)
                      : [...now, latest.id],
                  )
                }
                className="mb-2.5 ml-7 inline-flex items-center gap-1 text-caption font-semibold text-action-accent hover:underline"
              >
                <Icon
                  name="chevr"
                  className={`size-3.5 transition-transform ${open.includes(latest.id) ? "rotate-90" : ""}`}
                  aria-hidden
                />
                {earlier.length} earlier {earlier.length === 1 ? "result" : "results"}
              </button>
              {open.includes(latest.id) ? (
                <ul className="mb-2 ml-7 divide-y divide-border border-l border-border pl-3">
                  {earlier.map((item) => (
                    <li key={item.id}>
                      <Row item={item} small />
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
        </li>
      ))}
    </ul>
  );
}
