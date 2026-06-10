import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon } from "@heroicons/react/20/solid";
import type { StockMarketOverviewPayload } from "../model/market-data.types";

type MarketOverviewStripProps = {
  data?: StockMarketOverviewPayload;
  pending: boolean;
  error: boolean;
};

/** 渲染指数与市场宽度摘要带，状态同时使用文字和方向图标表达。 */
export function MarketOverviewStrip({ data, pending, error }: MarketOverviewStripProps) {
  return (
    <section aria-label="市场概览" className="grid border-b border-line bg-surface sm:grid-cols-3">
      {(data?.indices ?? [undefined, undefined]).map((index, position) => (
        <IndexMetric
          index={index}
          key={index?.symbol ?? position}
          label={index?.display_name ?? (position === 0 ? "上证指数" : "深证成指")}
          pending={pending}
        />
      ))}
      <div className="border-t border-line px-4 py-3 sm:border-l sm:border-t-0">
        <p className="text-xs font-medium text-muted">市场宽度</p>
        {pending ? (
          <p className="mt-1 text-sm text-muted">正在聚合最近交易日</p>
        ) : error || data?.breadth.status === "unavailable" ? (
          <p className="mt-1 text-sm text-muted">暂不可用</p>
        ) : (
          <>
            <div className="mt-1 flex flex-wrap items-baseline gap-x-3 gap-y-1 text-sm font-semibold">
              <span className="text-positive">↑ {data?.breadth.advanced ?? 0}</span>
              <span className="text-negative">↓ {data?.breadth.declined ?? 0}</span>
              <span className="text-muted">→ {data?.breadth.unchanged ?? 0}</span>
            </div>
            <p className="mt-1 text-[11px] text-muted">
              有效标的 {formatInteger(data?.breadth.total ?? 0)} · {data?.breadth.trade_date ?? "--"}
            </p>
          </>
        )}
      </div>
    </section>
  );
}

/**
 * 渲染单个指数的收盘值与方向。
 * @param props 指数数据、占位标题和加载状态。
 * @returns 指数摘要单元。
 */
function IndexMetric(props: {
  index?: StockMarketOverviewPayload["indices"][number];
  label: string;
  pending: boolean;
}) {
  const index = props.index;
  const change = index?.change ?? null;
  const direction = change === null || change === 0 ? "flat" : change > 0 ? "up" : "down";
  const DirectionIcon = direction === "up" ? ArrowUpIcon : direction === "down" ? ArrowDownIcon : ArrowRightIcon;
  const tone = direction === "up" ? "text-positive" : direction === "down" ? "text-negative" : "text-muted";

  return (
    <div className="border-t border-line px-4 py-3 first:border-t-0 sm:border-l sm:border-t-0 sm:first:border-l-0">
      <p className="text-xs font-medium text-muted">{props.label}</p>
      {props.pending ? (
        <p className="mt-1 text-sm text-muted">加载中</p>
      ) : !index || index.status === "unavailable" || index.close === null ? (
        <p className="mt-1 text-sm text-muted">暂不可用</p>
      ) : (
        <>
          <div className="mt-1 flex items-baseline gap-2">
            <strong className="text-lg font-semibold text-ink">{formatNumber(index.close)}</strong>
            <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${tone}`}>
              <DirectionIcon aria-hidden="true" className="h-3.5 w-3.5" />
              {formatSigned(index.change_pct)}%
            </span>
          </div>
          <p className="mt-1 text-[11px] text-muted">{index.trade_date ?? "--"} 收盘</p>
        </>
      )}
    </div>
  );
}

/** 将指数数值格式化为两位小数。 */
function formatNumber(value: number): string {
  return new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
}

/** 将家数格式化为带千分位的整数。 */
function formatInteger(value: number): string {
  return new Intl.NumberFormat("zh-CN").format(value);
}

/** 将涨跌幅格式化为带正负号的百分比数值。 */
function formatSigned(value: number | null): string {
  if (value === null) return "--";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}`;
}
