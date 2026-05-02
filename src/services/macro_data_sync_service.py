"""Macro Data 历史数据同步服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any, Callable, Iterable
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from .macro_data_historical import get_official_quarterly_real_growth, load_historical_gdp_rows
from .macro_data_repository import MacroDataRepository


WorldBankLoader = Callable[[str], list[dict[str, Any]]]
EastmoneyLoader = Callable[[], list[dict[str, Any]]]
ConstantPriceLoader = Callable[[], list[dict[str, Any]]]
HistoricalLoader = Callable[[], list[dict[str, Any]]]


@dataclass(frozen=True)
class ParsedQuarter:
    """解析后的季度标签。

    Args:
        year: 年份。
        quarter: 季度序号，取值 1-4。
        period_end: 季度结束日期。
        period_label: 展示标签，例如 `2026Q1`。

    Returns:
        不返回值；用于同步服务内部传递标准化季度。
    """

    year: int
    quarter: int
    period_end: str
    period_label: str


class MacroDataSyncService:
    """同步可公开获取的 Macro Data 历史数据到本地 SQLite。

    Args:
        repository: Macro Data 本地仓储。
        world_bank_loader: World Bank 指标加载函数，测试中可注入假数据。
        eastmoney_loader: 东方财富 GDP 季度数据加载函数，测试中可注入假数据。
        constant_price_loader: 近年不变价 GDP 加载函数，测试中可注入假数据。

    Returns:
        同步服务实例。
    """

    def __init__(
        self,
        repository: MacroDataRepository | None = None,
        *,
        world_bank_loader: WorldBankLoader | None = None,
        eastmoney_loader: EastmoneyLoader | None = None,
        constant_price_loader: ConstantPriceLoader | None = None,
        historical_loader: HistoricalLoader | None = None,
    ) -> None:
        self._repository = repository or MacroDataRepository()
        self._world_bank_loader = world_bank_loader or _load_world_bank_indicator
        self._eastmoney_loader = eastmoney_loader or _load_eastmoney_gdp_rows
        self._constant_price_loader = constant_price_loader or _load_chinairn_constant_price_rows
        self._historical_loader = historical_loader or load_historical_gdp_rows

    def sync_gdp_history(self) -> dict[str, int]:
        """同步 GDP 总量和增速历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        annual_nominal_points = self._world_bank_points("NY.GDP.MKTP.CN", "nominal_gdp")
        annual_real_points = self._world_bank_points("NY.GDP.MKTP.KN", "real_gdp")

        eastmoney_rows = list(self._eastmoney_loader())
        historical_rows = self._historical_loader()
        all_rows = eastmoney_rows + historical_rows

        quarterly_nominal_points = self._quarterly_nominal_points(all_rows)

        nominal_points = _merge_points(
            annual_nominal_points,
            quarterly_nominal_points,
            self._yearly_points_from_quarters(quarterly_nominal_points, provider_key="eastmoney_derived"),
        )

        chinairn_rows = self._constant_price_loader()
        real_points = self._derive_real_gdp_levels(
            annual_real_points=annual_real_points,
            constant_price_rows=chinairn_rows,
            quarterly_nominal_points=quarterly_nominal_points,
        )

        real_points = self._normalize_real_gdp_base_year(
            real_points=real_points,
            nominal_points=nominal_points,
            base_year=2020,
        )

        nominal_growth_points = self._growth_points_from_totals(nominal_points)
        real_growth_points = self._growth_points_from_totals(real_points)

        self._repository.replace_points(
            "nominal_gdp",
            nominal_points,
            status="live",
            warning_message="",
        )
        self._repository.replace_points(
            "real_gdp",
            real_points,
            status="live",
            warning_message="",
        )
        self._repository.replace_points(
            "nominal_gdp_growth",
            nominal_growth_points,
            status="live",
            warning_message="",
        )
        self._repository.replace_points(
            "real_gdp_growth",
            real_growth_points,
            status="live",
            warning_message="",
        )
        return {
            "nominal_gdp": len(nominal_points),
            "real_gdp": len(real_points),
            "nominal_gdp_growth": len(nominal_growth_points),
            "real_gdp_growth": len(real_growth_points),
        }

    def _world_bank_points(self, indicator: str, indicator_id: str) -> list[dict[str, Any]]:
        """将 World Bank 年度人民币 GDP 转为本地写入点位。

        Args:
            indicator: World Bank 指标代码。
            indicator_id: 本地指标 ID。

        Returns:
            可写入 Repository 的年度点位列表。
        """

        rows = self._world_bank_loader(indicator)
        points = []
        for row in rows:
            year = int(row["year"])
            value_yuan = float(row["value_yuan"])
            points.append(
                _point(
                    period_end=f"{year}-12-31",
                    period_label=str(year),
                    value=round(value_yuan / 100_000_000, 4),
                    unit="亿元",
                    frequency="yearly",
                    provider_key="world_bank",
                    source_url=f"https://api.worldbank.org/v2/country/CHN/indicator/{indicator}",
                )
            )
        return sorted(points, key=lambda point: str(point["period_end"]))

    def _quarterly_nominal_points(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """将东方财富 GDP 季度累计值转为名义 GDP 点位。

        Args:
            rows: 东方财富 GDP 行。

        Returns:
            名义 GDP 季度累计点位。
        """

        cumulative_by_year: dict[int, dict[int, tuple[ParsedQuarter, float]]] = {}
        for row in rows:
            quarter = _parse_china_quarter_label(str(row["label"]))
            value = _optional_float(row.get("nominal_value"))
            if quarter is None or value is None:
                continue
            cumulative_by_year.setdefault(quarter.year, {})[quarter.quarter] = (quarter, value)
        points = []
        for _, quarter_values in sorted(cumulative_by_year.items()):
            previous_cumulative = 0.0
            for quarter_number in sorted(quarter_values):
                quarter, cumulative_value = quarter_values[quarter_number]
                quarter_value = round(cumulative_value - previous_cumulative, 4)
                previous_cumulative = cumulative_value
                points.append(
                    _point(
                        period_end=quarter.period_end,
                        period_label=quarter.period_label,
                        value=quarter_value,
                        unit="亿元",
                        frequency="quarterly",
                        provider_key="eastmoney",
                        source_url="https://data.eastmoney.com/cjsj/gdp.html",
                    )
                )
        return sorted(points, key=lambda point: str(point["period_end"]))

    def _yearly_points_from_quarters(self, quarterly_points: list[dict[str, Any]], *, provider_key: str) -> list[dict[str, Any]]:
        """由完整四个季度当季值生成年度值。

        Args:
            quarterly_points: 当季值点位。
            provider_key: 派生年度值的数据来源标识。

        Returns:
            年度点位，只有四个季度齐全的年份才生成。
        """

        points_by_year: dict[int, list[dict[str, Any]]] = {}
        for point in quarterly_points:
            points_by_year.setdefault(int(str(point["period_end"])[:4]), []).append(point)
        yearly_points = []
        for year, year_points in sorted(points_by_year.items()):
            if len(year_points) != 4:
                continue
            yearly_points.append(
                _point(
                    period_end=f"{year}-12-31",
                    period_label=str(year),
                    value=round(sum(float(point["value"]) for point in year_points), 4),
                    unit=str(year_points[-1]["unit"]),
                    frequency="yearly",
                    provider_key=provider_key,
                    source_url=str(year_points[-1]["source_url"]),
                )
            )
        return yearly_points

    def _direct_real_growth_points(self, rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        """将东方财富/NBS GDP 同比增速转为实际 GDP 增速点位。

        Args:
            rows: 东方财富 GDP 行。

        Returns:
            实际 GDP 同比增速点位。
        """

        points = []
        for row in rows:
            quarter = _parse_china_quarter_label(str(row["label"]))
            value = _optional_float(row.get("real_growth"))
            if quarter is None or value is None:
                continue
            points.append(
                _point(
                    period_end=quarter.period_end,
                    period_label=quarter.period_label,
                    value=value,
                    unit="%",
                    frequency="quarterly",
                    provider_key="eastmoney",
                    source_url="https://data.eastmoney.com/cjsj/gdp.html",
                )
            )
        return sorted(points, key=lambda point: str(point["period_end"]))

    def _derive_real_gdp_levels(
        self,
        *,
        annual_real_points: list[dict[str, Any]],
        constant_price_rows: list[dict[str, Any]],
        quarterly_nominal_points: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """综合 chinairn 不变价当季值和 World Bank 年度实际 GDP 生成实际 GDP 点位。

        chinairn 数据（2022-2024 当季值）直接采用；其他年份按 World Bank
        年度实际 GDP 总额，以名义 GDP 当季占比分配到各个季度。

        Args:
            annual_real_points: World Bank 年度不变价 GDP。
            constant_price_rows: chinairn 可直接获取的近年不变价 GDP 当季值。
            quarterly_nominal_points: 名义 GDP 当季值，用于分配年度实际值。

        Returns:
            实际 GDP 点位。
        """

        direct_quarterly = [
            _point(
                period_end=str(row["period_end"]),
                period_label=str(row["period_label"]),
                value=float(row["value"]),
                unit="亿元",
                frequency="quarterly",
                provider_key="chinairn_nbs_mirror",
                source_url="https://www.chinairn.com/qgjdsj/moref1f2.shtml",
            )
            for row in constant_price_rows
        ]

        nominal_by_q: dict[str, float] = {}
        for pt in quarterly_nominal_points:
            key = str(pt["period_end"])
            nominal_by_q[key] = float(pt["value"])

        annual_by_year: dict[str, float] = {}
        for pt in annual_real_points:
            year = str(pt["period_end"])[:4]
            annual_by_year[year] = float(pt["value"])

        distributed_quarterly: list[dict[str, Any]] = []
        for year, annual_value in sorted(annual_by_year.items()):
            quarters = [f"{year}-03-31", f"{year}-06-30", f"{year}-09-30", f"{year}-12-31"]
            nominals = {q: nominal_by_q.get(q, 0) for q in quarters}
            total_nominal = sum(nominals.values())
            if total_nominal <= 0:
                continue
            for q in quarters:
                share = nominals[q] / total_nominal
                if share > 0:
                    distributed_quarterly.append(
                        _point(
                            period_end=q,
                            period_label=_quarter_from_period_end(q).period_label,
                            value=round(annual_value * share, 4),
                            unit="亿元",
                            frequency="quarterly",
                            provider_key="derived",
                            source_url="",
                        )
                    )

        quarterly = _merge_points(distributed_quarterly, direct_quarterly)

        # 对 World Bank 年度数据尚未覆盖的年份，用官方增速向前链推
        quarterly = self._forward_fill_real_levels(quarterly, nominal_by_q)

        quarterly = self._calibrate_real_levels_with_official_growth(quarterly, direct_quarterly)
        return _merge_points(
            annual_real_points,
            quarterly,
            self._yearly_points_from_quarters(quarterly, provider_key="derived"),
        )

    def _forward_fill_real_levels(
        self,
        quarterly: list[dict[str, Any]],
        nominal_by_q: dict[str, float],
    ) -> list[dict[str, Any]]:
        """对 World Bank 年度数据尚未覆盖的未来年份，用增速链推实际 GDP。

        Args:
            quarterly: 已有的实际 GDP 季度点位。
            nominal_by_q: 名义 GDP 当季值映射。

        Returns:
            扩展后的季度点位列表。
        """

        level_by = {str(pt["period_end"]): float(pt["value"]) for pt in quarterly}
        if not level_by:
            return quarterly

        # 找到已有季度数据的最大年份，和名义数据的最大年份
        max_real_year = max(int(k[:4]) for k in level_by)
        nominal_years = {int(k[:4]) for k in nominal_by_q}
        future_years = sorted(y for y in nominal_years if y > max_real_year)

        for year in future_years:
            for month_day in ["-03-31", "-06-30", "-09-30", "-12-31"]:
                q = f"{year}{month_day}"
                if q in level_by:
                    continue
                prev_q = f"{year - 1}{month_day}"
                if prev_q not in level_by:
                    continue
                growth = get_official_quarterly_real_growth(q)
                if growth is not None:
                    level_by[q] = round(level_by[prev_q] * (1 + growth / 100), 4)
                else:
                    # 无官方增速时，用名义增速近似替代
                    prev_nominal = nominal_by_q.get(prev_q, 0)
                    cur_nominal = nominal_by_q.get(q, 0)
                    if prev_nominal > 0 and cur_nominal > 0:
                        nominal_growth = (cur_nominal / prev_nominal - 1) * 100
                        level_by[q] = round(level_by[prev_q] * (1 + nominal_growth / 100), 4)

        return [
            _point(
                period_end=pe,
                period_label=_quarter_from_period_end(pe).period_label,
                value=v,
                unit="亿元",
                frequency="quarterly",
                provider_key="forward_filled",
                source_url="",
            )
            for pe, v in sorted(level_by.items())
        ]

    def _calibrate_real_levels_with_official_growth(
        self,
        quarterly: list[dict[str, Any]],
        direct_quarterly: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """用官方公布的季度实际增速校准名义占比法推得的实际 GDP 水平。

        以 chinairn 数据为锚，对收录了官方增速的季度，链式反推水平值，
        覆盖名义占比法在结构剧变期（如 2020 COVID）可能产生的偏差。

        Args:
            quarterly: 初步的实际 GDP 季度点位。
            direct_quarterly: chinairn 直接获取的不变价当季值（锚点）。

        Returns:
            校准后的季度点位。
        """

        direct_dates = {str(pt["period_end"]) for pt in direct_quarterly}
        level_by = {str(pt["period_end"]): float(pt["value"]) for pt in quarterly}
        calibrated = dict(level_by)

        # 收集所有有官方增速的季度
        official_quarters: list[str] = []
        for period_end in sorted(level_by):
            growth = get_official_quarterly_real_growth(period_end)
            if growth is not None:
                official_quarters.append(period_end)

        if not official_quarters:
            return quarterly

        # 找出所有 chinairn 锚点季度
        anchors = sorted(direct_dates & set(level_by))

        # 从每个锚点向前后链式反推
        changed = True
        max_iterations = 30
        while changed and max_iterations > 0:
            changed = False
            max_iterations -= 1
            for period_end in official_quarters:
                growth = get_official_quarterly_real_growth(period_end)
                if growth is None:
                    continue
                year = int(period_end[:4])

                # 从上一年的同季度前推
                prev_year_end = f"{year - 1}{period_end[4:]}"
                if prev_year_end in calibrated and period_end not in direct_dates:
                    expected = round(calibrated[prev_year_end] * (1 + growth / 100), 4)
                    if abs(calibrated.get(period_end, 0) - expected) > 0.01:
                        calibrated[period_end] = expected
                        changed = True

                # 从下一年的同季度后推
                next_year_end = f"{year + 1}{period_end[4:]}"
                if next_year_end in calibrated and period_end in direct_dates:
                    continue
                if next_year_end in calibrated and period_end not in direct_dates:
                    growth_next = get_official_quarterly_real_growth(next_year_end)
                    if growth_next is not None:
                        expected = round(calibrated[next_year_end] / (1 + growth_next / 100), 4)
                        if abs(calibrated.get(period_end, 0) - expected) > 0.01:
                            calibrated[period_end] = expected
                            changed = True

        return [
            _point(
                period_end=pe,
                period_label=_quarter_from_period_end(pe).period_label,
                value=v,
                unit="亿元",
                frequency="quarterly",
                provider_key="calibrated",
                source_url="",
            )
            for pe, v in sorted(calibrated.items())
        ]

    def _normalize_real_gdp_base_year(
        self,
        *,
        real_points: list[dict[str, Any]],
        nominal_points: list[dict[str, Any]],
        base_year: int = 2020,
    ) -> list[dict[str, Any]]:
        """将实际 GDP 水平值缩放到与名义 GDP 在基年一致。

        不变价 GDP 应以基年价格衡量，基年处实际 GDP ≈ 名义 GDP。
        chinairn 不变价数据可能使用经济普查修订前的水平，与修订后的
        名义 GDP 在基年存在微小偏差，统一缩放消除该偏差。

        Args:
            real_points: 初步实际 GDP 点位。
            nominal_points: 名义 GDP 点位（含年度值）。
            base_year: 不变价基年，默认 2020。

        Returns:
            缩放后的实际 GDP 点位，增速保持不变。
        """

        base_year_str = f"{base_year}-12-31"
        nominal_base = sum(
            float(point["value"])
            for point in nominal_points
            if str(point["period_end"]) == base_year_str and str(point["frequency"]) == "yearly"
        )
        real_base = sum(
            float(point["value"])
            for point in real_points
            if str(point["period_end"]) == base_year_str and str(point["frequency"]) == "yearly"
        )
        if real_base <= 0 or nominal_base <= 0:
            return real_points
        scale = nominal_base / real_base
        if abs(scale - 1.0) < 0.0001:
            return real_points

        return [
            {
                **point,
                "value": round(float(point["value"]) * scale, 4),
            }
            for point in real_points
        ]

    def _growth_points_from_totals(self, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """基于同周期上一年总量计算名义 GDP 同比增速。

        Args:
            points: GDP 总量点位。

        Returns:
            名义 GDP 同比增速点位。
        """

        by_date = {(str(point["period_end"]), str(point["frequency"])): point for point in points}
        growth_points = []
        for (period_end, frequency), point in sorted(by_date.items()):
            previous = by_date.get((_shift_year(period_end, -1), frequency))
            if previous is None or float(previous["value"]) == 0:
                continue
            quarter = _quarter_from_period_end(period_end)
            growth_points.append(
                _point(
                    period_end=period_end,
                    period_label=quarter.period_label if frequency == "quarterly" else str(period_end)[:4],
                    value=round((float(point["value"]) / float(previous["value"]) - 1) * 100, 2),
                    unit="%",
                    frequency=frequency,
                    provider_key="derived",
                    source_url="",
                )
            )
        return growth_points


def _load_world_bank_indicator(indicator: str) -> list[dict[str, Any]]:
    """从 World Bank API 读取中国年度 GDP 指标。

    Args:
        indicator: World Bank 指标代码。

    Returns:
        含 `year` 与 `value_yuan` 的年度数据列表。
    """

    url = f"https://api.worldbank.org/v2/country/CHN/indicator/{indicator}?format=json&per_page=20000"
    with urlopen(Request(url, headers={"User-Agent": "ai-news-bot/0.1"}), timeout=30) as response:
        payload = json.load(response)
    rows = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
    return [
        {"year": int(row["date"]), "value_yuan": float(row["value"])}
        for row in rows
        if row.get("value") is not None
    ]


def _load_eastmoney_gdp_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取东方财富中国 GDP 季度数据。

    Returns:
        标准化后的 GDP 行列表。
    """

    import akshare as ak

    frame = ak.macro_china_gdp()
    return [
        {
            "label": str(row["季度"]),
            "nominal_value": row["国内生产总值-绝对值"],
            "real_growth": row["国内生产总值-同比增长"],
        }
        for _, row in frame.iterrows()
    ]


def _load_chinairn_constant_price_rows() -> list[dict[str, Any]]:
    """读取可访问的 NBS 不变价 GDP 镜像页面。

    Returns:
        近年不变价 GDP 累计值点位。
    """

    url = "https://www.chinairn.com/qgjdsj/moref1f2.shtml"
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=30) as response:
        html = response.read().decode("utf-8", "ignore")
    soup = BeautifulSoup(html, "html.parser")
    headers = [header.get_text(strip=True) for header in soup.select("table th")][1:]
    for row in soup.select("table tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all("td")]
        if not cells or cells[0] != "国内生产总值(不变价)当季值(亿元)":
            continue
        values = cells[1:]
        points = []
        for label, raw_value in zip(headers, values):
            quarter = _parse_china_quarter_label(label)
            value = _optional_float(raw_value)
            if quarter is None or value is None:
                continue
            points.append({"period_end": quarter.period_end, "period_label": quarter.period_label, "value": value})
        return points
    return []


def _parse_china_quarter_label(label: str) -> ParsedQuarter | None:
    """解析中文季度标签。

    Args:
        label: 形如 `2026年第1季度` 或 `2025年第1-4季度` 的标签。

    Returns:
        解析成功时返回标准季度对象，否则返回 `None`。
    """

    if "年" not in label or "季度" not in label:
        return None
    year_text, quarter_text = label.split("年", 1)
    quarter_text = quarter_text.replace("第", "").replace("季度", "")
    if "-" in quarter_text:
        quarter_text = quarter_text.split("-")[-1]
    quarter_text = {"一": "1", "二": "2", "三": "3", "四": "4"}.get(quarter_text, quarter_text)
    try:
        year = int(year_text)
        quarter = int(quarter_text)
    except ValueError:
        return None
    if quarter not in {1, 2, 3, 4}:
        return None
    month_day_by_quarter = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}
    return ParsedQuarter(
        year=year,
        quarter=quarter,
        period_end=f"{year}-{month_day_by_quarter[quarter]}",
        period_label=f"{year}Q{quarter}",
    )


def _quarter_from_period_end(period_end: str) -> ParsedQuarter:
    """从季度结束日期反推季度标签。

    Args:
        period_end: 周期结束日期。

    Returns:
        标准季度对象。
    """

    year = int(period_end[:4])
    month = int(period_end[5:7])
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(month, 4)
    return ParsedQuarter(year=year, quarter=quarter, period_end=period_end, period_label=f"{year}Q{quarter}")


def _shift_year(period_end: str, years: int) -> str:
    """按年偏移日期字符串。

    Args:
        period_end: 原始日期。
        years: 年份偏移量。

    Returns:
        偏移后的日期字符串。
    """

    return f"{int(period_end[:4]) + years}{period_end[4:]}"


def _optional_float(value: Any) -> float | None:
    """将可空输入转换为浮点数。

    Args:
        value: 原始值。

    Returns:
        转换成功时返回浮点数，否则返回 `None`。
    """

    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _point(
    *,
    period_end: str,
    period_label: str,
    value: float,
    unit: str,
    frequency: str,
    provider_key: str,
    source_url: str,
) -> dict[str, Any]:
    """构造 Repository 可写入点位。

    Args:
        period_end: 周期结束日期。
        period_label: 展示周期标签。
        value: 指标数值。
        unit: 单位。
        frequency: 频率。
        provider_key: 数据源标识。
        source_url: 来源地址。

    Returns:
        点位字典。
    """

    return {
        "period_end": period_end,
        "period_label": period_label,
        "value": value,
        "unit": unit,
        "frequency": frequency,
        "provider_key": provider_key,
        "source_url": source_url,
        "released_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }


def _merge_points(*point_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按周期和频率合并点位，后传入的组覆盖同键旧值。

    Args:
        point_groups: 点位列表集合。

    Returns:
        按日期升序排列的点位。
    """

    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for points in point_groups:
        for point in points:
            merged[(str(point["period_end"]), str(point["frequency"]))] = point
    return [merged[key] for key in sorted(merged)]
