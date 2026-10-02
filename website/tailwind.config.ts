import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#101828",
        muted: "#475467",
        sky: "#0369a1",
        night: "#10213b",
        mist: "#eef5fa",
        line: "#dfe7ed",
      },
      fontFamily: {
        sans: ["Inter", "Arial", "sans-serif"],
        display: ["Sora", "Inter", "sans-serif"],
      },
      boxShadow: {
        float: "0 28px 76px rgba(16, 33, 59, .15)",
      },
    },
  },
  plugins: [],
} satisfies Config;
