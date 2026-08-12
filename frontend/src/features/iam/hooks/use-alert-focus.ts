import { useEffect, useRef } from "react";

/**
 * DS §7.2 — a rejected submit shows a form-level alert block AND moves focus
 * to it. Attach the returned ref to an ErrorBanner; focus lands whenever
 * `active` flips true.
 */
export function useAlertFocus(active: boolean) {
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (active) ref.current?.focus();
  }, [active]);

  return ref;
}
