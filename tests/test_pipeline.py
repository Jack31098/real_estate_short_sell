from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import pipeline  # noqa: E402


class GeometryTests(unittest.TestCase):
    def test_point_in_polygon_with_hole(self) -> None:
        outer = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
        hole = [[3, 3], [7, 3], [7, 7], [3, 7], [3, 3]]
        self.assertTrue(pipeline.point_in_polygon(1, 1, [outer, hole]))
        self.assertFalse(pipeline.point_in_polygon(5, 5, [outer, hole]))
        self.assertFalse(pipeline.point_in_polygon(12, 5, [outer, hole]))


class OutputInvariantTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.combined = pd.read_csv(
            PROJECT_ROOT / "outputs" / "lender_metrics_2023_2025.csv"
        )
        cls.yearly = pd.read_csv(
            PROJECT_ROOT / "outputs" / "lender_metrics_by_year.csv"
        )
        cls.regional = pd.read_csv(
            PROJECT_ROOT / "outputs" / "regional_totals_by_year.csv"
        )
        cls.candidates = pd.read_csv(
            PROJECT_ROOT / "outputs" / "candidate_banks_2023_2025.csv"
        )
        cls.tracts = pd.read_csv(
            PROJECT_ROOT / "data" / "derived" / "tract_scores.csv",
            dtype={"census_tract": "string"},
        )

    def test_tracts_are_unique(self) -> None:
        self.assertFalse(self.tracts["census_tract"].duplicated().any())

    def test_expected_places_exist(self) -> None:
        expected = {
            "Bellevue",
            "Redmond",
            "Seattle",
            "Palo Alto",
            "Mountain View",
            "Sunnyvale",
            "Cupertino",
        }
        self.assertTrue(expected.issubset(set(self.tracts["place"])))

    def test_market_shares_reconcile(self) -> None:
        sums = self.combined.groupby("region")["weighted_market_share"].sum()
        for value in sums:
            self.assertAlmostEqual(float(value), 1.0, places=9)

    def test_regional_totals_reconcile(self) -> None:
        recomputed = (
            self.yearly.groupby(["activity_year", "region"], as_index=False)[
                ["loan_count", "regional_amount", "core_count", "core_amount", "weighted_amount"]
            ]
            .sum()
            .sort_values(["activity_year", "region"])
            .reset_index(drop=True)
        )
        reported = self.regional.sort_values(
            ["activity_year", "region"]
        ).reset_index(drop=True)
        pd.testing.assert_frame_equal(recomputed, reported, check_dtype=False)

    def test_all_candidate_tickers_present_in_both_regions(self) -> None:
        expected = {row["ticker"] for row in pipeline.CANDIDATE_CATALOG}
        for region, group in self.candidates.groupby("region"):
            self.assertEqual(set(group["ticker"]), expected, msg=region)

    def test_nonnegative_analytical_amounts(self) -> None:
        columns = ["regional_amount", "core_amount", "weighted_amount"]
        self.assertTrue((self.combined[columns] >= 0).all().all())


if __name__ == "__main__":
    unittest.main()
