"""A 股与 ETF 行情的 AkShare 同步服务。"""

from __future__ import annotations

from datetime import date, timedelta
import logging
import re
from typing import Any, Callable, Mapping, Sequence

from .stock_market_repository import StockInstrument, StockMarketRepository


DataFrameLoader = Callable[..., Any]
logger = logging.getLogger(__name__)
AKSHARE_DAILY_TIMEOUT_SECONDS = 10


class StockMarketSyncService:
    """通过 AkShare 同步股票市场标的、日线、概况和财报。

    Args:
        repository: 股票市场本地仓储。
        stock_universe_loader: A 股代码名称加载函数，测试可注入。
        etf_universe_loader: ETF 代码名称加载函数，测试可注入。
        lof_universe_loader: LOF 代码名称加载函数，测试可注入。
        stock_daily_loader: A 股日线加载函数，测试可注入。
        etf_daily_loader: ETF 日线加载函数，测试可注入。
        lof_daily_loader: LOF 日线加载函数，测试可注入。

    Returns:
        可执行同步任务的服务实例。
    """

    def __init__(
        self,
        repository: StockMarketRepository | None = None,
        *,
        stock_universe_loader: DataFrameLoader | None = None,
        etf_universe_loader: DataFrameLoader | None = None,
        lof_universe_loader: DataFrameLoader | None = None,
        stock_daily_loader: DataFrameLoader | None = None,
        etf_daily_loader: DataFrameLoader | None = None,
        lof_daily_loader: DataFrameLoader | None = None,
        profile_loader: DataFrameLoader | None = None,
        benefit_loader: DataFrameLoader | None = None,
        cash_loader: DataFrameLoader | None = None,
        debt_loader: DataFrameLoader | None = None,
        valuation_loader: DataFrameLoader | None = None,
        dividend_loader: DataFrameLoader | None = None,
        financial_analysis_loader: DataFrameLoader | None = None,
    ) -> None:
        """初始化股票同步服务及其可替换的数据加载器。

        Args:
            repository: 股票市场仓储。
            stock_universe_loader: A 股标的加载器。
            etf_universe_loader: ETF 标的加载器。
            lof_universe_loader: LOF 标的加载器。
            stock_daily_loader: A 股日线加载器。
            etf_daily_loader: ETF 日线加载器。
            lof_daily_loader: LOF 日线加载器。
            profile_loader: 公司概况加载器。
            benefit_loader: 利润表加载器。
            cash_loader: 现金流量表加载器。
            debt_loader: 资产负债表加载器。
            valuation_loader: 个股日频估值加载器。
            dividend_loader: 个股分红事件加载器。
            financial_analysis_loader: 个股主要财务指标加载器。
        """

        self._repository = repository or StockMarketRepository()
        self._stock_universe_loader = stock_universe_loader or _ak_stock_universe
        self._etf_universe_loader = etf_universe_loader or _ak_etf_universe
        self._lof_universe_loader = lof_universe_loader or _ak_lof_universe
        self._stock_daily_loader = stock_daily_loader or _ak_stock_daily
        self._etf_daily_loader = etf_daily_loader or _ak_etf_daily
        self._lof_daily_loader = lof_daily_loader or _ak_lof_daily
        self._profile_loader = profile_loader or _ak_stock_profile
        self._benefit_loader = benefit_loader or _ak_financial_benefit
        self._cash_loader = cash_loader or _ak_financial_cash
        self._debt_loader = debt_loader or _ak_financial_debt
        self._valuation_loader = valuation_loader or _ak_stock_valuation
        self._dividend_loader = dividend_loader or _ak_stock_dividend
        self._financial_analysis_loader = financial_analysis_loader or _ak_financial_analysis

    def sync_universe(self) -> dict[str, Any]:
        """同步 A 股全市场股票、ETF 和 LOF 标的列表。

        Returns:
            分类型写入数量和可展示的上游告警。
        """

        warnings: list[str] = []
        stock_rows: list[dict[str, str]] = []
        etf_rows: list[dict[str, str]] = []
        lof_rows: list[dict[str, str]] = []
        try:
            stock_rows = _stock_universe_from_frame(self._stock_universe_loader())
        except Exception as error:
            logger.warning("stock universe source failed: %s", _compact_error_message(error))
            warnings.append(f"A股标的同步失败：{_compact_error_message(error)}")
        try:
            etf_rows = _etf_universe_from_frame(self._etf_universe_loader())
        except Exception as error:
            logger.warning("ETF universe source failed: %s", _compact_error_message(error))
            warnings.append(f"ETF标的同步失败：{_compact_error_message(error)}")
        try:
            lof_rows = _lof_universe_from_frame(self._lof_universe_loader())
        except Exception as error:
            logger.warning("LOF universe source failed: %s", _compact_error_message(error))
            warnings.append(f"LOF标的同步失败：{_compact_error_message(error)}")

        rows = [*stock_rows, *etf_rows, *lof_rows]
        if rows:
            self._repository.upsert_instruments(rows)
        return {
            "stock": len(stock_rows),
            "etf": len(etf_rows),
            "lof": len(lof_rows),
            "total": len(rows),
            "warnings": warnings,
        }

    def sync_symbol_window(
        self,
        instrument: StockInstrument,
        *,
        start_date: date,
        end_date: date,
        include_valuation: bool = True,
        include_history_padding: bool = True,
    ) -> dict[str, int]:
        """同步单只股票指定窗口的日线数据，并补足均线计算前置窗口。

        Args:
            instrument: 已持久化的股票或 ETF 标的。
            start_date: 用户请求起始日期。
            end_date: 用户请求结束日期。
            include_valuation: 是否为 A 股同步日频估值和分红数据；批量基础行情刷新会关闭该项以避开易失败扩展源。
            include_history_padding: 是否向前扩展下载窗口以补足均线前置数据；缺口补采关闭该项以避免重复下载已缓存区间。

        Returns:
            本次写入的日线点位数量。
        """

        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        # 为 MA120 留出足够的历史缓冲，避免窗口开始处均线断裂。
        padded_start = start_date - timedelta(days=220) if include_history_padding else start_date
        if instrument.instrument_type == "lof":
            loader = self._lof_daily_loader
        elif instrument.instrument_type == "etf":
            loader = self._etf_daily_loader
        else:
            loader = self._stock_daily_loader
        frame = loader(
            symbol=instrument.code,
            start_date=padded_start.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        bars = _daily_bars_from_frame(frame)
        if not bars:
            raise ValueError(f"stock daily history returned no data: {instrument.symbol}")
        rows = _with_moving_averages(bars)
        warnings: list[str] = []
        if instrument.instrument_type == "stock" and include_valuation:
            valuation_frame: Any = None
            dividend_frame: Any = None
            try:
                valuation_frame = self._valuation_loader(symbol=instrument.code)
            except Exception as error:
                message = f"估值数据同步失败：{_compact_error_message(error)}"
                logger.warning("stock valuation sync failed for %s: %s", instrument.symbol, message)
                warnings.append(message)
            try:
                dividend_frame = self._dividend_loader(symbol=instrument.code)
            except Exception as error:
                message = f"分红数据同步失败：{_compact_error_message(error)}"
                logger.warning("stock dividend sync failed for %s: %s", instrument.symbol, message)
                warnings.append(message)
            rows = _valuation_rows_from_frames(rows, valuation_frame, dividend_frame)
        count = self._repository.upsert_daily_bars(instrument.symbol, rows)
        if warnings:
            self._repository.record_sync_warning(instrument.symbol, "；".join(warnings))
        return {"daily_bars": count}

    def sync_profile(self, instrument: StockInstrument) -> dict[str, int]:
        """同步单只股票公司概况；ETF/LOF 使用基础信息兜底。"""

        if _is_fund_instrument(instrument):
            self._repository.upsert_profile(_fund_profile(instrument))
            return {"profile": 1}
        try:
            frame = self._profile_loader(symbol=instrument.code)
            profile = _stock_profile_from_frame(instrument, frame)
        except Exception as error:
            logger.warning("stock profile sync failed for %s: %s", instrument.symbol, error)
            profile = _fallback_profile(instrument)
        self._repository.upsert_profile(profile)
        return {"profile": 1}

    def sync_financials(self, instrument: StockInstrument) -> dict[str, int]:
        """同步单只股票财报摘要；ETF/LOF 没有公司财报，保持空结果。"""

        if _is_fund_instrument(instrument):
            return {"financial_metrics": 0}
        code = instrument.code
        benefit_frame = self._benefit_loader(symbol=code)
        cash_frame = self._cash_loader(symbol=code)
        debt_frame = self._debt_loader(symbol=code)
        warning = ""
        analysis_frame: Any = None
        try:
            analysis_frame = self._financial_analysis_loader(symbol=instrument.symbol)
        except Exception as error:
            warning = f"财务分析指标同步失败：{_compact_error_message(error)}"
            logger.warning("stock financial analysis sync failed for %s: %s", instrument.symbol, warning)
        metrics = _financial_metrics_from_frames(
            benefit_frame,
            cash_frame,
            debt_frame,
            analysis_frame,
        )
        count = self._repository.upsert_financial_metrics(instrument.symbol, metrics)
        if warning:
            self._repository.record_sync_warning(instrument.symbol, warning)
        return {"financial_metrics": count}


def _ak_stock_universe() -> Any:
    """读取 AkShare A 股代码名称表，主端点失败时切换快照端点。"""

    import akshare as ak

    return _first_successful_akshare_call(
        [
            ("stock_info_a_code_name", lambda: ak.stock_info_a_code_name()),
            ("stock_zh_a_spot_em", lambda: ak.stock_zh_a_spot_em()),
            ("stock_zh_a_spot", lambda: ak.stock_zh_a_spot()),
        ]
    )


def _ak_etf_universe() -> Any:
    """读取 AkShare ETF 列表，东方财富失败时切换同花顺/新浪端点。"""

    import akshare as ak

    return _first_successful_akshare_call(
        [
            ("fund_etf_spot_em", lambda: ak.fund_etf_spot_em()),
            ("fund_etf_fund_daily_em", lambda: ak.fund_etf_fund_daily_em()),
            ("fund_etf_spot_ths", lambda: ak.fund_etf_spot_ths()),
            ("fund_etf_category_ths", lambda: ak.fund_etf_category_ths(symbol="ETF")),
            ("fund_etf_category_sina", lambda: ak.fund_etf_category_sina(symbol="ETF基金")),
        ]
    )


def _ak_lof_universe() -> Any:
    """读取 AkShare LOF 列表，主端点失败时回退场内基金排行和新浪分类。"""

    import akshare as ak

    return _first_successful_akshare_call(
        [
            ("fund_lof_spot_em", lambda: ak.fund_lof_spot_em()),
            ("fund_etf_category_sina", lambda: ak.fund_etf_category_sina(symbol="LOF基金")),
            ("fund_exchange_rank_em", lambda: ak.fund_exchange_rank_em()),
        ]
    )


def _ak_stock_daily(**kwargs: Any) -> Any:
    """读取 A 股历史日线，东方财富失败时回退腾讯/新浪兼容端点。"""

    import akshare as ak

    symbol = str(kwargs["symbol"])
    start_date = str(kwargs["start_date"])
    end_date = str(kwargs["end_date"])
    exchange = _exchange_for_code(symbol)
    prefixed_symbol = f"{exchange.lower()}{symbol}" if exchange else symbol
    return _first_successful_akshare_call(
        [
            (
                "stock_zh_a_hist",
                lambda: ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                    timeout=AKSHARE_DAILY_TIMEOUT_SECONDS,
                ),
            ),
            (
                "stock_zh_a_hist_tx",
                lambda: _normalize_tencent_stock_history_frame(
                    ak.stock_zh_a_hist_tx(
                        symbol=prefixed_symbol,
                        start_date=start_date,
                        end_date=end_date,
                        adjust="",
                        timeout=AKSHARE_DAILY_TIMEOUT_SECONDS,
                    )
                ),
            ),
            (
                "stock_zh_a_daily",
                lambda: _filter_history_frame_by_date(
                    ak.stock_zh_a_daily(symbol=prefixed_symbol, start_date=start_date, end_date=end_date, adjust=""),
                    start_date=start_date,
                    end_date=end_date,
                ),
            ),
        ]
    )


def _normalize_tencent_stock_history_frame(frame: Any) -> Any:
    """规范腾讯 A 股日线字段，并将成交量从手转换为股。

    Args:
        frame: AkShare `stock_zh_a_hist_tx` 返回的 DataFrame。

    Returns:
        使用统一 `volume` 字段且成交量单位为股的 DataFrame。
    """

    columns = getattr(frame, "columns", [])
    if "amount" not in columns or "volume" in columns:
        return frame
    copied = frame.copy()
    copied["volume"] = copied["amount"].map(
        lambda value: parsed * 100 if (parsed := _parse_number(value)) is not None else None
    )
    return copied.drop(columns=["amount"])


def _ak_etf_daily(**kwargs: Any) -> Any:
    """读取 ETF 历史日线，东方财富失败时回退新浪端点。"""

    import akshare as ak

    symbol = str(kwargs["symbol"])
    start_date = str(kwargs["start_date"])
    end_date = str(kwargs["end_date"])
    exchange = _exchange_for_code(symbol)
    prefixed_symbol = f"{exchange.lower()}{symbol}" if exchange else symbol
    return _first_successful_akshare_call(
        [
            (
                "fund_etf_hist_em",
                lambda: ak.fund_etf_hist_em(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust="",
                ),
            ),
            (
                "fund_etf_hist_sina",
                lambda: _filter_history_frame_by_date(
                    ak.fund_etf_hist_sina(symbol=prefixed_symbol),
                    start_date=start_date,
                    end_date=end_date,
                ),
            ),
        ]
    )


def _ak_lof_daily(**kwargs: Any) -> Any:
    """读取 LOF 历史日线。"""

    import akshare as ak

    return ak.fund_lof_hist_em(
        symbol=str(kwargs["symbol"]),
        period="daily",
        start_date=str(kwargs["start_date"]),
        end_date=str(kwargs["end_date"]),
        adjust="",
    )


def _ak_stock_profile(**kwargs: Any) -> Any:
    """读取东方财富个股信息。"""

    import akshare as ak

    return ak.stock_individual_info_em(**kwargs)


def _ak_financial_benefit(**kwargs: Any) -> Any:
    """读取同花顺利润表。"""

    import akshare as ak

    return ak.stock_financial_benefit_ths(indicator="按报告期", **kwargs)


def _ak_financial_cash(**kwargs: Any) -> Any:
    """读取同花顺现金流量表。"""

    import akshare as ak

    return ak.stock_financial_cash_ths(indicator="按报告期", **kwargs)


def _ak_financial_debt(**kwargs: Any) -> Any:
    """读取同花顺资产负债表。"""

    import akshare as ak

    return ak.stock_financial_debt_ths(indicator="按报告期", **kwargs)


def _ak_stock_valuation(**kwargs: Any) -> Any:
    """读取东方财富个股日频估值历史。"""

    import akshare as ak

    return ak.stock_value_em(**kwargs)


def _ak_stock_dividend(**kwargs: Any) -> Any:
    """读取东方财富个股分红送配详情。"""

    import akshare as ak

    return ak.stock_fhps_detail_em(**kwargs)


def _ak_financial_analysis(**kwargs: Any) -> Any:
    """读取东方财富个股主要财务指标。"""

    import akshare as ak

    return ak.stock_financial_analysis_indicator_em(indicator="按报告期", **kwargs)


def _first_successful_akshare_call(loaders: Sequence[tuple[str, Callable[[], Any]]]) -> Any:
    """按顺序调用 AkShare 端点，返回首个非空 DataFrame。

    Args:
        loaders: 端点名称与加载函数列表。

    Returns:
        首个成功且非空的 DataFrame。
    """

    errors: list[str] = []
    for name, loader in loaders:
        try:
            frame = loader()
            if getattr(frame, "empty", False):
                errors.append(f"{name}: empty")
                continue
            return frame
        except Exception as error:
            errors.append(f"{name}: {_compact_error_message(error)}")
    raise RuntimeError("; ".join(errors))


def _filter_history_frame_by_date(frame: Any, *, start_date: str, end_date: str) -> Any:
    """过滤不支持日期参数的 AkShare 历史表。

    Args:
        frame: AkShare 返回的 DataFrame。
        start_date: `YYYYMMDD` 起始日期。
        end_date: `YYYYMMDD` 结束日期。

    Returns:
        按日期过滤后的 DataFrame；缺少日期列时返回原表。
    """

    date_column = None
    for candidate in ("日期", "date", "trade_date"):
        if candidate in getattr(frame, "columns", []):
            date_column = candidate
            break
    if date_column is None:
        return frame
    start_text = _compact_date(start_date)
    end_text = _compact_date(end_date)
    copied = frame.copy()
    date_values = copied[date_column].astype(str).map(_compact_date)
    return copied[(date_values >= start_text) & (date_values <= end_text)]


def _compact_error_message(error: Exception) -> str:
    """压缩外部数据源异常，避免长 URL 和代理栈进入前端提示。

    Args:
        error: 上游调用异常。

    Returns:
        面向日志和 UI 的短错误说明。
    """

    message = str(error)
    lowered = message.lower()
    if "proxyerror" in lowered or "unable to connect to proxy" in lowered:
        return "代理连接失败，无法访问上游端点"
    if "max retries exceeded" in lowered:
        return "上游端点多次重试失败"
    if "invalid argument" in lowered:
        return "上游端点参数或本地网络环境异常"
    return message[:180]


def _compact_date(raw_value: str) -> str:
    """将日期文本压缩为 YYYYMMDD 便于比较。"""

    digits = re.sub(r"\D", "", str(raw_value))
    return digits[:8]


def _stock_universe_from_frame(frame: Any) -> list[dict[str, str]]:
    """将 AkShare A 股代码表转换为统一标的列表。"""

    rows: list[dict[str, str]] = []
    for _, row in frame.iterrows():
        code = _normalize_code(_cell(row, ["code", "symbol", "证券代码", "股票代码", "代码", "代码代码"]))
        name = _cell(row, ["name", "证券简称", "股票简称", "名称", "股票名称", "简称"])
        if not _is_stock_code(code) or not name:
            continue
        exchange = _exchange_for_code(code)
        if not exchange:
            continue
        rows.append({
            "symbol": f"{code}.{exchange}",
            "code": code,
            "exchange": exchange,
            "name": name,
            "instrument_type": "stock",
            "market_board": _board_for_stock_code(code),
            "listing_status": _listing_status_for_name(name),
            "source_url": "https://akshare.akfamily.xyz/",
        })
    return _dedupe_rows(rows)


def _etf_universe_from_frame(frame: Any) -> list[dict[str, str]]:
    """将 AkShare ETF 列表转换为统一标的列表。"""

    rows: list[dict[str, str]] = []
    for _, row in frame.iterrows():
        code = _normalize_code(_cell(row, ["代码", "基金代码", "symbol", "code", "基金代码", "代码代码"]))
        name = _cell(row, ["名称", "基金简称", "name", "基金简称", "简称"])
        if not _is_etf_code(code) or not name:
            continue
        exchange = _exchange_for_code(code)
        if not exchange:
            continue
        rows.append({
            "symbol": f"{code}.{exchange}",
            "code": code,
            "exchange": exchange,
            "name": name,
            "instrument_type": "etf",
            "market_board": _board_for_fund_code(code, name, _cell(row, ["类型", "基金类型"])),
            "listing_status": _listing_status_for_name(name),
            "source_url": "https://akshare.akfamily.xyz/",
        })
    return _dedupe_rows(rows)


def _lof_universe_from_frame(frame: Any) -> list[dict[str, str]]:
    """将 AkShare LOF 列表转换为统一标的列表。"""

    rows: list[dict[str, str]] = []
    for _, row in frame.iterrows():
        code = _normalize_code(_cell(row, ["代码", "基金代码", "symbol", "code", "基金代码", "代码代码"]))
        name = _cell(row, ["名称", "基金简称", "name", "基金简称", "简称"])
        if not _is_lof_code(code) or not name:
            continue
        exchange = _exchange_for_code(code)
        if not exchange:
            continue
        rows.append({
            "symbol": f"{code}.{exchange}",
            "code": code,
            "exchange": exchange,
            "name": name,
            "instrument_type": "lof",
            "market_board": _board_for_fund_code(code, name, _cell(row, ["类型", "基金类型"])),
            "listing_status": _listing_status_for_name(name),
            "source_url": "https://akshare.akfamily.xyz/",
        })
    return _dedupe_rows(rows)


def _daily_bars_from_frame(frame: Any) -> list[dict[str, float | str]]:
    """将 AkShare 日线 DataFrame 解析为 OHLCV 点。"""

    bars: list[dict[str, float | str]] = []
    for _, row in frame.iterrows():
        trade_date = _cell(row, ["日期", "date", "trade_date"])
        if hasattr(trade_date, "strftime"):
            date_text = trade_date.strftime("%Y-%m-%d")
        else:
            date_text = str(trade_date)[:10]
        open_price = _parse_number(_cell(row, ["开盘", "open"]))
        close_price = _parse_number(_cell(row, ["收盘", "close"]))
        high_price = _parse_number(_cell(row, ["最高", "high"]))
        low_price = _parse_number(_cell(row, ["最低", "low"]))
        volume = _parse_number(_cell(row, ["成交量", "volume"]))
        if None in (open_price, close_price, high_price, low_price, volume):
            continue
        bars.append({
            "trade_date": date_text,
            "open_price": float(open_price),
            "close_price": float(close_price),
            "high_price": float(high_price),
            "low_price": float(low_price),
            "volume": float(volume),
            "provider_key": "akshare",
            "source_url": "https://akshare.akfamily.xyz/",
        })
    return sorted(bars, key=lambda item: str(item["trade_date"]))


def _with_moving_averages(bars: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """为日线点补充 MA5/10/20/60/120。"""

    rows: list[dict[str, Any]] = [dict(item) for item in bars]
    closes = [float(row["close_price"]) for row in rows]
    for period in (5, 10, 20, 60, 120):
        values = _simple_moving_average(closes, period)
        for row, value in zip(rows, values):
            row[f"ma{period}"] = value
    return rows


def _simple_moving_average(values: Sequence[float], period: int) -> list[float | None]:
    """计算简单移动平均线。"""

    result: list[float | None] = []
    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= period:
            rolling_sum -= values[index - period]
        if index < period - 1:
            result.append(None)
        else:
            result.append(round(rolling_sum / period, 4))
    return result


def _stock_profile_from_frame(instrument: StockInstrument, frame: Any) -> dict[str, Any]:
    """将个股信息表转换为公司概况。"""

    values: dict[str, str] = {}
    for _, row in frame.iterrows():
        key = _cell(row, ["item", "指标", "项目"])
        value = _cell(row, ["value", "值", "数值"])
        if key:
            values[key] = value
    industry = _first_present(values, ["行业", "所属行业", "行业板块"])
    region = _first_present(values, ["地区", "省份", "区域"])
    listing_date = _normalize_listing_date(_first_present(values, ["上市时间", "上市日期"]))
    company_name = _first_present(values, ["股票简称", "公司名称", "名称"]) or instrument.name
    sector = industry or instrument.market_board
    return {
        "symbol": instrument.symbol,
        "company_name": company_name,
        "industry": industry,
        "sector": sector,
        "region": region,
        "listing_date": listing_date,
        "attributes": _infer_stock_attributes(instrument, industry),
        "summary": f"{company_name}，{instrument.market_board}上市公司，所属行业：{industry or '未知'}。",
        "provider_key": "akshare_profile",
        "source_url": "https://akshare.akfamily.xyz/",
    }


def _fallback_profile(instrument: StockInstrument) -> dict[str, Any]:
    """构造公司概况兜底数据，保证前端空态可解释。"""

    return {
        "symbol": instrument.symbol,
        "company_name": instrument.name,
        "industry": "",
        "sector": instrument.market_board,
        "region": "",
        "listing_date": "",
        "attributes": _infer_stock_attributes(instrument, ""),
        "provider_key": "fallback",
        "source_url": "",
    }


def _fund_profile(instrument: StockInstrument) -> dict[str, Any]:
    """构造 ETF/LOF 概况。"""

    fund_type = "LOF" if instrument.instrument_type == "lof" else "ETF"

    return {
        "symbol": instrument.symbol,
        "company_name": instrument.name,
        "industry": fund_type,
        "sector": instrument.market_board,
        "region": "",
        "listing_date": "",
        "attributes": [fund_type],
        "summary": f"{instrument.name} 是{fund_type}场内基金，暂无公司财报口径。",
        "provider_key": f"akshare_{instrument.instrument_type}",
        "source_url": "https://akshare.akfamily.xyz/",
    }


def _financial_metrics_from_frames(
    benefit_frame: Any,
    cash_frame: Any,
    debt_frame: Any,
    analysis_frame: Any = None,
) -> list[dict[str, Any]]:
    """从三张财务报表和主要指标表抽取前端需要的财报指标。"""

    metrics_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    specs = [
        (benefit_frame, "revenue", "营业收入", ["*营业总收入", "一、营业总收入", "营业总收入", "其中：营业收入"]),
        (benefit_frame, "expense", "营业支出", ["*营业支出", "二、营业支出", "营业总成本", "营业支出"]),
        (cash_frame, "cash_flow", "经营活动现金流", ["*经营活动产生的现金流量净额", "经营活动产生的现金流量净额"]),
        (debt_frame, "liability", "负债合计", ["*负债合计", "负债合计"]),
        (debt_frame, "asset", "资产合计", ["*资产合计", "资产合计"]),
    ]
    for frame, metric, label, columns in specs:
        for item in _extract_metric_rows(frame, metric, label, columns):
            key = (str(item["report_period"]), str(item["report_type"]), str(item["metric"]))
            metrics_by_key[key] = item
    percentage_specs = [
        ("roe", "ROE", ["ROEJQ", "净资产收益率"]),
        ("revenue_yoy", "营收同比", ["TOTALOPERATEREVETZ", "营业总收入同比增长"]),
        ("net_profit_yoy", "净利润同比", ["PARENTNETPROFITTZ", "归属净利润同比增长"]),
        ("debt_asset_ratio", "资产负债率", ["ZCFZL", "资产负债率"]),
    ]
    for metric, label, columns in percentage_specs:
        for item in _extract_percentage_metric_rows(analysis_frame, metric, label, columns):
            key = (str(item["report_period"]), str(item["report_type"]), str(item["metric"]))
            metrics_by_key[key] = item
    return sorted(metrics_by_key.values(), key=lambda item: (str(item["report_period"]), str(item["metric"])))


def _extract_metric_rows(frame: Any, metric: str, label: str, columns: Sequence[str]) -> list[dict[str, Any]]:
    """从单张财报表抽取指定列。"""

    rows: list[dict[str, Any]] = []
    for _, row in _iter_frame_rows(frame):
        report_period = _cell(row, ["报告期", "日期", "report_period"])
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_period):
            continue
        raw_value = _first_row_value(row, columns)
        value = _parse_money_to_yi(raw_value)
        if value is None:
            continue
        rows.append({
            "report_period": report_period,
            "report_type": "yearly" if report_period.endswith("12-31") else "quarterly",
            "metric": metric,
            "label": label,
            "value": round(value, 4),
            "unit": "亿元",
            "provider_key": "akshare_financial",
        })
    return rows


def _extract_percentage_metric_rows(
    frame: Any,
    metric: str,
    label: str,
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    """从主要财务指标表抽取单项百分比序列。

    Args:
        frame: 东方财富主要财务指标 DataFrame。
        metric: 稳定的指标标识。
        label: 前端展示名称。
        columns: 上游字段候选列表。

    Returns:
        按报告期标准化的百分比指标列表。
    """

    rows: list[dict[str, Any]] = []
    for _, row in _iter_frame_rows(frame):
        report_period = _cell(row, ["REPORT_DATE", "报告期", "日期", "report_period"])[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report_period):
            continue
        value = _parse_number(_first_row_value(row, columns))
        if value is None:
            continue
        rows.append({
            "report_period": report_period,
            "report_type": "yearly" if report_period.endswith("12-31") else "quarterly",
            "metric": metric,
            "label": label,
            "value": round(value, 4),
            "unit": "%",
            "provider_key": "akshare_financial_analysis",
        })
    return rows


def _valuation_rows_from_frames(
    bars: Sequence[Mapping[str, Any]],
    valuation_frame: Any,
    dividend_frame: Any,
) -> list[dict[str, Any]]:
    """将日频估值和已实施分红事件合并到 OHLCV 行。

    Args:
        bars: 已计算均线的日线记录。
        valuation_frame: 东方财富估值历史 DataFrame。
        dividend_frame: 东方财富分红送配详情 DataFrame。

    Returns:
        增加 PE、PB、股息率和总市值字段的日线记录。
    """

    valuation_by_date: dict[str, dict[str, float | None]] = {}
    for _, row in _iter_frame_rows(valuation_frame):
        trade_date = _cell(row, ["数据日期", "日期", "date", "trade_date"])[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", trade_date):
            continue
        valuation_by_date[trade_date] = {
            "pe_ttm": _parse_number(_first_row_value(row, ["PE(TTM)", "PE_TTM", "市盈率(TTM)"])),
            "pb_mrq": _parse_number(_first_row_value(row, ["市净率", "PB_MRQ", "PB(MRQ)"])),
            "total_market_cap": _parse_number(
                _first_row_value(row, ["总市值", "TOTAL_MARKET_CAP", "total_market_cap"])
            ),
        }

    dividends: list[tuple[date, float]] = []
    for _, row in _iter_frame_rows(dividend_frame):
        progress = _cell(row, ["方案进度", "进度", "status"])
        ex_date_text = _cell(row, ["除权除息日", "除息日", "ex_date"])[:10]
        cash_per_ten = _parse_number(
            _first_row_value(row, ["现金分红-现金分红比例", "派息", "cash_dividend_per_10"])
        )
        if "实施" not in progress or cash_per_ten is None:
            continue
        try:
            ex_date = date.fromisoformat(ex_date_text)
        except ValueError:
            continue
        dividends.append((ex_date, cash_per_ten / 10))

    rows: list[dict[str, Any]] = []
    for item in bars:
        row = dict(item)
        trade_date_text = str(item["trade_date"])[:10]
        valuation = valuation_by_date.get(trade_date_text, {})
        row["pe_ttm"] = valuation.get("pe_ttm")
        row["pb_mrq"] = valuation.get("pb_mrq")
        row["total_market_cap"] = valuation.get("total_market_cap")
        close_price = _parse_number(item.get("close_price"))
        try:
            trade_date = date.fromisoformat(trade_date_text)
        except ValueError:
            trade_date = None
        if trade_date is None or close_price is None or close_price == 0:
            row["dividend_yield_ttm"] = None
        else:
            window_start = trade_date - timedelta(days=365)
            cash_per_share = sum(
                amount
                for ex_date, amount in dividends
                if window_start < ex_date <= trade_date
            )
            row["dividend_yield_ttm"] = (
                round(cash_per_share / close_price * 100, 4)
                if cash_per_share > 0
                else None
            )
        rows.append(row)
    return rows


def _iter_frame_rows(frame: Any) -> Any:
    """安全返回 DataFrame 行迭代器，空值按空表处理。"""

    if frame is None or not hasattr(frame, "iterrows"):
        return ()
    return frame.iterrows()


def _infer_stock_attributes(instrument: StockInstrument, industry: str) -> list[str]:
    """根据板块和行业推断成长/价值/周期等股票属性。"""

    attributes: list[str] = []
    if instrument.market_board in {"科创板", "创业板"}:
        attributes.append("成长股")
    if any(keyword in industry for keyword in ["银行", "公用事业", "交通运输", "高速"]):
        attributes.append("价值股")
    if any(keyword in industry for keyword in ["有色", "钢铁", "煤炭", "化工", "房地产", "建材"]):
        attributes.append("周期股")
    if not attributes:
        attributes.append("综合型")
    return attributes


def _is_fund_instrument(instrument: StockInstrument) -> bool:
    """判断标的是否为没有公司财报口径的场内基金。"""

    return instrument.instrument_type in {"etf", "lof"}


def _board_for_stock_code(code: str) -> str:
    """按 A 股代码前缀识别交易板块。"""

    if code.startswith(("688", "689")):
        return "科创板"
    if code.startswith(("300", "301")):
        return "创业板"
    if code.startswith(("8", "4", "920")):
        return "北交所"
    if code.startswith(("000", "001", "002", "003")):
        return "深市"
    if code.startswith(("600", "601", "603", "605")):
        return "沪市"
    return "A股"


def _board_for_fund_code(code: str, name: str, category: str = "") -> str:
    """按基金底层资产和上市交易所识别市场类型。

    Args:
        code: 六位基金代码。
        name: 基金简称。
        category: AkShare 返回的基金类型字段。

    Returns:
        `境外`、`沪市`、`深市` 或兜底的 `场内基金`。
    """

    if _is_overseas_fund(name, category):
        return "境外"
    exchange = _exchange_for_code(code)
    if exchange == "SH":
        return "沪市"
    if exchange == "SZ":
        return "深市"
    return "场内基金"


def _listing_status_for_name(name: str) -> str:
    """从简称识别上市、ST 或退市状态。"""

    normalized = name.strip().upper()
    if "退市" in name or normalized.startswith(("退", "PT")):
        return "delisted"
    if normalized.startswith(("*ST", "ST", "S*ST", "SST")):
        return "st"
    return "listed"


def _is_overseas_fund(name: str, category: str = "") -> bool:
    """判断场内基金是否主要跟踪境外市场。"""

    text = f"{name} {category}".upper()
    overseas_keywords = (
        "海外",
        "QDII",
        "港股",
        "香港",
        "恒生",
        "恒指",
        "纳指",
        "纳斯达克",
        "标普",
        "日经",
        "日本",
        "德国",
        "法国",
        "韩国",
        "中韩",
        "沙特",
        "亚太",
        "印度",
        "美国",
        "中概",
        "全球",
    )
    return any(keyword.upper() in text for keyword in overseas_keywords)


def _exchange_for_code(code: str) -> str:
    """按代码前缀推断交易所后缀。"""

    if code.startswith(("600", "601", "603", "605", "688", "689", "501", "502", "510", "511", "512", "513", "515", "516", "517", "518", "560", "561", "562", "563", "588")):
        return "SH"
    if code.startswith(("000", "001", "002", "003", "300", "301", "150", "159", "160", "161", "162", "163", "164", "165", "166", "167", "168", "169")):
        return "SZ"
    if code.startswith(("8", "4", "920")):
        return "BJ"
    return ""


def _is_stock_code(code: str) -> bool:
    """判断是否为 6 位 A 股股票代码。"""

    return (
        bool(re.fullmatch(r"\d{6}", code))
        and bool(_exchange_for_code(code))
        and not _is_etf_code(code)
        and not _is_lof_code(code)
    )


def _is_etf_code(code: str) -> bool:
    """判断是否为常见沪深 ETF 代码。"""

    return bool(re.fullmatch(r"\d{6}", code)) and not _is_lof_code(code) and code.startswith(("15", "51", "56", "58"))


def _is_lof_code(code: str) -> bool:
    """判断是否为常见沪深 LOF 代码。"""

    return bool(re.fullmatch(r"\d{6}", code)) and code.startswith(
        ("160", "161", "162", "163", "164", "165", "166", "167", "168", "169", "501", "502")
    )


def _cell(row: Any, keys: Sequence[str]) -> str:
    """从 pandas 行按多个候选列名读取字符串。"""

    for key in keys:
        try:
            value = row.get(key)
        except AttributeError:
            value = None
        if value is not None and value is not False and str(value).strip() and str(value).lower() != "nan":
            return str(value).strip()
    return ""


def _first_row_value(row: Any, keys: Sequence[str]) -> str:
    """读取首个存在且非空的列值。"""

    return _cell(row, keys)


def _first_present(values: Mapping[str, str], keys: Sequence[str]) -> str:
    """从字典中读取首个有效值。"""

    for key in keys:
        value = values.get(key, "")
        if value:
            return value
    return ""


def _normalize_listing_date(raw_value: str) -> str:
    """将 AkShare 返回的上市日期归一为 YYYY-MM-DD。"""

    digits = re.sub(r"\D", "", raw_value)
    if len(digits) == 8:
        return f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
    return raw_value


def _normalize_code(raw_value: str) -> str:
    """从带交易所前缀/后缀的代码文本中提取 6 位证券代码。

    Args:
        raw_value: 原始代码字段。

    Returns:
        标准 6 位代码；无法提取时返回原值。
    """

    match = re.search(r"(\d{6})", raw_value)
    return match.group(1) if match else raw_value


def _parse_number(raw_value: object) -> float | None:
    """解析普通数值，支持逗号分隔。"""

    if raw_value is None or raw_value is False:
        return None
    text = str(raw_value).replace(",", "").strip()
    if not text or text.lower() == "nan":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_money_to_yi(raw_value: object) -> float | None:
    """将中文金额单位统一转换为亿元。"""

    if raw_value is None or raw_value is False:
        return None
    text = str(raw_value).replace(",", "").strip()
    if not text or text.lower() == "nan":
        return None
    match = re.fullmatch(r"(-?\d+(?:\.\d+)?)(万亿|亿|万)?", text)
    if match is None:
        return _parse_number(text)
    value = float(match.group(1))
    unit = match.group(2)
    if unit == "万亿":
        return value * 10000
    if unit == "亿":
        return value
    if unit == "万":
        return value / 10000
    return value


def _dedupe_rows(rows: Sequence[dict[str, str]]) -> list[dict[str, str]]:
    """按 symbol 去重并保持原始顺序。"""

    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for row in rows:
        symbol = row["symbol"]
        if symbol in seen:
            continue
        seen.add(symbol)
        result.append(row)
    return result
