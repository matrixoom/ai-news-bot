import type { ThemePreference } from "../hooks/use-theme-preference";
import { cn } from "../lib/cn";
import { MoonIcon, SunIcon } from "@heroicons/react/24/outline";

type ThemeToggleProps = {
  value: ThemePreference;
  onChange: (nextTheme: ThemePreference) => void;
};

export function ThemeToggle({ value, onChange }: ThemeToggleProps) {
  return (
    <div className="flex flex-col items-end gap-1.5">
      <div aria-label="Theme mode" role="group" className="inline-flex rounded-control border border-line bg-surface-subtle p-0.5">
        <button
          aria-label="Switch to light theme"
          aria-pressed={value === "light"}
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-[6px] px-2.5 text-xs font-semibold",
            value === "light"
              ? "bg-surface text-ink shadow-sm"
              : "text-muted hover:text-ink",
          )}
          onClick={() => onChange("light")}
          type="button"
        >
          <SunIcon aria-hidden="true" className="h-4 w-4" />
          <span>浅色</span>
        </button>
        <button
          aria-label="Switch to dark theme"
          aria-pressed={value === "dark"}
          className={cn(
            "inline-flex h-8 items-center gap-1.5 rounded-[6px] px-2.5 text-xs font-semibold",
            value === "dark"
              ? "bg-surface text-ink shadow-sm"
              : "text-muted hover:text-ink",
          )}
          onClick={() => onChange("dark")}
          type="button"
        >
          <MoonIcon aria-hidden="true" className="h-4 w-4" />
          <span>深色</span>
        </button>
      </div>
    </div>
  );
}
