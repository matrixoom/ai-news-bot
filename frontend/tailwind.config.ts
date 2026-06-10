import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        "surface-subtle": "rgb(var(--color-surface-subtle) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        muted: "rgb(var(--color-muted) / <alpha-value>)",
        accent: "rgb(var(--color-accent) / <alpha-value>)",
        "accent-soft": "rgb(var(--color-accent-soft) / <alpha-value>)",
        positive: "rgb(var(--color-positive) / <alpha-value>)",
        negative: "rgb(var(--color-negative) / <alpha-value>)",
        warning: "rgb(var(--color-warning) / <alpha-value>)",
      },
      borderRadius: {
        panel: "var(--radius-panel)",
        control: "var(--radius-control)",
      },
      boxShadow: {
        panel: "var(--shadow-panel)",
      },
      transitionDuration: {
        180: "180ms",
      },
    },
  },
  plugins: [],
} satisfies Config;
