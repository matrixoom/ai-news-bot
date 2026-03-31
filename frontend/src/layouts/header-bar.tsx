import { LastUpdatedBadge } from "../shared/ui/last-updated-badge";
import { MarketTicker } from "../shared/ui/market-ticker";
import { NewsModeSwitch } from "../shared/ui/news-mode-switch";
import { ThemeToggle } from "../shared/ui/theme-toggle";
import type { MarketSignalCard } from "../features/market/model/market-module.types";
import type { NewsModeOption, NewsMode } from "../shared/hooks/use-news-mode";
import type { PageMeta } from "../shared/types/page-meta";

type HeaderBarProps = {
  meta: PageMeta;
  freshnessValue: string | null;
  freshnessNote: string;
  marketTickerItems: MarketSignalCard[];
  marketTickerLoading: boolean;
  newsMode: NewsMode;
  newsModeOptions: readonly NewsModeOption[];
  onNewsModeChange: (nextMode: NewsMode) => void;
  theme: "light" | "dark";
  onThemeToggle: () => void;
  showMarketTicker: boolean;
};

export function HeaderBar({
  meta,
  freshnessNote,
  freshnessValue,
  marketTickerItems,
  marketTickerLoading,
  newsMode,
  newsModeOptions,
  onNewsModeChange,
  onThemeToggle,
  showMarketTicker,
  theme,
}: HeaderBarProps) {
  return (
    <header className="border-b border-slate-200 bg-white/95 px-8 py-5 backdrop-blur">
      <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-3xl">
          <h2 className="text-2xl font-semibold text-slate-950">{meta.title}</h2>
          <p className="mt-1 text-sm leading-6 text-slate-500">{meta.description}</p>
        </div>

        <div className="flex flex-col gap-4 xl:items-end">
          <div className="flex flex-wrap items-end gap-6">
            <NewsModeSwitch onChange={onNewsModeChange} options={newsModeOptions} value={newsMode} />
            <ThemeToggle onToggle={onThemeToggle} value={theme} />
            <div className="space-y-2">
              {freshnessValue ? <LastUpdatedBadge label="Freshness" value={freshnessValue} /> : <FreshnessFallback />}
              <p className="text-xs leading-5 text-slate-500">{freshnessNote}</p>
            </div>
          </div>
        </div>
      </div>

      {showMarketTicker ? (
        <div className="mt-4 border-t border-slate-100 pt-4">
          <MarketTicker isLoading={marketTickerLoading} items={marketTickerItems} />
        </div>
      ) : null}
    </header>
  );
}

function FreshnessFallback() {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-slate-500">
      <span className="text-xs font-semibold uppercase tracking-[0.18em]">Freshness</span>
      <span className="text-sm font-medium">Loading...</span>
    </div>
  );
}
