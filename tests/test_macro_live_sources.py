from datetime import date
from unittest.mock import Mock, patch
import unittest

import pandas as pd

from src.providers.live_data import OfficialMacroDataProvider


class OfficialMacroSourceParsingTests(unittest.TestCase):
    def setUp(self):
        self.provider = OfficialMacroDataProvider()

    @patch("pandas.read_excel")
    def test_fetch_safe_usd_cny_points_scales_safe_usd_column(self, mock_read_excel):
        mock_read_excel.return_value = pd.DataFrame(
            [
                ["2026-03-25", 689.11],
                ["2026-03-24", 689.43],
                ["2025-02-01", 710.00],
            ],
            columns=["日期", "美元"],
        )
        response = Mock()
        response.content = b"fake-excel"
        response.raise_for_status = Mock()
        self.provider._session.post = Mock(return_value=response)

        points = self.provider._fetch_safe_usd_cny_points(start_date=date(2025, 3, 1))

        self.assertEqual([point.period_label for point in points], ["2026-03-24", "2026-03-25"])
        self.assertEqual(points[-1].value, 6.8911)
        self.assertEqual(points[-1].source_url, self.provider._safe_rmb_history_url())

    @patch("pandas.read_excel")
    def test_fetch_world_bank_commodity_points_parses_monthly_sheet(self, mock_read_excel):
        rows = [[None, None, None, None] for _ in range(9)]
        rows[4] = [None, "Gold", "Crude oil, WTI", "Copper"]
        rows[6] = ["2026M01", 4800.0, 70.1, 12000.0]
        rows[7] = ["2026M02", 5019.97, 64.57, 12951.35]
        rows[8] = ["2025M01", 4500.0, 72.0, 11000.0]
        mock_read_excel.return_value = pd.DataFrame(rows)

        points = self.provider._fetch_world_bank_commodity_points(start_date=date(2026, 1, 1))

        self.assertEqual(points["gold_price"][-1].period_label, "2026-02")
        self.assertEqual(points["gold_price"][-1].value, 5019.97)
        self.assertEqual(points["oil_price"][-1].value, 64.57)
        self.assertEqual(points["copper_price"][-1].value, 12951.35)

    def test_fetch_treasury_10y_daily_points_parses_csv_rows(self):
        response = Mock()
        response.text = "Date,10 Yr\n03/25/2026,4.33\n03/24/2026,4.39\n"
        response.raise_for_status = Mock()
        self.provider._session.get = Mock(return_value=response)

        points = self.provider._fetch_treasury_10y_daily_points(start_date=date(2026, 3, 1))

        self.assertEqual(len(points), 2)
        self.assertEqual(points[0].period_label, "2026-03-24")
        self.assertEqual(points[-1].value, 4.33)

    @patch("pandas.read_excel")
    def test_fetch_treasury_hqm_10y_points_parses_monthly_excel(self, mock_read_excel):
        mock_read_excel.return_value = pd.DataFrame(
            {
                "Date": ["Jan 2026", "Feb 2026"],
                "Unnamed: 1": [0, 0],
                "Unnamed: 2": [0, 0],
                "Unnamed: 3": [0, 0],
                "Unnamed: 4": [4.89, 4.83],
            }
        )

        points = self.provider._fetch_treasury_hqm_10y_points(start_date=date(2026, 1, 1))

        self.assertEqual([point.period_label for point in points], ["2026-01", "2026-02"])
        self.assertEqual(points[-1].value, 4.83)

    def test_fetch_nasdaq_stock_history_points_parses_json_rows(self):
        response = Mock()
        response.raise_for_status = Mock()
        response.json.return_value = {
            "data": {
                "tradesTable": {
                    "rows": [
                        {"date": "03/25/2026", "close": "$123.45"},
                        {"date": "03/24/2026", "close": "$120.00"},
                    ]
                }
            }
        }
        self.provider._session.get = Mock(return_value=response)

        points = self.provider._fetch_nasdaq_stock_history_points(symbol="NVDA", start_date=date(2026, 3, 1))

        self.assertEqual([point.period_label for point in points], ["2026-03-24", "2026-03-25"])
        self.assertEqual(points[-1].value, 123.45)
        self.assertEqual(points[-1].source_url, "https://www.nasdaq.com/market-activity/stocks/nvda/historical")


if __name__ == "__main__":
    unittest.main()
