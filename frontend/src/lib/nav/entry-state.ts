import { useEffect, useRef, useState, type Dispatch, type SetStateAction } from "react";
import { useLocation } from "react-router-dom";

/**
 * Screen state that belongs to one entry in the browser's history.
 *
 * A register's filters, search, sort and page, and a detail page's open tab, are
 * React state, so leaving the page threw them away: open a control from a filtered
 * list, press Back, and the list was the whole library again. Keeping them against
 * the history entry (the router's `location.key`) is how a browser treats scroll:
 * Back and Forward return to exactly what that entry showed, while a fresh visit
 * (the sidebar, a link) is a new entry and starts clean. A reload keeps the entry,
 * so it keeps the state too.
 *
 * sessionStorage only, so it ends with the tab and `clearSession` empties it on
 * sign-out. JSON values only: no Date, Set or Map.
 */

const STORAGE_KEY = "verity.ui.entries";
/**
 * The first page of every document load has the router key "default", and
 * sessionStorage outlives the load. Left alone, a tab that began on /controls and
 * later had /controls?system=github typed into its address bar would restore the old
 * filters over the link. Scoping that one key to the load keeps Back to the first
 * page working within a visit and gives a new visit a clean start.
 */
const LOAD = String(Math.round(performance.timeOrigin));
const entryId = (key: string) => (key === "default" ? `default@${LOAD}` : key);
/** Entries remembered at once. Old ones are dropped, oldest first. */
const MAX_ENTRIES = 80;

type Store = Record<string, Record<string, unknown>>;

let cache: Store | null = null;
let flush: number | undefined;

function store(): Store {
  if (cache) return cache;
  try {
    cache = JSON.parse(sessionStorage.getItem(STORAGE_KEY) ?? "{}") as Store;
  } catch {
    cache = {};
  }
  return cache;
}

function save(): void {
  window.clearTimeout(flush);
  flush = window.setTimeout(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(cache));
    } catch {
      // Private mode and blocked storage both throw: remembering is best effort.
    }
  }, 150);
}

function remember(entry: string, name: string, value: unknown): void {
  const all = store();
  const kept = all[entry] ?? {};
  // Re-inserting keeps the keys in order of use, so trimming drops the stalest.
  delete all[entry];
  all[entry] = { ...kept, [name]: value };
  const keys = Object.keys(all);
  for (const stale of keys.slice(0, Math.max(0, keys.length - MAX_ENTRIES))) {
    delete all[stale];
  }
  save();
}

function forget(entry: string, name: string): void {
  const kept = store()[entry];
  if (!kept || !(name in kept)) return;
  delete kept[name];
  if (Object.keys(kept).length === 0) delete store()[entry];
  save();
}

const isPlainObject = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

/** Forget everything remembered. Called when the session ends or changes. */
export function forgetEntryState(): void {
  cache = {};
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // Nothing to clear if storage is blocked.
  }
}

/**
 * `useState` that comes back as it was when this history entry is revisited.
 *
 * Pass `null` as the name to opt out (the hook still runs, so a caller can decide
 * at render time without breaking the rules of hooks). Names are scoped to the
 * entry, so "search" on two pages cannot collide; give each state its own.
 */
export function useEntryState<T>(
  name: string | null,
  initial: T | (() => T),
): [T, Dispatch<SetStateAction<T>>] {
  const entry = entryId(useLocation().key);
  const [value, setValue] = useState<T>(() => {
    const start = typeof initial === "function" ? (initial as () => T)() : initial;
    const kept = name === null ? undefined : (store()[entry]?.[name] as T | undefined);
    if (kept === undefined) return start;
    // An object saved by an older build may lack a field this build added: what is
    // missing comes from the starting value, so the page never reads an absent field.
    return isPlainObject(start) && isPlainObject(kept) ? ({ ...start, ...kept } as T) : kept;
  });
  // A `replace` navigation (a search typed into the address bar's query) gives the same
  // page a new key each time. The old entry is gone from the history, so its copy goes
  // too, instead of piling up and pushing the entries Back can still reach out.
  const savedUnder = useRef(entry);
  useEffect(() => {
    if (name === null) return;
    if (savedUnder.current !== entry) {
      forget(savedUnder.current, name);
      savedUnder.current = entry;
    }
    remember(entry, name, value);
  }, [entry, name, value]);
  return [value, setValue];
}
