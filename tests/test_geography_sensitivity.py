from pathlib import Path
import sys
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from geography_sensitivity import scenario_mask  # noqa: E402


class GeographySensitivityTests(unittest.TestCase):
    def test_threshold_and_city_exclusion_are_distinct(self):
        places = pd.DataFrame(
            {"place": ["Seattle", "Bellevue", "Kirkland"], "tech_score": [0.8, 1.0, 0.8]}
        )
        self.assertEqual(scenario_mask(places, 0.9, "").tolist(), [False, True, False])
        self.assertEqual(scenario_mask(places, 0.7, "Seattle").tolist(), [False, True, True])

    def test_baseline_reconciles_to_candidate_screen(self):
        scenarios = pd.read_csv(PROJECT_ROOT / "outputs" / "residential_geography_sensitivity.csv")
        baseline = scenarios.loc[scenarios.scenario.eq("baseline_t0.7")]
        prior = pd.read_csv(PROJECT_ROOT / "outputs" / "candidate_banks_2023_2025.csv")
        merged = baseline.merge(prior[["region", "ticker", "core_amount"]], on=["region", "ticker"], validate="one_to_one")
        self.assertEqual(len(merged), len(baseline))
        self.assertTrue(((merged.core_origination_amount - merged.core_amount).abs() < 1).all())

    def test_seattle_candidate_order_is_scenario_sensitive(self):
        scenarios = pd.read_csv(PROJECT_ROOT / "outputs" / "residential_geography_sensitivity.csv")
        pair = scenarios.loc[
            scenarios.region.eq("Seattle/Puget Sound")
            & scenarios.ticker.isin(["FSBW", "WAFD"])
        ]
        baseline = pair.loc[pair.scenario.eq("baseline_t0.7")].set_index("ticker")
        narrow = pair.loc[pair.scenario.eq("narrow_t0.9")].set_index("ticker")
        self.assertGreater(baseline.loc["FSBW", "core_origination_amount"], baseline.loc["WAFD", "core_origination_amount"])
        self.assertLess(narrow.loc["FSBW", "core_origination_amount"], narrow.loc["WAFD", "core_origination_amount"])

    def test_new_city_scenario_matches_city_level_originations(self):
        scenarios = pd.read_csv(PROJECT_ROOT / "outputs" / "residential_geography_sensitivity.csv")
        places = pd.read_csv(PROJECT_ROOT / "outputs" / "candidate_originations_by_place_2023_2025.csv")
        added = places.loc[places.place.isin(["San Jose", "Santa Clara"])].groupby("ticker")["originated_amount"].sum()
        bay = scenarios.loc[scenarios.region.eq("Bay Area")]
        current = bay.loc[bay.scenario.eq("baseline_t0.7")].set_index("ticker")
        legacy = bay.loc[bay.scenario.eq("legacy_exclude_new_cities")].set_index("ticker")
        change = current.core_origination_amount - legacy.core_origination_amount
        for ticker, amount in added.items():
            self.assertAlmostEqual(change.loc[ticker], amount)


if __name__ == "__main__":
    unittest.main()
