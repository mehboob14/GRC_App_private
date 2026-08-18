import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { hexToRgbChannels, mixHexChannels } from "@/lib/color";

/**
 * Light is the product default, and the operating system is never consulted.
 *
 * There was a third mode, `system`, which followed `prefers-color-scheme` and
 * was what an unset preference fell back to. That meant anyone whose laptop was
 * in dark mode saw a dark app on first visit, having never asked for one. The
 * mode is now a deliberate choice between two, and absence of a choice is light.
 */
export type ThemeMode = "light" | "dark";

const STORAGE_KEY = "verity.theme";
const ACCENT_STYLE_ID = "verity-tenant-accent";
const DARK_PAGE = "#0F1622"; // dark surface-page — mix target for dark tints

type ThemeContextValue = {
  /** The stored preference: light | dark | system. */
  mode: ThemeMode;
  /** What is actually applied after resolving `system`. */
  resolvedTheme: "light" | "dark";
  setMode: (mode: ThemeMode) => void;
  setAccent: (hex: string | null) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredMode(): ThemeMode {
  try {
    // Only an explicit "dark" turns the lights off. An unset key, a stale
    // "system" value from before this changed, or unreadable storage all mean
    // light. Matches the pre-paint script in index.html.
    return window.localStorage.getItem(STORAGE_KEY) === "dark" ? "dark" : "light";
  } catch {
    return "light";
  }
}

/**
 * Theme + white-label accent provider.
 *
 * The mode is persisted in localStorage under `verity.theme`; an inline
 * script in index.html reads the same key before first paint so there is no
 * light flash. `.dark` on <html> switches the token set in tokens.css, which
 * also keeps `color-scheme` in sync.
 *
 * Tenant accent (`setAccent`) overrides exactly these tokens, in both
 * themes: --color-action-primary (+ -hover), --color-action-accent
 * (+ -tint, -border) and --color-text-link. The -fg tokens are not touched —
 * label colours stay theme-controlled. Hover shades follow the DS rule:
 * darken in light, lighten in dark.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>(readStoredMode);

  // The stored mode is now the applied mode: there is nothing left to resolve
  // against, since the OS is not consulted. Kept as a distinct name because it
  // is part of the context contract that consumers already read.
  const resolvedTheme: "light" | "dark" = mode;

  useEffect(() => {
    document.documentElement.classList.toggle("dark", resolvedTheme === "dark");
  }, [resolvedTheme]);

  const setMode = useCallback((next: ThemeMode) => {
    setModeState(next);
    try {
      window.localStorage.setItem(STORAGE_KEY, next);
    } catch {
      // Private-mode storage failures degrade to session-only preference.
    }
  }, []);

  const setAccent = useCallback((hex: string | null) => {
    const existing = document.getElementById(ACCENT_STYLE_ID);
    if (!hex) {
      existing?.remove();
      return;
    }
    // A <style> element (not inline style) so the .dark overrides still win
    // by specificity when the theme flips.
    const accent = hexToRgbChannels(hex);
    const style = existing ?? document.createElement("style");
    style.id = ACCENT_STYLE_ID;
    style.textContent = [
      ":root {",
      `  --color-action-primary: ${accent};`,
      `  --color-action-primary-hover: ${mixHexChannels(hex, "#000000", 0.18)};`,
      `  --color-action-accent: ${accent};`,
      `  --color-action-accent-tint: ${mixHexChannels(hex, "#FFFFFF", 0.9)};`,
      `  --color-action-accent-border: ${mixHexChannels(hex, "#FFFFFF", 0.75)};`,
      `  --color-text-link: ${accent};`,
      "}",
      ".dark {",
      `  --color-action-primary: ${mixHexChannels(hex, "#FFFFFF", 0.3)};`,
      `  --color-action-primary-hover: ${mixHexChannels(hex, "#FFFFFF", 0.45)};`,
      `  --color-action-accent: ${mixHexChannels(hex, "#FFFFFF", 0.3)};`,
      `  --color-action-accent-tint: ${mixHexChannels(hex, DARK_PAGE, 0.82)};`,
      `  --color-action-accent-border: ${mixHexChannels(hex, DARK_PAGE, 0.6)};`,
      `  --color-text-link: ${mixHexChannels(hex, "#FFFFFF", 0.3)};`,
      "}",
    ].join("\n");
    if (!existing) {
      document.head.appendChild(style);
    }
  }, []);

  const value = useMemo(
    () => ({ mode, resolvedTheme, setMode, setAccent }),
    [mode, resolvedTheme, setMode, setAccent],
  );

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within ThemeProvider");
  }
  return ctx;
}
