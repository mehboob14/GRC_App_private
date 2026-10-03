import type { Config } from "tailwindcss";

/** Colours resolve to CSS variables so the docs dark theme can swap them in one place. */
const token = (name: string) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./content/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: token("canvas"),
        surface: token("surface"),
        subtle: token("subtle"),
        muted: token("muted-bg"),
        ink: token("ink"),
        body: token("body"),
        dim: token("dim"),
        faint: token("faint"),
        line: token("line"),
        "line-strong": token("line-strong"),
        accent: token("accent"),
        "accent-strong": token("accent-strong"),
        "accent-soft": token("accent-soft"),
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "Segoe UI", "Arial", "sans-serif"],
        serif: ["'Source Serif 4 Variable'", "Georgia", "'Times New Roman'", "serif"],
        mono: ["'JetBrains Mono Variable'", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      fontSize: {
        "display-xl": ["clamp(2.75rem, 1.6rem + 4.6vw, 4.75rem)", { lineHeight: "1.03", letterSpacing: "-0.022em" }],
        "display-lg": ["clamp(2.25rem, 1.5rem + 3vw, 3.4rem)", { lineHeight: "1.08", letterSpacing: "-0.018em" }],
        "display-md": ["clamp(1.85rem, 1.4rem + 1.8vw, 2.6rem)", { lineHeight: "1.12", letterSpacing: "-0.014em" }],
        "display-sm": ["clamp(1.5rem, 1.25rem + 1vw, 1.95rem)", { lineHeight: "1.18", letterSpacing: "-0.01em" }],
        eyebrow: ["0.75rem", { lineHeight: "1rem", letterSpacing: "0.14em" }],
      },
      maxWidth: { frame: "80rem", prose: "47.5rem" },
      boxShadow: {
        card: "0 1px 2px rgb(16 24 40 / 0.04), 0 8px 24px -6px rgb(16 24 40 / 0.08)",
        float: "0 2px 4px rgb(16 24 40 / 0.04), 0 24px 56px -12px rgb(16 24 40 / 0.18)",
        menu: "0 1px 2px rgb(16 24 40 / 0.05), 0 28px 64px -16px rgb(16 24 40 / 0.22)",
        focus: "0 0 0 3px rgb(var(--accent) / 0.35)",
      },
      borderRadius: { card: "0.875rem" },
      transitionTimingFunction: { out: "cubic-bezier(0.16, 1, 0.3, 1)" },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "pop-in": { from: { opacity: "0", transform: "translateY(6px) scale(0.98)" }, to: { opacity: "1", transform: "none" } },
        "slide-in-end": { from: { transform: "translateX(100%)" }, to: { transform: "none" } },
        "slide-in-start": { from: { transform: "translateX(-100%)" }, to: { transform: "none" } },
      },
      animation: {
        "fade-in": "fade-in 180ms ease-out both",
        "pop-in": "pop-in 220ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "slide-in-end": "slide-in-end 280ms cubic-bezier(0.16, 1, 0.3, 1) both",
        "slide-in-start": "slide-in-start 260ms cubic-bezier(0.16, 1, 0.3, 1) both",
      },
    },
  },
  plugins: [],
} satisfies Config;
