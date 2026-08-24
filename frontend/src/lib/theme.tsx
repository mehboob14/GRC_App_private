import { createContext, useContext } from "react";

/**
 * Light is the product default, and the operating system is never consulted.
 *
 * There was a third mode, `system`, which followed `prefers-color-scheme` and
 * was what an unset preference fell back to. That meant anyone whose laptop was
 * in dark mode saw a dark app on first visit, having never asked for one. The
 * mode is now a deliberate choice between two, and absence of a choice is light.
 */
export type ThemeMode = "light" | "dark";

/**
 * Dark mode is switched off product-wide for now: the sidebar toggle is hidden
 * and the app renders light regardless of any stored preference, so someone who
 * chose dark before is not stranded there with no way back.
 *
 * To restore it: flip this to `true` and re-enable the same flag in the
 * pre-paint script in index.html. Nothing else needs to change.
 */
export const DARK_MODE_ENABLED = false;

/** Read here and written by the provider; the pre-paint script in index.html
 *  reads the same key. */
export const STORAGE_KEY = "verity.theme";

export type ThemeContextValue = {
  /** The stored preference: light | dark | system. */
  mode: ThemeMode;
  /** What is actually applied after resolving `system`. */
  resolvedTheme: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  setAccent: (hex: string | null) => void;
};

export const ThemeContext = createContext<ThemeContextValue | null>(null);

export function readStoredMode(): ThemeMode {
  if (!DARK_MODE_ENABLED) return "light";
  try {
    // Only an explicit "dark" turns the lights off. An unset key, a stale
    // "system" value from before this changed, or unreadable storage all mean
    // light. Matches the pre-paint script in index.html.
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
