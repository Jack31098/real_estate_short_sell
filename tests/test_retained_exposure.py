import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import retained_exposure as model  # noqa: E402


class RetainedExposureUnitTests(unittest.TestCase):
    def test_amortization_factor_declines_and_stays_bounded(self):
        terms = pd.Series([360, 360, 12])
        rates = pd.Series([6.0, 6.0, 0.0])
        ages = pd.Series([0, 24, 12])
        factors = model.amortization_factor(terms, rates, ages)
        self.assertAlmostEqual(factors[0], 1.0)
        self.assertGreater(factors[0], factors[1])
        self.assertEqual(factors[2], 0.0)
        self.assertTrue(((factors >= 0) & (factors <= 1)).all())

    def test_invalid_rate_and_term_use_fallbacks(self):
        factors = model.amortization_factor(
            pd.Series(["Exempt", None]),
            pd.Series(["Exempt", None]),
            pd.Series([6, 6]),
        )
        self.assertAlmostEqual(factors[0], factors[1])

    def test_tce_proxy_formula_and_units(self):
        self.assertEqual(model.fdic_tce_proxy(500, 20, 30), 450_000)


class RetainedExposureOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.totals = pd.read_csv(
            PROJECT_ROOT / "outputs" / "candidate_retained_exposure_total.csv"
        )
        cls.regions = pd.read_csv(
            PROJECT_ROOT / "outputs" / "candidate_retained_exposure_by_region.csv"
        )

    def test_all_named_candidates_present(self):
        self.assertEqual(
            set(self.totals["ticker"]),
            {"FSBW", "WAFD", "BMRC", "CVBF", "EWBC", "COLB", "HMST", "BCML"},
        )

    def test_expanded_proxy_not_smaller_than_strict(self):
        self.assertTrue(
            (
                self.totals["expanded_balance_base_8pct"]
                >= self.totals["strict_balance_base_8pct"]
            ).all()
        )

    def test_cpr_sensitivity_is_ordered(self):
        for scope in ("strict", "expanded"):
            self.assertTrue(
                (
                    self.totals[f"{scope}_balance_slow_4pct"]
                    >= self.totals[f"{scope}_balance_base_8pct"]
                ).all()
            )
            self.assertTrue(
                (
                    self.totals[f"{scope}_balance_base_8pct"]
                    >= self.totals[f"{scope}_balance_fast_15pct"]
                ).all()
            )

    def test_region_sums_reconcile_to_totals(self):
        region_sums = self.regions.groupby("ticker")[
            ["core_originated_amount", "expanded_balance_base_8pct"]
        ].sum()
        total_values = self.totals.set_index("ticker")[[
            "core_originated_amount",
            "expanded_balance_base_8pct",
        ]]
        pd.testing.assert_frame_equal(
            region_sums.sort_index(), total_values.sort_index(), check_dtype=False
        )

    def test_tce_and_assets_are_positive(self):
        self.assertTrue((self.totals["tce_proxy"] > 0).all())
        self.assertTrue((self.totals["assets"] > 0).all())


if __name__ == "__main__":
    unittest.main()
