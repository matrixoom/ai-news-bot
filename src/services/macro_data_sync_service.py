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
MoneySupplyLoader = Callable[[], list[dict[str, Any]]]
CpiMonthlyLoader = Callable[[], list[dict[str, Any]]]
PpiLoader = Callable[[], list[dict[str, Any]]]
PmiLoader = Callable[[], list[dict[str, Any]]]
NonManPmiLoader = Callable[[], list[dict[str, Any]]]
TradeLoader = Callable[[], list[dict[str, Any]]]
CnbsLoader = Callable[[], list[dict[str, Any]]]
NewLoansLoader = Callable[[], list[dict[str, Any]]]
SocialFinancingLoader = Callable[[], list[dict[str, Any]]]
PbocCreditBreakdownLoader = Callable[[], list[dict[str, Any]]]


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
        money_supply_loader: MoneySupplyLoader | None = None,
        cpi_monthly_loader: CpiMonthlyLoader | None = None,
        ppi_loader: PpiLoader | None = None,
        pmi_loader: PmiLoader | None = None,
        non_man_pmi_loader: NonManPmiLoader | None = None,
        trade_loader: TradeLoader | None = None,
        cnbs_loader: CnbsLoader | None = None,
        new_loans_loader: NewLoansLoader | None = None,
        social_financing_loader: SocialFinancingLoader | None = None,
        pboc_credit_breakdown_loader: PbocCreditBreakdownLoader | None = None,
    ) -> None:
        self._repository = repository or MacroDataRepository()
        self._world_bank_loader = world_bank_loader or _load_world_bank_indicator
        self._eastmoney_loader = eastmoney_loader or _load_eastmoney_gdp_rows
        self._constant_price_loader = constant_price_loader or _load_chinairn_constant_price_rows
        self._historical_loader = historical_loader or load_historical_gdp_rows
        self._money_supply_loader = money_supply_loader or _load_money_supply_rows
        self._cpi_monthly_loader = cpi_monthly_loader or _load_cpi_monthly_rows
        self._ppi_loader = ppi_loader or _load_ppi_rows
        self._pmi_loader = pmi_loader or _load_pmi_rows
        self._non_man_pmi_loader = non_man_pmi_loader or _load_non_man_pmi_rows
        self._trade_loader = trade_loader or _load_trade_rows
        self._cnbs_loader = cnbs_loader or _load_cnbs_rows
        self._new_loans_loader = new_loans_loader or _load_new_loans_rows
        self._social_financing_loader = social_financing_loader or _load_social_financing_rows
        self._pboc_credit_breakdown_loader = pboc_credit_breakdown_loader or _load_pboc_credit_breakdown_rows

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

    def sync_all_history(self) -> dict[str, dict[str, int]]:
        """同步所有宏观指标历史数据。

        Returns:
            每个分类本次写入的点位数量。
        """

        result: dict[str, dict[str, int]] = {}
        result["gdp"] = self.sync_gdp_history()
        result["currency"] = self.sync_currency_history()
        result["prices"] = self.sync_prices_history()
        result["climate"] = self.sync_climate_history()
        result["trade"] = self.sync_trade_history()
        result["credit"] = self.sync_credit_history()
        result["credit_breakdown"] = self.sync_credit_breakdown_history()
        return result

    def sync_currency_history(self) -> dict[str, int]:
        """同步货币供应量 M0/M1/M2 历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        rows = self._money_supply_loader()
        m0_points = self._money_supply_points(rows, "m0")
        m1_points = self._money_supply_points(rows, "m1")
        m2_points = self._money_supply_points(rows, "m2")
        for indicator_id, points in [("m0", m0_points), ("m1", m1_points), ("m2", m2_points)]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {"m0": len(m0_points), "m1": len(m1_points), "m2": len(m2_points)}

    def sync_prices_history(self) -> dict[str, int]:
        """同步物价 CPI/PPI 历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        cpi_rows = self._cpi_monthly_loader()
        ppi_rows = self._ppi_loader()
        cpi_points = self._monthly_points(cpi_rows, "cpi", "%", "akshare_cpi")
        ppi_points = self._monthly_points(ppi_rows, "ppi", "%", "akshare_ppi")
        for indicator_id, points in [("cpi", cpi_points), ("ppi", ppi_points)]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {"cpi": len(cpi_points), "ppi": len(ppi_points)}

    def sync_climate_history(self) -> dict[str, int]:
        """同步景气 PMI 历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        pmi_rows = self._pmi_loader()
        non_man_rows = self._non_man_pmi_loader()
        pmi_points = self._monthly_points(pmi_rows, "manufacturing_pmi", "%", "akshare_pmi")
        non_man_points = self._monthly_points(non_man_rows, "non_manufacturing_pmi", "%", "akshare_non_man_pmi")
        for indicator_id, points in [("manufacturing_pmi", pmi_points), ("non_manufacturing_pmi", non_man_points)]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {"manufacturing_pmi": len(pmi_points), "non_manufacturing_pmi": len(non_man_points)}

    def sync_trade_history(self) -> dict[str, int]:
        """同步外贸进出口历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        rows = self._trade_loader()
        exports_points: list[dict[str, Any]] = []
        imports_points: list[dict[str, Any]] = []
        for row in rows:
            period_end = str(row["period_end"])
            year = int(period_end[:4])
            exports_val = float(row["exports"])
            imports_val = float(row["imports"])
            exports_points.append(
                _point(
                    period_end=period_end,
                    period_label=_month_label(period_end),
                    value=_usd_thousands_to_yi_wan(year, exports_val),
                    unit="亿元",
                    frequency="monthly",
                    provider_key="akshare_hgjck",
                    source_url="https://data.eastmoney.com/cjsj/hgjck.html",
                )
            )
            imports_points.append(
                _point(
                    period_end=period_end,
                    period_label=_month_label(period_end),
                    value=_usd_thousands_to_yi_wan(year, imports_val),
                    unit="亿元",
                    frequency="monthly",
                    provider_key="akshare_hgjck",
                    source_url="https://data.eastmoney.com/cjsj/hgjck.html",
                )
            )
        for indicator_id, points in [("exports", exports_points), ("imports", imports_points)]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {"exports": len(exports_points), "imports": len(imports_points)}

    def sync_credit_history(self) -> dict[str, int]:
        """同步信贷/杠杆率/社融历史数据。

        Returns:
            每个指标本次写入的点位数量。
        """

        cnbs_rows = self._cnbs_loader()
        household_leverage_points: list[dict[str, Any]] = []
        corporate_leverage_points: list[dict[str, Any]] = []
        for row in cnbs_rows:
            household_leverage_points.append(
                _point(
                    period_end=str(row["period_end"]),
                    period_label=str(row["period_label"]),
                    value=float(row["household_leverage"]),
                    unit="%",
                    frequency="quarterly",
                    provider_key="akshare_cnbs",
                    source_url="https://www.nifd.cn/",
                )
            )
            corporate_leverage_points.append(
                _point(
                    period_end=str(row["period_end"]),
                    period_label=str(row["period_label"]),
                    value=float(row["corporate_leverage"]),
                    unit="%",
                    frequency="quarterly",
                    provider_key="akshare_cnbs",
                    source_url="https://www.nifd.cn/",
                )
            )

        new_loans_rows = self._new_loans_loader()
        new_loans_points = self._monthly_points(new_loans_rows, "new_rmb_loans", "亿元", "akshare_new_loans")

        sf_rows = self._social_financing_loader()
        sf_points = self._monthly_points(sf_rows, "social_financing", "亿元", "akshare_social_financing")

        for indicator_id, points in [
            ("household_leverage_ratio", household_leverage_points),
            ("corporate_leverage_ratio", corporate_leverage_points),
            ("new_rmb_loans", new_loans_points),
            ("social_financing", sf_points),
        ]:
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {
            "household_leverage_ratio": len(household_leverage_points),
            "corporate_leverage_ratio": len(corporate_leverage_points),
            "new_rmb_loans": len(new_loans_points),
            "social_financing": len(sf_points),
        }

    def sync_credit_breakdown_history(self) -> dict[str, int]:
        """同步新增人民币贷款按部门与期限的细分数据（来源：人民银行金融机构人民币信贷收支表）。

        从人民银行官网下载各年 Excel 表，提取住户短期/中长期、企业短期/中长期
        贷款余额，计算月度环比增量作为当月新增贷款。

        Returns:
            每个指标本次写入的点位数量。
        """

        rows = self._pboc_credit_breakdown_loader()
        indicator_points: dict[str, list[dict[str, Any]]] = {
            "household_short_term_loans": [],
            "household_long_term_loans": [],
            "corporate_short_term_loans": [],
            "corporate_long_term_loans": [],
        }
        key_map = {
            "household_short_term": "household_short_term_loans",
            "household_long_term": "household_long_term_loans",
            "corporate_short_term": "corporate_short_term_loans",
            "corporate_long_term": "corporate_long_term_loans",
        }
        for row in rows:
            period_end = str(row["period_end"])
            for row_key, indicator_id in key_map.items():
                value = _optional_float(row.get(row_key))
                if value is None:
                    continue
                indicator_points[indicator_id].append(
                    _point(
                        period_end=period_end,
                        period_label=_month_label(period_end),
                        value=value,
                        unit="亿元",
                        frequency="monthly",
                        provider_key="pboc_credit_balance",
                        source_url="http://www.pbc.gov.cn/diaochatongjisi/116219/116319/index.html",
                    )
                )
        for indicator_id, points in indicator_points.items():
            self._repository.replace_points(indicator_id, points, status="live", warning_message="")
        return {k: len(v) for k, v in indicator_points.items()}

    def _money_supply_points(self, rows: list[dict[str, Any]], series_key: str) -> list[dict[str, Any]]:
        """从货币供应量行中提取单条序列的点位。

        Args:
            rows: 货币供应量行。
            series_key: 取值 `m0`、`m1`、`m2`。

        Returns:
            可写入 Repository 的月度点位列表。
        """

        title_map = {"m0": "M0", "m1": "M1", "m2": "M2"}
        points: list[dict[str, Any]] = []
        for row in rows:
            period_end = str(row["period_end"])
            value = _optional_float(row.get(series_key))
            if value is None:
                continue
            points.append(
                _point(
                    period_end=period_end,
                    period_label=_month_label(period_end),
                    value=value,
                    unit="亿元",
                    frequency="monthly",
                    provider_key="akshare_money_supply",
                    source_url="https://data.eastmoney.com/cjsj/hbgyl.html",
                )
            )
        return points

    def _monthly_points(
        self, rows: list[dict[str, Any]], indicator_id: str, unit: str, provider_key: str
    ) -> list[dict[str, Any]]:
        """将通用月度行转换为可写入点位。

        Args:
            rows: 含 `period_end` 和 `value` 的月度行。
            indicator_id: 指标 ID。
            unit: 单位。
            provider_key: 数据来源标识。

        Returns:
            可写入 Repository 的点位列表。
        """

        points: list[dict[str, Any]] = []
        for row in rows:
            period_end = str(row["period_end"])
            value = _optional_float(row.get("value"))
            if value is None:
                continue
            points.append(
                _point(
                    period_end=period_end,
                    period_label=_month_label(period_end),
                    value=value,
                    unit=unit,
                    frequency="monthly",
                    provider_key=provider_key,
                    source_url="",
                )
            )
        return points

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


def _load_money_supply_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国货币供应量月度数据。

    Returns:
        含 M0/M1/M2 余额的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_money_supply()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        rows.append(
            {
                "period_end": month_end,
                "m2": _optional_float(row.iloc[1]),
                "m1": _optional_float(row.iloc[4]),
                "m0": _optional_float(row.iloc[7]),
            }
        )
    return rows


def _load_cpi_monthly_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国 CPI 月度同比数据。

    Returns:
        含 CPI 同比增速的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_cpi_monthly()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        date_val = row.iloc[1]
        if not hasattr(date_val, "year"):
            continue
        period_end = f"{date_val.year}-{date_val.month:02d}-{_month_last_day(date_val.year, date_val.month)}"
        value = _optional_float(row.iloc[2])
        if value is None:
            continue
        rows.append({"period_end": period_end, "value": value})
    return rows


def _load_ppi_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国 PPI 月度同比数据。

    Returns:
        含 PPI 同比增速的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_ppi()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        value = _optional_float(row.iloc[2])
        if value is None:
            continue
        rows.append({"period_end": month_end, "value": value})
    return rows


def _load_pmi_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国制造业 PMI 月度数据。

    Returns:
        含制造业 PMI 指数值的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_pmi()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        value = _optional_float(row.iloc[1])
        if value is None:
            continue
        rows.append({"period_end": month_end, "value": value})
    return rows


def _load_non_man_pmi_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国非制造业 PMI 月度数据。

    Returns:
        含非制造业 PMI 指数值的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_non_man_pmi()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        date_val = row.iloc[1]
        if not hasattr(date_val, "year"):
            continue
        period_end = f"{date_val.year}-{date_val.month:02d}-{_month_last_day(date_val.year, date_val.month)}"
        value = _optional_float(row.iloc[2])
        if value is None:
            continue
        rows.append({"period_end": period_end, "value": value})
    return rows


def _load_trade_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国进出口月度数据（美元计价）。

    Returns:
        含出口和进口金额（千美元）的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_hgjck()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        exports = _optional_float(row.iloc[1])
        imports = _optional_float(row.iloc[4])
        if exports is None or imports is None:
            continue
        rows.append({"period_end": month_end, "exports": exports, "imports": imports})
    return rows


def _load_cnbs_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国宏观杠杆率季度数据。

    Returns:
        含居民杠杆率和企业杠杆率的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_cnbs()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        label = str(row.iloc[0]).strip()
        quarter = _parse_cnbs_quarter_label(label)
        if quarter is None:
            continue
        household = _optional_float(row.iloc[1])
        corporate = _optional_float(row.iloc[2])
        if household is None or corporate is None:
            continue
        rows.append(
            {
                "period_end": quarter["period_end"],
                "period_label": quarter["period_label"],
                "household_leverage": household,
                "corporate_leverage": corporate,
            }
        )
    return rows


def _load_new_loans_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国新增人民币贷款月度数据。

    Returns:
        含当月新增贷款的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_new_financial_credit()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        value = _optional_float(row.iloc[1])
        if value is None:
            continue
        rows.append({"period_end": month_end, "value": value})
    return rows


def _load_social_financing_rows() -> list[dict[str, Any]]:
    """通过 AkShare 读取中国社会融资规模月度数据。

    Returns:
        含当月社融增量的标准化行列表。
    """

    import akshare as ak

    frame = ak.macro_china_wbck()
    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        month_end = _parse_chinese_month_label(str(row.iloc[0]))
        if month_end is None:
            continue
        value = _optional_float(row.iloc[1])
        if value is None:
            continue
        rows.append({"period_end": month_end, "value": value})
    return rows


def _load_pboc_credit_breakdown_rows() -> list[dict[str, Any]]:
    """从人民银行官网下载各年金融机构人民币信贷收支表 Excel 文件，
    提取住户短期/中长期、企业短期/中长期贷款余额，计算月度环比增量。

    数据覆盖 2015-2026 年（Excel 格式自此年开始提供）。

    Returns:
        含 household_short_term/household_long_term/corporate_short_term/
        corporate_long_term 当月新增值的标准化行列表。
    """

    import io
    import re

    import pandas as pd
    import requests

    base = "http://www.pbc.gov.cn"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    # 各年统计页面 URL（2015 起采用新 ID 体系）
    _YEAR_PAGES: dict[int, str] = {
        2026: f"{base}/diaochatongjisi/116219/116319/2026ntjsj/index.html",
        2025: f"{base}/diaochatongjisi/116219/116319/5570903/index.html",
        2024: f"{base}/diaochatongjisi/116219/116319/5225358/index.html",
        2023: f"{base}/diaochatongjisi/116219/116319/4780803/index.html",
        2022: f"{base}/diaochatongjisi/116219/116319/4458449/index.html",
        2021: f"{base}/diaochatongjisi/116219/116319/4184109/index.html",
        2020: f"{base}/diaochatongjisi/116219/116319/3959050/index.html",
        2019: f"{base}/diaochatongjisi/116219/116319/3750274/index.html",
        2018: f"{base}/diaochatongjisi/116219/116319/3471721/index.html",
        2017: f"{base}/diaochatongjisi/116219/116319/3245697/index.html",
        2016: f"{base}/diaochatongjisi/116219/116319/3013637/index.html",
        2015: f"{base}/diaochatongjisi/116219/116319/2161324/index.html",
    }

    # 收集所有年月的贷款余额原始数据
    # outstanding[(year, month)] = {hh_short, hh_long, corp_short, corp_long}
    outstanding: dict[tuple[int, int], dict[str, float]] = {}

    for year in sorted(_YEAR_PAGES):
        try:
            year_page = _YEAR_PAGES[year]
            resp = requests.get(year_page, headers=headers, timeout=30)
            resp.encoding = "utf-8"
            soup = BeautifulSoup(resp.text, "html.parser")

            # 找到"金融机构信贷收支统计"链接
            credit_link = None
            for a in soup.find_all("a"):
                text = a.get_text(strip=True)
                if "信贷收支" in text:
                    credit_link = a.get("href", "")
                    break
            if not credit_link:
                continue

            credit_url = credit_link if credit_link.startswith("http") else base + credit_link
            resp2 = requests.get(credit_url, headers=headers, timeout=30)
            resp2.encoding = "utf-8"
            soup2 = BeautifulSoup(resp2.text, "html.parser")

            # 收集所有 Excel 链接，第 5 个是"金融机构人民币信贷收支表"
            xls_links = []
            for a in soup2.find_all("a"):
                href = a.get("href", "")
                if ".xls" in href.lower():
                    xls_links.append(href)

            if len(xls_links) < 5:
                continue

            file_url = xls_links[4] if xls_links[4].startswith("http") else base + xls_links[4]
            resp3 = requests.get(file_url, headers=headers, timeout=30)
            df = pd.read_excel(io.BytesIO(resp3.content), header=None)

            year_data = _parse_credit_balance_sheet(df, year)
            for (y, m), values in year_data.items():
                outstanding[(y, m)] = values
        except Exception:
            continue

    # 计算月度环比增量（当月新增 = 当月余额 - 上月余额）
    rows: list[dict[str, Any]] = []
    sorted_months = sorted(outstanding.keys())
    for i, (year, month) in enumerate(sorted_months):
        if i == 0:
            continue  # 第一个月没有上月数据
        prev_year, prev_month = sorted_months[i - 1]
        # 确保是相邻月份
        expected_prev = (year - 1, 12) if month == 1 else (year, month - 1)
        if (prev_year, prev_month) != expected_prev:
            continue  # 月份不连续则跳过
        cur = outstanding[(year, month)]
        prev = outstanding[(prev_year, prev_month)]
        period_end = f"{year}-{month:02d}-{_month_last_day(year, month)}"
        rows.append(
            {
                "period_end": period_end,
                "household_short_term": round(cur["hh_short"] - prev["hh_short"], 2),
                "household_long_term": round(cur["hh_long"] - prev["hh_long"], 2),
                "corporate_short_term": round(cur["corp_short"] - prev["corp_short"], 2),
                "corporate_long_term": round(cur["corp_long"] - prev["corp_long"], 2),
            }
        )
    return rows


def _parse_credit_balance_sheet(df: "pd.DataFrame", expected_year: int) -> dict[tuple[int, int], dict[str, float]]:
    """解析人民银行金融机构人民币信贷收支表 Excel。

    通过扫描第一列的行标签识别四个目标指标所在行，再读取各月数值列。

    Args:
        df: 不带表头的原始 DataFrame。
        expected_year: 预期年份，用于解析列标题。

    Returns:
        {(year, month): {"hh_short": ..., "hh_long": ..., "corp_short": ..., "corp_long": ...}}
    """

    import re

    import pandas as pd

    # 找到列标题行（含 "项目" 的行）
    header_row = -1
    month_columns: dict[int, int] = {}  # col_index -> month_number
    for i in range(min(10, df.shape[0])):
        for j in range(df.shape[1]):
            val = str(df.iloc[i, j]) if pd.notna(df.iloc[i, j]) else ""
            if "项目" in val:
                header_row = i
                break
        if header_row >= 0:
            break

    if header_row < 0:
        return {}

    # 解析列标题，映射到月份
    for j in range(1, df.shape[1]):
        val = str(df.iloc[header_row, j]) if pd.notna(df.iloc[header_row, j]) else ""
        match = re.match(r"(\d{4})\.(\d{1,2})", val)
        if match:
            year = int(match.group(1))
            month = int(match.group(2))
            if year == expected_year:
                month_columns[j] = month

    if not month_columns:
        return {}

    # 扫描行标签，跟踪当前所处的节
    in_household = False
    in_corporate = False
    target_rows: dict[str, int] = {}  # key -> row_index

    for i in range(header_row + 1, df.shape[0]):
        label = str(df.iloc[i, 0]).strip() if pd.notna(df.iloc[i, 0]) else ""

        if "住户贷款" in label or "Loans to Households" in label:
            in_household = True
            in_corporate = False
            continue
        if ("企（事）业单位贷款" in label
                or "非金融企业及机关团体贷款" in label
                or "Loans to Non-financial Enterprises" in label):
            in_household = False
            in_corporate = True
            continue
        if "非银行业金融机构贷款" in label or "Loans to Non-banking Financial" in label:
            in_household = False
            in_corporate = False
            continue
        if "境外贷款" in label or "Overseas Loans" in label:
            in_household = False
            in_corporate = False
            continue

        if in_household and "短期贷款" in label and "Short-term" in label:
            target_rows["hh_short"] = i
        elif in_household and "中长期贷款" in label and "Mid" in label:
            target_rows["hh_long"] = i
        elif in_corporate and "短期贷款" in label and "Short-term" in label:
            target_rows["corp_short"] = i
        elif in_corporate and "中长期贷款" in label and "Mid" in label:
            target_rows["corp_long"] = i

    # 提取数据
    result: dict[tuple[int, int], dict[str, float]] = {}
    for col_idx, month in month_columns.items():
        values: dict[str, float] = {}
        for key, row_idx in target_rows.items():
            raw = df.iloc[row_idx, col_idx]
            if pd.isna(raw) or str(raw).strip() == "":
                break
            try:
                values[key] = float(raw)
            except (ValueError, TypeError):
                break
        if len(values) == 4:
            result[(expected_year, month)] = values

    return result


def _parse_cnbs_quarter_label(label: str) -> dict[str, str] | None:
    """解析 CNBS 季度标签。

    Args:
        label: 形如 `2005-03` 或 `2024-12` 的标签。

    Returns:
        含 period_end 和 period_label 的字典，解析失败返回 None。
    """

    try:
        year = int(label[:4])
        month = int(label[5:7])
    except (ValueError, IndexError):
        return None
    quarter = {3: 1, 6: 2, 9: 3, 12: 4}.get(month)
    if quarter is None:
        return None
    month_day = {1: "03-31", 2: "06-30", 3: "09-30", 4: "12-31"}[quarter]
    return {"period_end": f"{year}-{month_day}", "period_label": f"{year}Q{quarter}"}


def _parse_chinese_month_label(label: str) -> str | None:
    """解析中文月度标签为月末日期。

    Args:
        label: 形如 `2026年03月份` 的标签。

    Returns:
        形如 `2026-03-31` 的月末日期，解析失败返回 None。
    """

    import re

    match = re.match(r"(\d{4})\D*(\d{1,2})\D*", label)
    if not match:
        return None
    year = int(match.group(1))
    month = int(match.group(2))
    if month < 1 or month > 12:
        return None
    return f"{year}-{month:02d}-{_month_last_day(year, month)}"


def _month_last_day(year: int, month: int) -> str:
    """返回指定年月的最后一天。

    Args:
        year: 年份。
        month: 月份。

    Returns:
        形如 `31` 的日期字符串。
    """

    import calendar

    return str(calendar.monthrange(year, month)[1])


# 近似的美元兑人民币年平均汇率，用于将贸易数据从千美元转换为亿元
_USD_CNY_YEARLY: dict[int, float] = {
    2008: 6.95,
    2009: 6.83,
    2010: 6.77,
    2011: 6.46,
    2012: 6.31,
    2013: 6.15,
    2014: 6.16,
    2015: 6.28,
    2016: 6.64,
    2017: 6.75,
    2018: 6.62,
    2019: 6.91,
    2020: 6.90,
    2021: 6.45,
    2022: 6.73,
    2023: 7.08,
    2024: 7.12,
    2025: 7.17,
    2026: 7.25,
}


def _usd_thousands_to_yi_wan(year: int, value_usd_thousands: float) -> float:
    """将千美元转换为亿元。

    Args:
        year: 数据年份。
        value_usd_thousands: 千美元金额。

    Returns:
        亿元金额。
    """

    rate = _USD_CNY_YEARLY.get(year, 7.0)
    return round(value_usd_thousands * rate / 100_000, 4)


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


def _month_label(period_end: str) -> str:
    """从月末日期生成月度展示标签。

    Args:
        period_end: 形如 `2026-03-31` 的月末日期。

    Returns:
        形如 `2026-03` 的月度标签。
    """

    return period_end[:7]


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
