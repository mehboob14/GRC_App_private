import { useCallback, useEffect, useMemo, useState } from "react";

export type ColumnDef<K extends string> = { key: K; label: string };

/**
 * Which columns a register shows, remembered per browser.
 *
 * Two modules had grown byte-identical copies of this: the same TOGGLEABLE_COLUMNS
 * array, the same ColKey type, the same localStorage load/save pair, the same
 * hiddenCount maths and the same dropdown. Every other register had no picker at
 * all, so the same table was configurable in one module and fixed in the next.
 *
 * The identity column (Title, Control, Name) and the structural ones (selection
 * checkbox, row actions) are never toggleable: hiding them would leave a row you
 * cannot identify or act on. Pass only the optional columns.
 *
 *   const cols = useColumnPrefs("verity.assets.columns", ASSET_COLUMNS, ["value"]);
 *   <ColumnPicker {...cols} />
 *   {cols.isVisible("owner") ? <TH>Owner</TH> : null}
 */
export function useColumnPrefs<K extends string>(
  /** Stable per register, e.g. "verity.assets.columns". */
  storageKey: string,
  columns: readonly ColumnDef<K>[],
  /** Columns off by default. Everything else starts visible. */
  defaultHidden: readonly K[] = [],
) {
  const hiddenSignature = defaultHidden.join(",");
  const defaults = useMemo(
    () =>
      Object.fromEntries(
        columns.map((c) => [c.key, !hiddenSignature.split(",").includes(c.key)]),
      ) as Record<K, boolean>,
    [columns, hiddenSignature],
  );

  const [visible, setVisible] = useState<Record<K, boolean>>(() => {
    // A stored preference may predate a column being added or removed, so start
    // from today's defaults and only take keys we still know about.
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return defaults;
      const saved = JSON.parse(raw) as Partial<Record<K, boolean>>;
      const merged = { ...defaults };
      for (const { key } of columns) {
        if (typeof saved[key] === "boolean") merged[key] = saved[key] as boolean;
      }
      return merged;
    } catch {
      return defaults;
    }
  });

  useEffect(() => {
    // Private mode and blocked site data both throw here; a lost preference must
    // never take the register down with it.
    try {
      localStorage.setItem(storageKey, JSON.stringify(visible));
    } catch {
      /* preference is best effort */
    }
  }, [storageKey, visible]);

  const toggle = useCallback(
    (key: K, next: boolean) => setVisible((prev) => ({ ...prev, [key]: next })),
    [],
  );
  const reset = useCallback(() => setVisible(defaults), [defaults]);
  const isVisible = useCallback((key: K) => visible[key] !== false, [visible]);
  const hiddenCount = columns.filter((c) => !visible[c.key]).length;

  return { columns, visible, toggle, reset, isVisible, hiddenCount };
}
