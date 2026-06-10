import { Bars3Icon } from "@heroicons/react/24/outline";
import { ThemeToggle } from "../shared/ui/theme-toggle";
import type { PageMeta } from "../shared/types/page-meta";

type HeaderBarProps = {
  meta: PageMeta;
  theme: "light" | "dark";
  onThemeChange: (nextTheme: "light" | "dark") => void;
  onOpenNavigation: () => void;
};

export function HeaderBar({
  meta,
  onOpenNavigation,
  onThemeChange,
  theme,
}: HeaderBarProps) {
  return (
    <header className="border-b border-line bg-surface/95 px-4 py-3 backdrop-blur md:px-6">
      <div data-testid="shell-header-row" className="flex min-w-0 items-center gap-3">
        <button
          aria-label="打开导航"
          className="workbench-icon-button lg:hidden"
          onClick={onOpenNavigation}
          type="button"
        >
          <Bars3Icon aria-hidden="true" className="h-5 w-5" />
        </button>
        <div data-testid="shell-header-title" className="min-w-0 flex-1">
          <p className="mb-0.5 text-xs font-medium text-muted">Trend Insight / {meta.title}</p>
          <div className="flex min-w-0 items-baseline gap-3">
            <h2 className="truncate text-xl font-semibold tracking-tight text-ink">{meta.title}</h2>
            <p className="hidden truncate text-xs text-muted md:block">{meta.description}</p>
          </div>
        </div>

        <div data-testid="shell-header-theme" className="shrink-0">
          <ThemeToggle onChange={onThemeChange} value={theme} />
        </div>
      </div>
    </header>
  );
}
