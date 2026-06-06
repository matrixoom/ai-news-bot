"""A 股与 ETF 行情的 AkShare 同步服务。"""

from __future__ import annotations

from datetime import date, timedelta
import logging
import re
from typing import Any, Callable, Mapping, Sequence

from .stock_market_repository import StockInstrument, StockMarketRepository


DataFrameLoader = Callable[..., Any]
logger = logging.getLogger(__name__)


class StockMarketSyncService:
    """通过 AkShare 同步股票市场标的、日线、概况和财报。

    Args:
        repository: 股票市场本地仓储。
        stock_universe_loader: A 股代码名称加载函数，测试可注入。
        etf_universe_loader: ETF 代码名称加载函数，测试可注入。
        stock_daily_loader: A 股日线加载函数，测试可注入。
        etf_daily_loader: ETF 日线加载函数，测试可注入。

    Returns:
        可执行同步任务的服务实例。
    """

    def __init__(
        self,
        repository: StockMarketRepository | None = None,
        *,
        stock_universe_loader: DataFrameLoader | None = None,
        etf_universe_loader: DataFrameLoader | None = None,
        stock_daily_loader: DataFrameLoader | None = None,
        etf_daily_loader: DataFrameLoader | None = None,
        profile_loader: DataFrameLoader | None = None,
        benefit_loader: DataFrameLoader | None = None,
        cash_loader: DataFrameLoader | None = None,
        debt_loader: DataFrameLoader | None = None,
    ) -> None:
        self._repository = repository or StockMarketRepository()
        self._stock_universe_loader = stock_universe_loader or _ak_stock_universe
        self._etf_universe_loader = etf_universe_loader or _ak_etf_universe
        self._stock_daily_loader = stock_daily_loader or _ak_stock_daily
        self._etf_daily_loader = etf_daily_loader or _ak_etf_daily
        self._profile_loader = profile_loader or _ak_stock_profile
        self._benefit_loader = benefit_loader or _ak_financial_benefit
        self._cash_loader = cash_loader or _ak_financial_cash
        self._debt_loader = debt_loader or _ak_financial_debt

    def sync_universe(self) -> dict[str, Any]:
        """同步 A 股全市场股票和 ETF 标的列表。

        Returns:
            分类型写入数量和可展示的上游告警。
        """

        warnings: list[str] = []
        stock_rows: list[dict[str, str]] = []
        etf_rows: list[dict[str, str]] = []
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

        rows = [*stock_rows, *etf_rows]
        if rows:
            self._repository.upsert_instruments(rows)
        return {
            "stock": len(stock_rows),
            "etf": len(etf_rows),
            "total": len(rows),
            "warnings": warnings,
        }

    def sync_symbol_window(self, instrument: StockInstrument, *, start_date: date, end_date: date) -> dict[str, int]:
        """同步单只股票指定窗口的日线数据，并补足均线计算前置窗口。

        Args:
            instrument: 已持久化的股票或 ETF 标的。
            start_date: 用户请求起始日期。
            end_date: 用户请求结束日期。

        Returns:
            本次写入的日线点位数量。
        """

        if start_date > end_date:
            raise ValueError("start_date must be before end_date")
        # 为 MA120 留出足够的历史缓冲，避免窗口开始处均线断裂。
        padded_start = start_date - timedelta(days=220)
        loader = self._etf_daily_loader if instrument.instrument_type == "etf" else self._stock_daily_loader
        frame = loader(
            symbol=instrument.code,
            start_date=padded_start.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d"),
        )
        bars = _daily_bars_from_frame(frame)
        if not bars:
            raise ValueError(f"stock daily history returned no data: {instrument.symbol}")
        rows = _with_moving_averages(bars)
        count = self._repository.upsert_daily_bars(instrument.symbol, rows)
        return {"daily_bars": count}

    def sync_profile(self, instrument: StockInstrument) -> dict[str, int]:
        """同步单只股票公司概况；ETF 使用基础信息兜底。"""

        if instrument.instrument_type == "etf":
            self._repository.upsert_profile(_etf_profile(instrument))
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
        """同步单只股票财报摘要；ETF 没有公司财报，保持空结果。"""

        if instrument.instrument_type == "etf":
            return {"financial_metrics": 0}
        code = instrument.code
        benefit_frame = self._benefit_loader(symbol=code)
        cash_frame = self._cash_loader(symbol=code)
        debt_frame = self._debt_loader(symbol=code)
        metrics = _financial_metrics_from_frames(benefit_frame, cash_frame, debt_frame)
        count = self._repository.upsert_financial_metrics(instrument.symbol, metrics)
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


def _ak_stock_daily(**kwargs: Any) -> Any:
    """读取 A 股历史日线。"""

    import akshare as ak

    return ak.stock_zh_a_hist(period="daily", adjust="", **kwargs)


def _ak_etf_daily(**kwargs: Any) -> Any:
    """读取 ETF 历史日线。"""

    import akshare as ak

    return ak.fund_etf_hist_em(period="daily", adjust="", **kwargs)


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
            "listing_status": "listed",
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
            "market_board": "ETF",
            "listing_status": "listed",
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
        "summary": f"{instrument.name}，{instrument.market_board}标的。公司概况等待上游数据补充。",
        "provider_key": "fallback",
        "source_url": "",
    }


def _etf_profile(instrument: StockInstrument) -> dict[str, Any]:
    """构造 ETF 概况。"""

    return {
        "symbol": instrument.symbol,
        "company_name": instrument.name,
        "industry": "ETF",
        "sector": "ETF",
        "region": "",
        "listing_date": "",
        "attributes": ["ETF"],
        "summary": f"{instrument.name} 是交易型开放式指数基金，暂无公司财报口径。",
        "provider_key": "akshare_etf",
        "source_url": "https://akshare.akfamily.xyz/",
    }


def _financial_metrics_from_frames(benefit_frame: Any, cash_frame: Any, debt_frame: Any) -> list[dict[str, Any]]:
    """从利润表、现金流量表、资产负债表抽取前端需要的财报指标。"""

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
    return sorted(metrics_by_key.values(), key=lambda item: (str(item["report_period"]), str(item["metric"])))


def _extract_metric_rows(frame: Any, metric: str, label: str, columns: Sequence[str]) -> list[dict[str, Any]]:
    """从单张财报表抽取指定列。"""

    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
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


def _board_for_stock_code(code: str) -> str:
    """按 A 股代码前缀识别交易板块。"""

    if code.startswith(("688", "689")):
        return "科创板"
    if code.startswith(("300", "301")):
        return "创业板"
    if code.startswith(("8", "4", "920")):
        return "北交所"
    if code.startswith(("000", "001", "002", "003")):
        return "深市主板"
    if code.startswith(("600", "601", "603", "605")):
        return "沪市主板"
    return "A股"


def _exchange_for_code(code: str) -> str:
    """按代码前缀推断交易所后缀。"""

    if code.startswith(("600", "601", "603", "605", "688", "689", "510", "511", "512", "513", "515", "516", "517", "518", "560", "561", "562", "563", "588")):
        return "SH"
    if code.startswith(("000", "001", "002", "003", "300", "301", "150", "159", "160", "161", "162")):
        return "SZ"
    if code.startswith(("8", "4", "920")):
        return "BJ"
    return ""


def _is_stock_code(code: str) -> bool:
    """判断是否为 6 位 A 股股票代码。"""

    return bool(re.fullmatch(r"\d{6}", code)) and bool(_exchange_for_code(code)) and not _is_etf_code(code)


def _is_etf_code(code: str) -> bool:
    """判断是否为常见沪深 ETF 代码。"""

    return bool(re.fullmatch(r"\d{6}", code)) and code.startswith(("15", "16", "51", "56", "58"))


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
