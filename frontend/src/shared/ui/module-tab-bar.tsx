import { Link } from "react-router-dom";
import { buildModuleTabHref, type ModuleTabDefinition } from "../lib/module-tabs";

type ModuleTabBarProps<TValue extends string> = {
  pathname: string;
  searchParams: URLSearchParams;
  tabs: readonly ModuleTabDefinition<TValue>[];
  activeTab: TValue;
  ariaLabel?: string;
};

export function ModuleTabBar<TValue extends string>({
  pathname,
  searchParams,
  tabs,
  activeTab,
  ariaLabel = "Module tabs",
}: ModuleTabBarProps<TValue>) {
  return (
    <div aria-label={ariaLabel} className="flex flex-wrap gap-2" role="tablist">
      {tabs.map((tab) => {
        const selected = tab.value === activeTab;

        return (
          <Link
            key={tab.value}
            aria-current={selected ? "page" : undefined}
            aria-selected={selected}
            className={[
              "inline-flex items-center rounded-full border px-4 py-2 text-sm font-medium transition",
              selected
                ? "border-slate-900 bg-slate-900 text-white shadow-sm"
                : "border-slate-200 bg-white text-slate-600 hover:border-slate-300 hover:text-slate-950",
            ].join(" ")}
            role="tab"
            to={buildModuleTabHref(pathname, searchParams, tab.value)}
          >
            {tab.label}
          </Link>
        );
      })}
    </div>
  );
}
