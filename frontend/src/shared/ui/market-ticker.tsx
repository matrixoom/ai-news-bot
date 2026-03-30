import type { MarketSignalCard } from "../../features/market/model/market-module.types";

type MarketTickerProps = {
  items: MarketSignalCard[];
  isLoading?: boolean;
};

export function MarketTicker({ items, isLoading = false }: MarketTickerProps) {
  if (isLoading && !items.length) {
    return <p className="text-sm text-slate-500">Market ticker loading...</p>;
  }

  if (!items.length) {
    return <p className="text-sm text-slate-500">Market ticker unavailable.</p>;
  }

  return (
    <div aria-label="Market ticker" role="region" className="flex flex-wrap gap-2">
      {items.map((item) => (
        <article
          key={item.key}
          className="inline-flex items-center gap-3 rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-sm shadow-sm"
        >
          <div className="leading-tight">
            <p className="font-medium text-slate-950">{item.label}</p>
            <p className="text-xs text-slate-500">{item.sourceLabel}</p>
          </div>
          <div className="text-right leading-tight">
            <p className="font-medium text-slate-900">{item.closeValue}</p>
            <p className="text-xs text-slate-500">{item.signal}</p>
          </div>
          <p className="text-xs text-slate-500">{item.tradeDate}</p>
        </article>
      ))}
    </div>
  );
}
