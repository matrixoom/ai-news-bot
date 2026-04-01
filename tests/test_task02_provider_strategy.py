import unittest
from pathlib import Path

from src.providers import (
    CategoryStrategy,
    FeasibilityLevel,
    MacroDataProvider,
    MarketDataProvider,
    NewsProvider,
    ProviderAvailability,
    ProviderStatus,
    ResearchProvider,
    SearchProvider,
    StrategyCategory,
    build_provider_strategy,
)


class Task02DocumentationTests(unittest.TestCase):
    def test_task02_main_doc_links_all_deliverables(self):
        content = Path("tasks/02-data-source-feasibility-and-provider-strategy.md").read_text(encoding="utf-8")

        self.assertIn("Completed for design phase.", content)
        self.assertIn("02-data-source-matrix.md", content)
        self.assertIn("02-provider-contracts.md", content)
        self.assertIn("02-free-data-feasibility-conclusion.md", content)

    def test_task02_supporting_docs_exist(self):
        expected_paths = [
            Path("tasks/02-data-source-matrix.md"),
            Path("tasks/02-provider-contracts.md"),
            Path("tasks/02-free-data-feasibility-conclusion.md"),
        ]

        for path in expected_paths:
            self.assertTrue(path.exists(), f"Missing deliverable: {path}")


class ProviderStrategyTests(unittest.TestCase):
    def test_strategy_covers_all_required_categories(self):
        strategies = build_provider_strategy()
        categories = {strategy.category for strategy in strategies}

        self.assertEqual(
            categories,
            {
                StrategyCategory.TECHNOLOGY_NEWS,
                StrategyCategory.FINANCE_NEWS,
                StrategyCategory.POLICY_NEWS,
                StrategyCategory.SEARCH_HOTSPOTS,
                StrategyCategory.MACRO_INDICATORS,
                StrategyCategory.BROAD_MARKET_INDICES,
                StrategyCategory.EVENT_OUTLOOK,
            },
        )

    def test_each_category_has_free_primary_fallback_and_degradation(self):
        for strategy in build_provider_strategy():
            self.assertIsInstance(strategy, CategoryStrategy)
            self.assertTrue(strategy.primary_source.is_free, strategy.category)
            self.assertGreaterEqual(len(strategy.fallback_sources), 1, strategy.category)
            self.assertTrue(strategy.degradation_mode.strip(), strategy.category)
            self.assertIn(
                strategy.free_feasibility,
                {FeasibilityLevel.VIABLE, FeasibilityLevel.VIABLE_WITH_GUARDRAILS},
            )

    def test_provider_contract_mapping_matches_category(self):
        strategies = {strategy.category: strategy for strategy in build_provider_strategy()}

        self.assertEqual(strategies[StrategyCategory.TECHNOLOGY_NEWS].provider_contract, "NewsProvider")
        self.assertEqual(strategies[StrategyCategory.FINANCE_NEWS].provider_contract, "NewsProvider")
        self.assertEqual(strategies[StrategyCategory.POLICY_NEWS].provider_contract, "NewsProvider")
        self.assertEqual(strategies[StrategyCategory.SEARCH_HOTSPOTS].provider_contract, "SearchProvider")
        self.assertEqual(strategies[StrategyCategory.MACRO_INDICATORS].provider_contract, "MacroDataProvider")
        self.assertEqual(strategies[StrategyCategory.BROAD_MARKET_INDICES].provider_contract, "MarketDataProvider")
        self.assertEqual(strategies[StrategyCategory.EVENT_OUTLOOK].provider_contract, "ResearchProvider")


class ProviderContractTests(unittest.TestCase):
    def test_provider_status_keeps_healthcheck_shape_stable(self):
        status = ProviderStatus(
            provider_key="example",
            availability=ProviderAvailability.DEGRADED,
            detail="rate limited",
            checked_at="2026-03-15T12:00:00Z",
        )

        self.assertEqual(status.provider_key, "example")
        self.assertEqual(status.availability, ProviderAvailability.DEGRADED)
        self.assertEqual(status.detail, "rate limited")

    def test_protocols_define_required_methods(self):
        expected_methods = {
            NewsProvider: {"fetch_latest", "healthcheck"},
            SearchProvider: {"search", "healthcheck"},
            MarketDataProvider: {"fetch_index_snapshots", "healthcheck"},
            MacroDataProvider: {"fetch_latest_readings", "healthcheck"},
            ResearchProvider: {"collect_outlook", "healthcheck"},
        }

        for protocol, method_names in expected_methods.items():
            for method_name in method_names:
                self.assertIn(method_name, protocol.__dict__, f"{protocol.__name__} is missing {method_name}")


if __name__ == "__main__":
    unittest.main()
