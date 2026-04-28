import { ThemeToggle } from "../shared/ui/theme-toggle";
import type { PageMeta } from "../shared/types/page-meta";

type HeaderBarProps = {
  meta: PageMeta;
  theme: "light" | "dark";
  onThemeChange: (nextTheme: "light" | "dark") => void;
};

export function HeaderBar({
  meta,
  onThemeChange,
  theme,
}: HeaderBarProps) {
  return (
    <header className="border-b border-slate-200 bg-white/95 px-8 py-5 backdrop-blur">
      <div data-testid="shell-header-row" className="flex min-w-0 items-start gap-4">
        <div data-testid="shell-header-title" className="shrink-0 pr-1">
          <h2 className="text-2xl font-semibold text-slate-950">{meta.title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">{meta.description}</p>
        </div>

        <div className="flex-1" />

        <div data-testid="shell-header-theme" className="shrink-0 pl-2">
          <ThemeToggle onChange={onThemeChange} value={theme} />
        </div>
      </div>
    </header>
  );
}
