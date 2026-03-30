import { cn } from "../lib/cn";
import type { NewsMode, NewsModeOption } from "../hooks/use-news-mode";

type NewsModeSwitchProps = {
  value: NewsMode;
  options: readonly NewsModeOption[];
  onChange: (nextMode: NewsMode) => void;
};

export function NewsModeSwitch({ value, options, onChange }: NewsModeSwitchProps) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">News mode</p>
      <div aria-label="News mode" role="group" className="inline-flex rounded-full border border-slate-200 bg-slate-50 p-1">
        {options.map((option) => {
          const active = option.value === value;
          return (
            <button
              key={option.value}
              aria-pressed={active}
              className={cn(
                "rounded-full px-3 py-1.5 text-sm font-medium transition",
                active ? "bg-slate-900 text-white shadow-sm" : "text-slate-600 hover:bg-white hover:text-slate-900",
              )}
              onClick={() => onChange(option.value)}
              type="button"
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
