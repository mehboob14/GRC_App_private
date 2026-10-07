import { useCallback, useMemo } from "react";
import { useEntryState } from "@/lib/nav/entry-state";

export type SortDir = "asc" | "desc";

/** Value kinds a column can sort on. null/undefined always sort last. */
type SortValue = string | number | boolean | Date | null | undefined;

/**
 * Column sorting for the shared Table.
 *
 * `TH` has shipped `sortable`/`sorted`/`onSort`/`aria-sort` since it was
 * written and no register ever used them, so not one column header in the
 * product was clickable. This hook is the missing half: it owns the state, the
 * tri-state toggle and the comparator, so a register wires a column in one
 * line and every table sorts identically.
 *
 *   const { thProps, sortRows } = useTableSort<Row, "name" | "risk">("risk", {
 *     name: (r) => r.name,
 *     risk: (r) => r.risk_score,
 *   }, "desc");
 *
 * The sort comes back when a person returns to the page with Back (see
 * `useEntryState`). A page has one table to sort, so the state is named for that.
 *   ...
 *   <TH {...thProps("name")}>Name</TH>
 *   ...
 *   {sortRows(rows).map(...)}
 */
export function useTableSort<T, K extends string>(
  /**
   * Column to sort by before the user clicks anything. Pass null (the default)
   * to keep the order the server sent, which for most registers encodes real
   * ranking: audit events are newest first, vulnerabilities are risk-ranked,
   * tasks are SLA-ranked. Forcing an initial column silently discards that.
   */
  initialKey: K | null,
  accessors: Record<K, (row: T) => SortValue>,
  initialDir: SortDir = "asc",
) {
  const [key, setKey] = useEntryState<K | null>("table.sort", initialKey);
  const [dir, setDir] = useEntryState<SortDir>("table.sortDir", initialDir);

  // Not a side effect inside a setState updater: React invokes updaters twice
  // under StrictMode, which would toggle the direction twice per click.
  const onSort = useCallback(
    (next: K) => {
      if (next === key) {
        // The third click clears the column, so the order the server sent —
        // which for most registers here encodes real ranking — is reachable
        // again. Only for a register that started unsorted: one that named an
        // initial column meant it, and must not be toggleable into no order.
        if (dir === "desc" && initialKey === null) {
          setKey(null);
          setDir(initialDir);
          return;
        }
        setDir((d) => (d === "asc" ? "desc" : "asc"));
        return;
      }
      setKey(next);
      setDir("asc");
    },
    [key, dir, initialKey, initialDir, setKey, setDir],
  );

  /** Spread onto a TH to make that column sortable. */
  const thProps = useCallback(
    (column: K) => ({
      sortable: true,
      sorted: (key === column ? dir : false) as SortDir | false,
      onSort: () => onSort(column),
    }),
    [key, dir, onSort],
  );

  // A remembered column this build no longer sorts on is ignored, not called.
  const accessor = key === null ? null : (accessors[key] ?? null);
  const sortRows = useCallback(
    (rows: readonly T[]): T[] => {
      // Untouched: hand back the server's order rather than imposing one.
      if (accessor === null) return [...rows];
      const factor = dir === "asc" ? 1 : -1;
      // Decorate with the original index so equal values keep source order:
      // Array.prototype.sort is only stable within a single comparison pass and
      // we compare through an accessor that may collapse distinct rows.
      return rows
        .map((row, index) => ({ row, index }))
        .sort((a, b) => {
          const cmp = compare(accessor(a.row), accessor(b.row));
          return cmp !== 0 ? cmp * factor : a.index - b.index;
        })
        .map((d) => d.row);
    },
    [accessor, dir],
  );

  return useMemo(
    () => ({ key, dir, thProps, sortRows }),
    [key, dir, thProps, sortRows],
  );
}

function compare(a: SortValue, b: SortValue): number {
  // Empty values sort last in BOTH directions, so flipping a column never
  // fills the first screen with blanks.
  const aEmpty = a === null || a === undefined || a === "";
  const bEmpty = b === null || b === undefined || b === "";
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;

  if (a instanceof Date || b instanceof Date) {
    return Number(a instanceof Date ? a : new Date(String(a))) -
      Number(b instanceof Date ? b : new Date(String(b)));
  }
  if (typeof a === "number" && typeof b === "number") return a - b;
  if (typeof a === "boolean" && typeof b === "boolean") return Number(a) - Number(b);
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: "base" });
}
