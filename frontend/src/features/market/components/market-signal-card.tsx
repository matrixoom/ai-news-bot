import type { MarketSignalCard as MarketSignalCardView } from "../model/market-module.types";

type MarketSignalCardProps = {
  card: MarketSignalCardView;
  compact?: boolean;
};

export function MarketSignalCard({ card, compact = false }: MarketSignalCardProps) {
  const latestPoint = card.chartPoints[card.chartPoints.length - 1];

  return (
    <article
      className={[
        "rounded-[1.75rem] border border-slate-200 bg-white shadow-sm",
        compact ? "p-4" : "p-5",
      ].join(" ")}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h4 className={compact ? "text-lg font-semibold text-slate-950" : "text-xl font-semibold text-slate-950"}>
            {card.label}
          </h4>
          <p className="mt-2 text-sm leading-6 text-slate-600">{card.explanation}</p>
        </div>
        <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-medium uppercase tracking-[0.16em] text-slate-600">
          {card.status}
        </span>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <SummaryTile label="Signal" value={card.signal} />
        <SummaryTile label="Deviation" value={card.deviationLabel} />
        <SummaryTile label="Close" value={card.closeValue} />
        <SummaryTile label="20d avg" value={card.ma20Value} />
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <SummaryTile label="Trade date" value={formatTradeDate(card.tradeDate)} />
        <SummaryTile label="Source" value={card.sourceLabel} />
      </div>

      <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{card.dataWindowLabel || "Data window"}</p>
        <p className="mt-2 text-sm leading-6 text-slate-600">
          {latestPoint
            ? `Latest point ${formatTradeDate(latestPoint.tradeDate)} at ${latestPoint.closePrice.toFixed(1)}`
            : "No chart history was returned."}
        </p>
        {card.historyWarning ? <p className="mt-2 text-sm text-amber-700">{card.historyWarning}</p> : null}
      </div>
    </article>
  );
}

function SummaryTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-slate-950">{value}</p>
    </div>
  );
}

function formatTradeDate(value: string): string {
  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  }).format(parsed);
}
