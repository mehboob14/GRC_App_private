import { useEffect, useState } from "react";

export const linkClass =
  "rounded-sm font-semibold text-text-link underline-offset-4 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent";

/** A quiet full width pill for the second action on a screen. */
export const secondaryPill =
  "flex h-11 w-full items-center justify-center gap-2 rounded-full border border-border bg-surface-primary text-label-md font-semibold text-text-primary transition-colors hover:bg-surface-hover focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-action-accent disabled:cursor-not-allowed disabled:opacity-60";

/** Seconds left on a resend cooldown, so nobody hammers "send again". */
export function useCooldown() {
  const [until, setUntil] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!until) return;
    const timer = window.setInterval(() => {
      const tick = Date.now();
      setNow(tick);
      if (tick >= until) window.clearInterval(timer);
    }, 250);
    return () => window.clearInterval(timer);
  }, [until]);
  return {
    left: Math.max(0, Math.ceil((until - now) / 1000)),
    start: (seconds: number) => {
      setNow(Date.now());
      setUntil(Date.now() + seconds * 1000);
    },
  };
}

/**
 * Recovery codes are minted as two groups of five joined by a hyphen. They are
 * shown with a space, and whatever separator someone types (space, hyphen,
 * none) is put back the way the server hashed it.
 */
export const displayRecoveryCode = (code: string) =>
  code.replace(/[^a-z0-9]+/gi, " ");

export function normalizeRecoveryCode(input: string): string {
  const compact = input.toLowerCase().replace(/[^a-z0-9]/g, "");
  return compact.length === 10
    ? `${compact.slice(0, 5)}-${compact.slice(5)}`
    : input.trim().toLowerCase();
}
