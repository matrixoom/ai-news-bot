"""Market Data 历史数据同步服务。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from .market_data_repository import MarketDataRepository


CommodityLoader = Callable[[], list[dict[str, Any]]]


class MarketDataSyncService:
    """同步 Market Data 历史数据到本地 SQLite。

    Args:
        repository: Market Data 本地仓储。

    Returns:
        同步服务实例。
    """

    def __init__(
        self,
        repository: MarketDataRepository | None = None,
        *,
        wti_loader: CommodityLoader | None = None,
        brent_loader: CommodityLoader | None = None,
        gold_loader: CommodityLoader | None = None,
        silver_loader: CommodityLoader | None = None,
        copper_loader: CommodityLoader | None = None,
    ) -> None:
        self._repository = repository or MarketDataRepository()
        self._wti_loader = wti_loader or _load_wti_rows
        self._brent_loader = brent_loader or _load_brent_rows
        self._gold_loader = gold_loader or _load_gold_rows
        self._silver_loader = silver_loader or _load_silver_rows
        self._copper_loader = copper_loader or _load_copper_rows

    def sync_commodities_history(self) -> dict[str, int]:
        """同步商品类（WTI 原油、布伦特原油）历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        wti_points = self._wti_loader()
        brent_points = self._brent_loader()
        for indicator_id, points in [
            ("wti_crude_oil", wti_points),
            ("brent_crude_oil", brent_points),
        ]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {"wti_crude_oil": len(wti_points), "brent_crude_oil": len(brent_points)}

    def sync_precious_metals_history(self) -> dict[str, int]:
        """同步贵金属类（黄金、白银、铜）历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        gold_points = self._gold_loader()
        silver_points = self._silver_loader()
        copper_points = self._copper_loader()
        for indicator_id, points in [
            ("gold_spot", gold_points),
            ("silver_spot", silver_points),
            ("copper", copper_points),
        ]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {
            "gold_spot": len(gold_points),
            "silver_spot": len(silver_points),
            "copper": len(copper_points),
        }

    def sync_all_history(self) -> dict[str, dict[str, int]]:
        """同步所有市场数据历史。

        Returns:
            每个分类本次写入的点位数量。
        """

        result: dict[str, dict[str, int]] = {}
        result["commodities"] = self.sync_commodities_history()
        result["precious_metals"] = self.sync_precious_metals_history()
        return result


def _load_wti_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取 NYMEX WTI 原油期货日度数据。

    Returns:
        标准化点位列表。
    """

    import akshare as ak

    frame = ak.futures_foreign_hist(symbol="CL")
    return _futures_points(frame, "美元/桶", "akshare_wti")


def _load_brent_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取 ICE 布伦特原油期货日度数据。

    Returns:
        标准化点位列表。
    """

    import akshare as ak

    frame = ak.futures_global_hist_em(symbol="B00Y")
    points: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw_date = row.iloc[0]
        value = _optional_float(row.iloc[3])  # 收盘价
        if value is None:
            continue
        try:
            date_str = str(raw_date)[:10]
        except (TypeError, ValueError):
            continue
        points.append({
            "period_end": date_str,
            "period_label": date_str,
            "value": value,
            "unit": "美元/桶",
            "frequency": "daily",
            "provider_key": "akshare_brent",
            "source_url": "https://data.eastmoney.com/",
            "released_at": "",
        })
    return points


def _load_gold_rows() -> list[dict[str, Any]]:
    """读取黄金历史数据：COMEX 日度期货（2000 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_frame = ak.futures_global_hist_em(symbol="GC00Y")
    daily_points = _global_futures_points(daily_frame, "美元/盎司", "akshare_gold")
    monthly_points = _world_bank_commodity_points("Gold", "美元/盎司", "world_bank_gold")
    return daily_points + monthly_points


def _load_silver_rows() -> list[dict[str, Any]]:
    """读取白银历史数据：COMEX 日度期货（2011 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_frame = ak.futures_global_hist_em(symbol="SI00Y")
    daily_points = _global_futures_points(daily_frame, "美元/盎司", "akshare_silver")
    monthly_points = _world_bank_commodity_points("Silver", "美元/盎司", "world_bank_silver")
    return daily_points + monthly_points


def _load_copper_rows() -> list[dict[str, Any]]:
    """读取铜历史数据：COMEX 日度期货（2011 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_frame = ak.futures_global_hist_em(symbol="HG00Y")
    daily_points = _global_futures_points(daily_frame, "美元/磅", "akshare_copper")
    # World Bank 铜价单位为美元/公吨，需转换为美元/磅（1 mt ≈ 2204.62 lb）
    wb_points = _world_bank_commodity_points("Copper", "美元/磅", "world_bank_copper", scale=1 / 2204.6226218488)
    return daily_points + wb_points


def _futures_points(
    frame, unit: str, provider_key: str
) -> list[dict[str, Any]]:
    """将 futures_foreign_hist 返回的 DataFrame 转为标准化点位。

    Args:
        frame: AkShare 返回的 DataFrame。
        unit: 单位。
        provider_key: 数据来源标识。

    Returns:
        标准化点位列表。
    """

    points: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw_date = row["date"]
        value = _optional_float(row.get("close"))
        if value is None:
            continue
        try:
            if hasattr(raw_date, "strftime"):
                date_str = raw_date.strftime("%Y-%m-%d")
            else:
                date_str = str(raw_date)[:10]
        except (TypeError, ValueError):
            continue
        points.append({
            "period_end": date_str,
            "period_label": date_str,
            "value": value,
            "unit": unit,
            "frequency": "daily",
            "provider_key": provider_key,
            "source_url": "https://akshare.akfamily.xyz/",
            "released_at": "",
        })
    return points


def _global_futures_points(
    frame, unit: str, provider_key: str
) -> list[dict[str, Any]]:
    """将 futures_global_hist_em 返回的 DataFrame 转为标准化点位。

    futures_global_hist_em 列序: 日期(0), 开盘(1), 收盘(2), 最高(3), 最低(4), ...

    Args:
        frame: AkShare 返回的 DataFrame。
        unit: 单位。
        provider_key: 数据来源标识。

    Returns:
        标准化点位列表。
    """

    points: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw_date = row.iloc[0]
        value = _optional_float(row.iloc[3])  # 收盘价
        if value is None:
            continue
        try:
            date_str = str(raw_date)[:10]
        except (TypeError, ValueError):
            continue
        points.append({
            "period_end": date_str,
            "period_label": date_str,
            "value": value,
            "unit": unit,
            "frequency": "daily",
            "provider_key": provider_key,
            "source_url": "https://data.eastmoney.com/",
            "released_at": "",
        })
    return points


def _world_bank_commodity_points(
    commodity_name: str, unit: str, provider_key: str, *, scale: float = 1.0
) -> list[dict[str, Any]]:
    """从 World Bank Pink Sheet 读取商品月度历史数据（1960 年起）。

    Args:
        commodity_name: Pink Sheet 中的商品名称（如 "Silver", "Copper"）。
        unit: 单位。
        provider_key: 数据来源标识。
        scale: 值缩放系数（用于单位转换，如公吨→磅）。

    Returns:
        月度标准化点位列表。
    """

    import calendar
    import re

    import pandas as pd

    url = (
        "https://thedocs.worldbank.org/en/doc/"
        "74e8be41ceb20fa0da750cda2f6b9e4e-0050012026/related/CMO-Historical-Data-Monthly.xlsx"
    )
    try:
        raw = pd.read_excel(url, sheet_name="Monthly Prices", header=None, engine="openpyxl")
    except Exception:
        return []

    commodity_names = [str(v).strip() for v in raw.iloc[4].tolist()]
    data = raw.iloc[6:].copy()
    data.columns = ["period_code"] + commodity_names[1:]

    target_col = None
    for col in data.columns:
        if commodity_name.lower() == str(col).strip().lower():
            target_col = col
            break
    if target_col is None:
        return []

    points: list[dict[str, Any]] = []
    for _, row in data.iterrows():
        period_code = str(row["period_code"]).strip()
        match = re.fullmatch(r"(\d{4})M(\d{2})", period_code)
        if match is None:
            continue
        year = int(match.group(1))
        month = int(match.group(2))
        raw_value = row[target_col]
        value = _optional_float(raw_value)
        if value is None:
            continue
        last_day = calendar.monthrange(year, month)[1]
        period_end = f"{year}-{month:02d}-{last_day}"
        period_label = f"{year}-{month:02d}"
        points.append({
            "period_end": period_end,
            "period_label": period_label,
            "value": round(value * scale, 4),
            "unit": unit,
            "frequency": "monthly",
            "provider_key": provider_key,
            "source_url": "https://www.worldbank.org/en/research/commodity-markets",
            "released_at": "",
        })
    return points


def _optional_float(value: Any) -> float | None:
    """将可空输入转换为浮点数。

    Args:
        value: 原始值。

    Returns:
        转换成功时返回浮点数，否则返回 None。
    """

    import math

    try:
        if value is None or str(value).strip() == "":
            return None
        result = float(value)
        if math.isnan(result):
            return None
        return result
    except (TypeError, ValueError):
        return None
