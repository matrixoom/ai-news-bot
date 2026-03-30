import type { ThemePreference } from "../hooks/use-theme-preference";
import { cn } from "../lib/cn";

type ThemeToggleProps = {
  value: ThemePreference;
  onToggle: () => void;
};

export function ThemeToggle({ value, onToggle }: ThemeToggleProps) {
  const nextTheme = value === "light" ? "dark" : "light";

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Theme</p>
      <button
        aria-label={`Switch to ${nextTheme} theme`}
        aria-pressed={value === "dark"}
        className={cn(
          "inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm transition hover:border-slate-300 hover:text-slate-950",
        )}
        onClick={onToggle}
        type="button"
      >
        {value === "light" ? "Light" : "Dark"}
      </button>
    </div>
  );
}
