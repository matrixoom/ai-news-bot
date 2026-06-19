import { ArrowDownIcon, ArrowRightIcon, ArrowUpIcon } from "@heroicons/react/20/solid";
import type { StockMarketOverviewPayload } from "../model/market-data.types";

type MarketOverviewStripProps = {
  data?: StockMarketOverviewPayload;
  pending: boolean;
  error: boolean;
  selectedIndexSymbol?: string | null;
  onIndexSelect?: (symbol: string) => void;
};

const DEFAULT_OVERVIEW_INDEX_LABELS = ["沪深 300", "中证 500", "中证 1000", "上证综指", "深证成指", "创业板指", "恒生科技指数"];

/** 渲染指数与市场宽度摘要带，状态同时使用文字和方向图标表达。 */
export function MarketOverviewStrip({
  data,
  error,
  onIndexSelect,
  pending,
  selectedIndexSymbol,
}: MarketOverviewStripProps) {
  const indices =
    data?.indices && data.indices.length > 0
      ? data.indices
      : DEFAULT_OVERVIEW_INDEX_LABELS.map((label) => ({
          symbol: label,
          display_name: label,
          close: null,
          change: null,
          change_pct: null,
          trade_date: null,
          status: "unavailable",
        }));
  const overviewColumns = indices.length + 1;

  return (
    <section
      aria-label="市场概览"
      className="grid overflow-x-auto border-b border-line bg-surface"
      style={{ gridTemplateColumns: `repeat(${overviewColumns}, minmax(8rem, 1fr))` }}
    >
      {indices.map((index) => (
        <IndexMetric
          index={index}
          key={index.symbol}
          label={index.display_name}
          onSelect={onIndexSelect}
          pending={pending}
          selected={selectedIndexSymbol === index.symbol}
        />
      ))}
      <div className="min-w-0 border-l border-line px-3 py-2">
        <p className="truncate text-xs font-medium text-muted">市场宽度</p>
        {pending ? (
          <p className="mt-1 text-sm text-muted">正在聚合最近交易日</p>
        ) : error || data?.breadth.status === "unavailable" ? (
          <p className="mt-1 text-sm text-muted">暂不可用</p>
        ) : (
          <>
            <div className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5 text-sm font-semibold">
              <span className="text-positive">↑ {data?.breadth.advanced ?? 0}</span>
              <span className="text-negative">↓ {data?.breadth.declined ?? 0}</span>
              <span className="text-muted">→ {data?.breadth.unchanged ?? 0}</span>
            </div>
            <p className="mt-0.5 truncate text-[11px] text-muted">
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
  selected: boolean;
  pending: boolean;
  onSelect?: (symbol: string) => void;
}) {
  const index = props.index;
  const change = index?.change ?? null;
  const direction = change === null || change === 0 ? "flat" : change > 0 ? "up" : "down";
  const DirectionIcon = direction === "up" ? ArrowUpIcon : direction === "down" ? ArrowDownIcon : ArrowRightIcon;
  const tone = direction === "up" ? "text-positive" : direction === "down" ? "text-negative" : "text-muted";

  return (
    <button
      aria-expanded={props.selected}
      aria-label={`展开${props.label}宽基指数K线`}
      className={`min-w-0 border-l border-line px-3 py-2 text-left first:border-l-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent ${
        props.selected ? "bg-accent-soft/70" : "hover:bg-accent-soft/45"
      }`}
      onClick={() => index?.symbol && props.onSelect?.(index.symbol)}
      type="button"
    >
      <p className="truncate text-xs font-medium text-muted" title={props.label}>{props.label}</p>
      {props.pending ? (
        <p className="mt-1 text-sm text-muted">加载中</p>
      ) : !index || index.status === "unavailable" || index.close === null ? (
        <p className="mt-1 text-sm text-muted">暂不可用</p>
      ) : (
        <>
          <div className="mt-1 flex min-w-0 items-baseline gap-1.5">
            <strong className="truncate text-base font-semibold text-ink">{formatNumber(index.close)}</strong>
            <span className={`inline-flex items-center gap-0.5 text-xs font-semibold ${tone}`}>
              <DirectionIcon aria-hidden="true" className="h-3.5 w-3.5" />
              {formatSigned(index.change_pct)}%
            </span>
          </div>
          <p className="mt-0.5 truncate text-[11px] text-muted">{index.trade_date ?? "--"} 收盘</p>
        </>
      )}
    </button>
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
