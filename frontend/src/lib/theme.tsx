import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  type ReactNode,
} from "react";
import { hexToRgbChannels } from "@/lib/color";

/**
 * Accent-only theme. Figma ships white/light mode only — no dark theme.
 */
type ThemeContextValue = {
  setAccent: (hex: string | null) => void;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  useEffect(() => {
    document.documentElement.classList.remove("dark");
    window.localStorage.removeItem("verity.theme");
  }, []);

  const setAccent = useCallback((hex: string | null) => {
    if (!hex) {
      document.documentElement.style.removeProperty("--color-accent");
      return;
    }
    document.documentElement.style.setProperty(
      "--color-accent",
      hexToRgbChannels(hex),
    );
  }, []);

  const value = useMemo(() => ({ setAccent }), [setAccent]);

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
