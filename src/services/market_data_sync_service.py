"""Market Data 历史数据同步服务。"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
from typing import Any, Callable

from .market_data_repository import MarketDataRepository


CommodityLoader = Callable[[], list[dict[str, Any]]]
logger = logging.getLogger(__name__)


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
        housing_loader: CommodityLoader | None = None,
    ) -> None:
        self._repository = repository or MarketDataRepository()
        self._wti_loader = wti_loader or _load_wti_rows
        self._brent_loader = brent_loader or _load_brent_rows
        self._gold_loader = gold_loader or _load_gold_rows
        self._silver_loader = silver_loader or _load_silver_rows
        self._copper_loader = copper_loader or _load_copper_rows
        self._housing_loader = housing_loader or _load_housing_rows

    def sync_commodities_history(self) -> dict[str, int]:
        """同步商品类（WTI 原油、布伦特原油）历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        result: dict[str, int] = {}
        for indicator_id in ("wti_crude_oil", "brent_crude_oil"):
            result.update(self.sync_indicator_history(indicator_id))
        return result

    def sync_precious_metals_history(self) -> dict[str, int]:
        """同步贵金属类（黄金、白银、铜）历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        result: dict[str, int] = {}
        for indicator_id in ("gold_spot", "silver_spot", "copper"):
            result.update(self.sync_indicator_history(indicator_id))
        return result

    def sync_real_estate_history(self) -> dict[str, int]:
        """同步房地产类（70 城二手房价格指数）历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        housing_points = self._housing_loader()
        if not housing_points:
            raise ValueError("market indicator returned no data: second_hand_housing")
        self._repository.replace_housing_points(
            "second_hand_housing", housing_points, status="live", warning_message=""
        )
        return {"second_hand_housing": len(housing_points)}

    def sync_all_history(self) -> dict[str, dict[str, int]]:
        """同步所有市场数据历史。

        Returns:
            每个分类本次写入的点位数量。
        """

        result: dict[str, dict[str, int]] = {}
        result["commodities"] = self.sync_commodities_history()
        result["precious_metals"] = self.sync_precious_metals_history()
        result["real_estate"] = self.sync_real_estate_history()
        return result

    def sync_indicator_history(self, indicator_id: str) -> dict[str, int]:
        """仅同步指定图表的历史数据，避免单图刷新被同分类其他上游拖累。

        Args:
            indicator_id: Market Data 图表指标 ID。

        Returns:
            当前指标本次写入的点位数量。
        """

        loaders: dict[str, CommodityLoader] = {
            "wti_crude_oil": self._wti_loader,
            "brent_crude_oil": self._brent_loader,
            "gold_spot": self._gold_loader,
            "silver_spot": self._silver_loader,
            "copper": self._copper_loader,
        }
        if indicator_id == "second_hand_housing":
            return self.sync_real_estate_history()
        loader = loaders.get(indicator_id)
        if loader is None:
            raise ValueError(f"unknown market indicator: {indicator_id}")

        points = loader()
        if not points:
            raise ValueError(f"market indicator returned no data: {indicator_id}")
        self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {indicator_id: len(points)}


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

    return _load_global_or_foreign_futures_points(
        akshare=ak,
        eastmoney_symbol="B00Y",
        sina_symbol="OIL",
        unit="美元/桶",
        provider_key="akshare_brent",
    )


def _load_gold_rows() -> list[dict[str, Any]]:
    """读取黄金历史数据：COMEX 日度期货（2000 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_points = _load_global_or_foreign_futures_points(
        akshare=ak,
        eastmoney_symbol="GC00Y",
        sina_symbol="XAU",
        unit="美元/盎司",
        provider_key="akshare_gold",
    )
    monthly_points = _world_bank_commodity_points("Gold", "美元/盎司", "world_bank_gold")
    return daily_points + monthly_points


def _load_silver_rows() -> list[dict[str, Any]]:
    """读取白银历史数据：COMEX 日度期货（2011 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_points = _load_global_or_foreign_futures_points(
        akshare=ak,
        eastmoney_symbol="SI00Y",
        sina_symbol="XAG",
        unit="美元/盎司",
        provider_key="akshare_silver",
    )
    monthly_points = _world_bank_commodity_points("Silver", "美元/盎司", "world_bank_silver")
    return daily_points + monthly_points


def _load_copper_rows() -> list[dict[str, Any]]:
    """读取铜历史数据：COMEX 日度期货（2011 年起）+ World Bank 月度现货（1960 年起）。

    Returns:
        标准化点位列表（含 daily 和 monthly 两种频率）。
    """

    import akshare as ak

    daily_points = _load_global_or_foreign_futures_points(
        akshare=ak,
        eastmoney_symbol="HG00Y",
        sina_symbol="CAD",
        unit="美元/磅",
        provider_key="akshare_copper",
        sina_scale=1 / 2204.6226218488,
    )
    # World Bank 铜价单位为美元/公吨，需转换为美元/磅（1 mt ≈ 2204.62 lb）
    wb_points = _world_bank_commodity_points("Copper", "美元/磅", "world_bank_copper", scale=1 / 2204.6226218488)
    return daily_points + wb_points


def _futures_points(
    frame, unit: str, provider_key: str, *, scale: float = 1.0
) -> list[dict[str, Any]]:
    """将 futures_foreign_hist 返回的 DataFrame 转为标准化点位。

    Args:
        frame: AkShare 返回的 DataFrame。
        unit: 单位。
        provider_key: 数据来源标识。
        scale: 数值缩放系数；默认保持原值。

    Returns:
        标准化点位列表。
    """

    points: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        raw_date = row["date"]
        raw_value = _optional_float(row.get("close"))
        value = raw_value * scale if raw_value is not None else None
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
        # AkShare 全球期货表的第 3 列是最高价；优先按字段名读取收盘价，
        # 再兼容旧 DataFrame 的固定列序，避免趋势图把最高价误当收盘价。
        value = _optional_float(row.get("收盘", row.get("close")))
        if value is None and len(row) > 2:
            value = _optional_float(row.iloc[2])
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


def _load_global_or_foreign_futures_points(
    *,
    akshare: Any,
    eastmoney_symbol: str,
    sina_symbol: str,
    unit: str,
    provider_key: str,
    sina_scale: float = 1.0,
) -> list[dict[str, Any]]:
    """优先读取东方财富全球期货，失败时切换新浪外盘日线。

    Args:
        akshare: 已导入的 AkShare 模块。
        eastmoney_symbol: 东方财富全球期货代码。
        sina_symbol: 新浪外盘期货代码。
        unit: 标准化后的展示单位。
        provider_key: 主数据源标识。
        sina_scale: 新浪回退值的缩放系数。

    Returns:
        标准化后的日度期货点位列表。
    """

    try:
        frame = akshare.futures_global_hist_em(symbol=eastmoney_symbol)
        points = _global_futures_points(frame, unit, provider_key)
        if points:
            return points
        logger.warning(
            "Eastmoney futures history returned no rows for %s; falling back to Sina %s",
            eastmoney_symbol,
            sina_symbol,
        )
    except Exception as error:
        logger.warning(
            "Eastmoney futures history failed for %s; falling back to Sina %s: %s",
            eastmoney_symbol,
            sina_symbol,
            error,
        )
    frame = akshare.futures_foreign_hist(symbol=sina_symbol)
    return _futures_points(
        frame,
        unit,
        f"{provider_key}_sina",
        scale=sina_scale,
    )


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


# 国家统计局每月发布的 70 个大中城市名单
# 一线城市 (4) + 二线城市 (31) + 三线城市 (35)
_HOUSING_CITIES: list[str] = [
    # 一线城市
    "北京", "上海", "广州", "深圳",
    # 二线城市
    "天津", "石家庄", "太原", "呼和浩特", "沈阳", "大连", "长春", "哈尔滨",
    "南京", "杭州", "宁波", "合肥", "福州", "厦门", "南昌", "济南", "青岛",
    "郑州", "武汉", "长沙", "南宁", "海口", "重庆", "成都", "贵阳", "昆明",
    "西安", "兰州", "西宁", "银川", "乌鲁木齐",
    # 三线城市
    "唐山", "秦皇岛", "包头", "丹东", "锦州", "吉林", "牡丹江",
    "无锡", "徐州", "扬州", "温州", "金华", "蚌埠", "安庆", "泉州", "九江",
    "赣州", "烟台", "济宁", "洛阳", "平顶山", "宜昌", "襄阳", "岳阳", "常德",
    "惠州", "湛江", "韶关", "桂林", "北海", "三亚", "泸州", "南充", "遵义",
    "大理",
]


def _load_housing_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取 70 城二手房价格指数并合并。

    每次调用 macro_china_new_house_price 返回两个城市的数据，
    使用 ThreadPoolExecutor 并发拉取以加速。

    Returns:
        标准化点位列表（含 city 字段）。
    """

    from concurrent.futures import ThreadPoolExecutor, as_completed

    import akshare as ak

    all_points: list[dict[str, Any]] = []

    city_pairs: list[tuple[str, str]] = []
    for i in range(0, len(_HOUSING_CITIES), 2):
        city1 = _HOUSING_CITIES[i]
        city2 = _HOUSING_CITIES[i + 1] if i + 1 < len(_HOUSING_CITIES) else _HOUSING_CITIES[i]
        city_pairs.append((city1, city2))

    def _fetch_pair(c1: str, c2: str) -> list[dict[str, Any]]:
        try:
            frame = ak.macro_china_new_house_price(c1, c2)
        except Exception:
            return []
        return _housing_points_from_frame(frame)

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(_fetch_pair, c1, c2): (c1, c2) for c1, c2 in city_pairs}
        for future in as_completed(futures):
            try:
                points = future.result()
                all_points.extend(points)
            except Exception as e:
                c1, c2 = futures[future]
                print(f"[housing_sync] 获取 {c1}/{c2} 失败: {e}")

    return all_points


def _housing_points_from_frame(frame: Any) -> list[dict[str, Any]]:
    """将 AkShare 70 城房价表转换为同比、环比和全局走势点位。

    AkShare 字段值是以 100 为中性的指数，存储时将同比/环比转为百分比变化，
    并用环比序列从 100 起连续复合，得到跨全历史的房价走势指数。

    Args:
        frame: `macro_china_new_house_price` 返回的 DataFrame。

    Returns:
        含 city 与 metric 维度的标准化点位列表。
    """

    rows_by_city: dict[str, list[dict[str, Any]]] = {}
    for _, row in frame.iterrows():
        try:
            date_val = row["日期"]
            if hasattr(date_val, "strftime"):
                date_str = date_val.strftime("%Y-%m-%d")
            else:
                date_str = str(date_val)[:10]
        except (TypeError, ValueError):
            continue
        city = str(row["城市"]).strip()
        if not city:
            continue
        yoy_index = _optional_float(row.get("二手住宅价格指数-同比"))
        mom_index = _optional_float(row.get("二手住宅价格指数-环比"))
        if yoy_index is None and mom_index is None:
            continue
        rows_by_city.setdefault(city, []).append({
            "period_end": date_str,
            "period_label": date_str[:7],
            "city": city,
            "yoy": round(yoy_index - 100, 4) if yoy_index is not None else None,
            "mom": round(mom_index - 100, 4) if mom_index is not None else None,
        })

    points: list[dict[str, Any]] = []
    for city, city_rows in rows_by_city.items():
        global_index = 100.0
        for item in sorted(city_rows, key=lambda row: str(row["period_end"])):
            if item["yoy"] is not None:
                points.append(_housing_metric_point(item, "yoy", item["yoy"], "%"))
            if item["mom"] is None:
                continue
            points.append(_housing_metric_point(item, "mom", item["mom"], "%"))
            global_index *= 1 + float(item["mom"]) / 100
            points.append(_housing_metric_point(item, "global_index", round(global_index, 4), "指数"))
    return points


def _housing_metric_point(row: dict[str, Any], metric: str, value: float, unit: str) -> dict[str, Any]:
    """构造单条房价口径点位。

    Args:
        row: 已标准化的城市月份基础行。
        metric: 指标口径，取值 `yoy`、`mom`、`global_index`。
        value: 指标值。
        unit: 展示单位。

    Returns:
        可写入房价事实表的点位字典。
    """

    return {
        "period_end": str(row["period_end"]),
        "period_label": str(row["period_label"]),
        "city": str(row["city"]),
        "metric": metric,
        "value": value,
        "unit": unit,
        "frequency": "monthly",
        "provider_key": "akshare_housing",
        "source_url": "https://www.stats.gov.cn/sj/zxfb/",
        "released_at": "",
    }


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
