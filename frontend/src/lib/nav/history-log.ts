/**
 * Where this tab has been, by position in the browser's history.
 *
 * "Back to controls" on a detail page used to be a link to the controls list, so
 * a person who had opened it from somewhere else (an evidence item, a risk) was
 * sent to the wrong place, and one who came from a filtered list lost the filter.
 * The router stores each entry's position (`history.state.idx`) but not what the
 * entry before it was; this remembers that, so a back link can say where it
 * really goes and take the browser there.
 */
const seen = new Map<number, string>();

/** Where the browser is in this tab's history: 0 for the first page, one more for each page after. */
export function entryIndex(): number {
  const state = window.history.state as { idx?: number } | null;
  return typeof state?.idx === "number" ? state.idx : 0;
}

/** Note that the entry the browser is on now shows this path. */
export function recordEntry(path: string): void {
  seen.set(entryIndex(), path);
}

/** The page just before this one in the history, if this tab saw it. */
export function previousEntry(): string | null {
  const idx = entryIndex();
  return idx > 0 ? (seen.get(idx - 1) ?? null) : null;
}
