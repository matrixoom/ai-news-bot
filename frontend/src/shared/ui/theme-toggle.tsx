import type { ThemePreference } from "../hooks/use-theme-preference";
import { cn } from "../lib/cn";

type ThemeToggleProps = {
  value: ThemePreference;
  onChange: (nextTheme: ThemePreference) => void;
};

export function ThemeToggle({ value, onChange }: ThemeToggleProps) {
  return (
    <div className="flex flex-col items-end gap-1.5">
      <div aria-label="Theme mode" role="group" className="inline-flex rounded-full border border-slate-200 bg-slate-50 p-1">
        <button
          aria-label="Switch to light theme"
          aria-pressed={value === "light"}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition",
            value === "light"
              ? "border border-amber-200 bg-amber-50 text-amber-700 shadow-sm"
              : "text-slate-600 hover:bg-white hover:text-slate-900",
          )}
          onClick={() => onChange("light")}
          type="button"
        >
          <SunIcon />
          <span>Light</span>
        </button>
        <button
          aria-label="Switch to dark theme"
          aria-pressed={value === "dark"}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition",
            value === "dark"
              ? "bg-slate-800 text-white shadow-sm"
              : "text-slate-600 hover:bg-white hover:text-slate-900",
          )}
          onClick={() => onChange("dark")}
          type="button"
        >
          <MoonIcon />
          <span>Dark</span>
        </button>
      </div>
    </div>
  );
}

function SunIcon() {
  return (
    <svg aria-hidden="true" className="h-3.5 w-3.5" fill="none" viewBox="0 0 16 16">
      <circle cx="8" cy="8" r="3" className="stroke-current" strokeWidth="1.4" />
      <path
        className="stroke-current"
        d="M8 1.5V3.1M8 12.9v1.6M1.5 8h1.6M12.9 8h1.6M3.1 3.1l1.1 1.1M11.8 11.8l1.1 1.1M12.9 3.1l-1.1 1.1M4.2 11.8l-1.1 1.1"
        strokeLinecap="round"
        strokeWidth="1.2"
      />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg aria-hidden="true" className="h-3.5 w-3.5" fill="none" viewBox="0 0 16 16">
      <path
        className="stroke-current"
        d="M11.7 10.7a5 5 0 1 1-6.4-6.4A5.3 5.3 0 0 0 11.7 10.7Z"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.3"
      />
    </svg>
  );
}
