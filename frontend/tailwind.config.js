/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "rgb(var(--color-bg) / <alpha-value>)",
        "bg-elevated": "rgb(var(--color-bg-elevated) / <alpha-value>)",
        "bg-sunken": "rgb(var(--color-bg-sunken) / <alpha-value>)",
        "accent-tint": "rgb(var(--color-accent-tint) / <alpha-value>)",
        "na-bg": "rgb(var(--color-na-bg) / <alpha-value>)",
        border: {
          DEFAULT: "rgb(var(--color-border) / <alpha-value>)",
          strong: "rgb(var(--color-border-strong) / <alpha-value>)",
        },
        text: {
          DEFAULT: "rgb(var(--color-text) / <alpha-value>)",
          muted: "rgb(var(--color-text-muted) / <alpha-value>)",
          faint: "rgb(var(--color-text-faint) / <alpha-value>)",
          inverse: "rgb(var(--color-text-inverse) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--color-accent) / <alpha-value>)",
          fg: "rgb(var(--color-accent-fg) / <alpha-value>)",
        },
        pass: {
          DEFAULT: "rgb(var(--color-pass) / <alpha-value>)",
          fg: "rgb(var(--color-pass-fg) / <alpha-value>)",
          bg: "rgb(var(--color-pass-bg) / <alpha-value>)",
        },
        fail: {
          DEFAULT: "rgb(var(--color-fail) / <alpha-value>)",
          fg: "rgb(var(--color-fail-fg) / <alpha-value>)",
          bg: "rgb(var(--color-fail-bg) / <alpha-value>)",
          border: "rgb(var(--color-fail-border) / <alpha-value>)",
        },
        review: {
          DEFAULT: "rgb(var(--color-review) / <alpha-value>)",
          fg: "rgb(var(--color-review-fg) / <alpha-value>)",
          bg: "rgb(var(--color-review-bg) / <alpha-value>)",
        },
        pending: "rgb(var(--color-pending) / <alpha-value>)",
        "critical-fg": "rgb(var(--color-critical-fg) / <alpha-value>)",
        identity: {
          1: "rgb(var(--color-identity-1) / <alpha-value>)",
          2: "rgb(var(--color-identity-2) / <alpha-value>)",
          3: "rgb(var(--color-identity-3) / <alpha-value>)",
          4: "rgb(var(--color-identity-4) / <alpha-value>)",
          5: "rgb(var(--color-identity-5) / <alpha-value>)",
          6: "rgb(var(--color-identity-6) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Sora", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      fontSize: {
        "display-hero": ["3.25rem", { lineHeight: "3.25rem", fontWeight: "800" }],
        "display-xl": ["2rem", { lineHeight: "2.375rem", fontWeight: "800" }],
        "heading-xl": ["1.75rem", { lineHeight: "2.125rem", fontWeight: "800" }],
        "heading-lg": ["1.5rem", { lineHeight: "1.875rem", fontWeight: "800" }],
        "heading-md": ["1.25rem", { lineHeight: "1.625rem", fontWeight: "800" }],
        "heading-sm": ["1.125rem", { lineHeight: "1.5rem", fontWeight: "700" }],
        "title-md": ["0.875rem", { lineHeight: "1.25rem", fontWeight: "700" }],
        "title-sm": ["0.8125rem", { lineHeight: "1.125rem", fontWeight: "700" }],
        "body-lg": ["0.875rem", { lineHeight: "1.375rem", fontWeight: "400" }],
        "body-md": ["0.8125rem", { lineHeight: "1.25rem", fontWeight: "400" }],
        "body-sm": ["0.75rem", { lineHeight: "1.0625rem", fontWeight: "400" }],
        "label-md": ["0.8125rem", { lineHeight: "1rem", fontWeight: "600" }],
        "label-sm": ["0.75rem", { lineHeight: "0.9375rem", fontWeight: "600" }],
        caption: ["0.6875rem", { lineHeight: "0.9375rem", fontWeight: "400" }],
        overline: [
          "0.625rem",
          { lineHeight: "0.875rem", fontWeight: "700", letterSpacing: "0.05em" },
        ],
        "code-chip": ["0.75rem", { lineHeight: "1rem", fontWeight: "700" }],
        "numeral-lg": ["1.5rem", { lineHeight: "1.75rem", fontWeight: "800" }],
        "numeral-md": ["1.125rem", { lineHeight: "1.375rem", fontWeight: "800" }],
        "numeral-sm": ["0.875rem", { lineHeight: "1.125rem", fontWeight: "800" }],
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        mark: "var(--shadow-mark)",
      },
      spacing: {
        rail: "3rem",
        sidebar: "15rem",
        topbar: "3.5rem",
      },
      outlineOffset: {
        focus: "2px",
      },
    },
  },
  plugins: [],
};
