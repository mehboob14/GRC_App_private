/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          canvas: "rgb(var(--color-surface-canvas) / <alpha-value>)",
          page: "rgb(var(--color-surface-page) / <alpha-value>)",
          primary: "rgb(var(--color-surface-primary) / <alpha-value>)",
          sunken: "rgb(var(--color-surface-sunken) / <alpha-value>)",
          hover: "rgb(var(--color-surface-hover) / <alpha-value>)",
          inverse: "rgb(var(--color-surface-inverse) / <alpha-value>)",
        },
        border: {
          DEFAULT: "rgb(var(--color-border-default) / <alpha-value>)",
          strong: "rgb(var(--color-border-strong) / <alpha-value>)",
        },
        text: {
          primary: "rgb(var(--color-text-primary) / <alpha-value>)",
          secondary: "rgb(var(--color-text-secondary) / <alpha-value>)",
          subtle: "rgb(var(--color-text-subtle) / <alpha-value>)",
          faint: "rgb(var(--color-text-faint) / <alpha-value>)",
          link: "rgb(var(--color-text-link) / <alpha-value>)",
          inverse: "rgb(var(--color-text-inverse) / <alpha-value>)",
        },
        action: {
          primary: {
            DEFAULT: "rgb(var(--color-action-primary) / <alpha-value>)",
            hover: "rgb(var(--color-action-primary-hover) / <alpha-value>)",
            fg: "rgb(var(--color-action-primary-fg) / <alpha-value>)",
          },
          accent: {
            DEFAULT: "rgb(var(--color-action-accent) / <alpha-value>)",
            tint: "rgb(var(--color-action-accent-tint) / <alpha-value>)",
            border: "rgb(var(--color-action-accent-border) / <alpha-value>)",
          },
          danger: {
            DEFAULT: "rgb(var(--color-action-danger) / <alpha-value>)",
            hover: "rgb(var(--color-action-danger-hover) / <alpha-value>)",
            fg: "rgb(var(--color-action-danger-fg) / <alpha-value>)",
            tint: "rgb(var(--color-action-danger-tint) / <alpha-value>)",
          },
        },
        status: {
          success: {
            base: "rgb(var(--color-status-success-base) / <alpha-value>)",
            text: "rgb(var(--color-status-success-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-success-bg) / <alpha-value>)",
            border: "rgb(var(--color-status-success-border) / <alpha-value>)",
          },
          danger: {
            base: "rgb(var(--color-status-danger-base) / <alpha-value>)",
            text: "rgb(var(--color-status-danger-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-danger-bg) / <alpha-value>)",
            border: "rgb(var(--color-status-danger-border) / <alpha-value>)",
          },
          warning: {
            base: "rgb(var(--color-status-warning-base) / <alpha-value>)",
            text: "rgb(var(--color-status-warning-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-warning-bg) / <alpha-value>)",
            border: "rgb(var(--color-status-warning-border) / <alpha-value>)",
          },
          progress: {
            base: "rgb(var(--color-status-progress-base) / <alpha-value>)",
            text: "rgb(var(--color-status-progress-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-progress-bg) / <alpha-value>)",
          },
          pending: {
            base: "rgb(var(--color-status-pending-base) / <alpha-value>)",
            text: "rgb(var(--color-status-pending-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-pending-bg) / <alpha-value>)",
          },
          neutral: {
            base: "rgb(var(--color-status-neutral-base) / <alpha-value>)",
            text: "rgb(var(--color-status-neutral-text) / <alpha-value>)",
            bg: "rgb(var(--color-status-neutral-bg) / <alpha-value>)",
          },
        },
        severity: {
          critical: "rgb(var(--color-severity-critical) / <alpha-value>)",
          high: "rgb(var(--color-severity-high) / <alpha-value>)",
          medium: "rgb(var(--color-severity-medium) / <alpha-value>)",
          low: "rgb(var(--color-severity-low) / <alpha-value>)",
        },
        identity: {
          1: "rgb(var(--color-identity-1) / <alpha-value>)",
          2: "rgb(var(--color-identity-2) / <alpha-value>)",
          3: "rgb(var(--color-identity-3) / <alpha-value>)",
          4: "rgb(var(--color-identity-4) / <alpha-value>)",
          5: "rgb(var(--color-identity-5) / <alpha-value>)",
          6: "rgb(var(--color-identity-6) / <alpha-value>)",
        },
        // Auth marketing panel one-offs — see tokens.css for why these exist.
        panel: {
          1: "rgb(var(--color-panel-1) / <alpha-value>)",
          2: "rgb(var(--color-panel-2) / <alpha-value>)",
          3: "rgb(var(--color-panel-3) / <alpha-value>)",
          glow: "rgb(var(--color-panel-glow) / <alpha-value>)",
          accent: "rgb(var(--color-panel-accent) / <alpha-value>)",
          edge: "rgb(var(--color-panel-edge) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Sora", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      // DS §3.2 — the closed type ramp (F3). 15 core + 4 specialised.
      // Sora styles must be paired with `font-display` at the call site.
      fontSize: {
        "display-hero": [
          "3.25rem",
          { lineHeight: "3.25rem", fontWeight: "800", letterSpacing: "-1.56px" },
        ],
        "display-xl": [
          "2rem",
          { lineHeight: "2.375rem", fontWeight: "800", letterSpacing: "-0.8px" },
        ],
        "heading-xl": [
          "1.75rem",
          { lineHeight: "2.125rem", fontWeight: "800", letterSpacing: "-0.7px" },
        ],
        "heading-lg": [
          "1.5rem",
          { lineHeight: "1.875rem", fontWeight: "800", letterSpacing: "-0.48px" },
        ],
        "heading-md": [
          "1.25rem",
          { lineHeight: "1.625rem", fontWeight: "800", letterSpacing: "-0.4px" },
        ],
        "heading-sm": [
          "1.125rem",
          { lineHeight: "1.5rem", fontWeight: "700", letterSpacing: "-0.18px" },
        ],
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
        "numeral-lg": [
          "1.75rem",
          { lineHeight: "2rem", fontWeight: "800", letterSpacing: "-0.56px" },
        ],
        "numeral-md": [
          "1.5rem",
          { lineHeight: "1.75rem", fontWeight: "800", letterSpacing: "-0.48px" },
        ],
        "numeral-sm": [
          "1.25rem",
          { lineHeight: "1.5rem", fontWeight: "800", letterSpacing: "-0.2px" },
        ],
      },
      // DS §4.2 — closed radius scale (F4)
      borderRadius: {
        "2xs": "var(--radius-2xs)",
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      borderWidth: {
        1.5: "1.5px",
        3: "3px",
        4.5: "4.5px", // selected radio ring (§5.5)
      },
      // DS §4.4 — plus input focus/error rings (§5.4) and toast shadow (§7.2)
      boxShadow: {
        1: "var(--shadow-1)",
        2: "var(--shadow-2)",
        3: "var(--shadow-3)",
        4: "var(--shadow-4)",
        toast: "var(--shadow-toast)",
        "input-focus": "var(--ring-input-focus)",
        "input-error": "var(--ring-input-error)",
      },
      // DS §4.7 — layer scale
      zIndex: {
        "sticky-table": "100",
        "sticky-page": "200",
        dropdown: "1000",
        "bulk-bar": "1100",
        drawer: "1200",
        modal: "1300",
        palette: "1350",
        toast: "1400",
        tooltip: "1500",
      },
      // DS §4.1 space scale maps 1:1 onto Tailwind defaults (0.5=2 … 16=64,
      // including the in-component-only 2/6 exceptions at 0.5/1.5); only
      // layout constants are added here.
      spacing: {
        rail: "3rem",
        sidebar: "15rem",
        topbar: "3.5rem",
      },
      // DS §7.6 motion
      transitionDuration: {
        80: "80ms",
        250: "250ms",
      },
      transitionTimingFunction: {
        state: "var(--ease-state)",
        enter: "var(--ease-enter)",
      },
      outlineOffset: {
        focus: "2px",
      },
    },
  },
  plugins: [],
};
