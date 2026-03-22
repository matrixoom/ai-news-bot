import os
import unittest
from datetime import date

import akshare as ak

from src.providers.live_data import AkshareMarketDataProvider


@unittest.skipUnless(
    os.getenv("RUN_LIVE_HSTECH_DEMO") == "1",
    "Set RUN_LIVE_HSTECH_DEMO=1 to run the live HSTECH data demo.",
)
class HSTECHLiveDemoTests(unittest.TestCase):
    def test_akshare_sina_spot_contains_hstech(self):
        spot = ak.stock_hk_index_spot_sina()
        matched = spot[spot["代码"].astype(str) == "HSTECH"]

        self.assertFalse(matched.empty)
        self.assertIn("恒生科技指数", matched["名称"].astype(str).tolist())

    def test_akshare_sina_daily_and_provider_snapshot(self):
        daily = ak.stock_hk_index_daily_sina(symbol="HSTECH")

        self.assertFalse(daily.empty)
        self.assertIn("close", daily.columns)

        latest_row = daily.iloc[-1]
        print("HSTECH_LATEST_ROW")
        print(daily.tail(3).to_string())

        provider = AkshareMarketDataProvider()
        snapshots = provider.fetch_index_snapshots(
            symbols=["HSTECH"],
            trade_date=date.today(),
        )

        self.assertEqual([item.symbol for item in snapshots], ["HSTECH"])
        self.assertEqual(snapshots[0].currency, "HKD")
        self.assertAlmostEqual(snapshots[0].close_price, float(latest_row["close"]), places=2)
        self.assertGreaterEqual(len(snapshots[0].lookback_closes), 19)


if __name__ == "__main__":
    unittest.main()
