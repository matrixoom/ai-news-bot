import { useRef, type WheelEvent } from "react";
import type { MarketSignalCard } from "../../features/market/model/market-module.types";

type MarketTickerProps = {
  items: MarketSignalCard[];
  isLoading?: boolean;
};

export function MarketTicker({ items, isLoading = false }: MarketTickerProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    if (!scrollRef.current) {
      return;
    }

    if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) {
      return;
    }

    scrollRef.current.scrollLeft += event.deltaY;
    event.preventDefault();
  }

  if (isLoading && !items.length) {
    return <p className="text-sm text-slate-500">Market ticker loading...</p>;
  }

  if (!items.length) {
    return <p className="text-sm text-slate-500">Market ticker unavailable.</p>;
  }

  return (
    <div
      ref={scrollRef}
      aria-label="Market ticker"
      role="region"
      className="market-ticker-scroll overflow-x-auto"
      onWheel={handleWheel}
    >
      <div className="flex min-w-max gap-1 pb-1">
        {items.map((item) => (
          <article
            key={item.key}
            className="inline-grid min-w-[168px] grid-cols-[minmax(0,1fr)_auto] items-center gap-x-2 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-sm shadow-sm"
          >
            <div className="leading-tight">
              <p className="text-[12px] font-semibold text-slate-950">{item.label}</p>
              <p className="text-[11px] text-slate-500">{item.sourceLabel}</p>
            </div>
            <div className="text-right leading-tight">
              <p className="text-[12px] font-semibold text-slate-900">{item.closeValue}</p>
              <p className="text-[11px] text-slate-500">{item.signal}</p>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}
