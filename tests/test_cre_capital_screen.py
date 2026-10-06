import sys
import unittest
from pathlib import Path

import pandas as pd
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import cre_capital_screen as model  # noqa: E402


class CreCapitalOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.latest = pd.read_csv(
            PROJECT_ROOT / "outputs" / "candidate_cre_capital_screen_latest.csv"
        )

    def test_all_candidates_have_a_capital_record(self):
        self.assertEqual(
            set(self.latest["ticker"]),
            {"FSBW", "WAFD", "BMRC", "CVBF", "EWBC", "COLB", "HMST", "BCML"},
        )

    def test_nonresidential_components_reconcile(self):
        difference = (
            self.latest["LNRENRES"]
            - self.latest["LNRENROW"]
            - self.latest["LNRENROT"]
        ).abs()
        self.assertTrue((difference < 1).all())

    def test_cre_proxy_does_not_exceed_real_estate_loans(self):
        self.assertTrue((self.latest["cre_proxy"] <= self.latest["LNRE"] + 1).all())

    def test_severe_stress_exceeds_moderate(self):
        self.assertTrue(
            (
                self.latest["severe_gross_loss_to_tce"]
                >= self.latest["moderate_gross_loss_to_tce"]
            ).all()
        )

    def test_rates_are_bounded(self):
        for column in [
            "real_estate_noncurrent_rate",
            "real_estate_early_delinquency_rate",
            "cre_category_noncurrent_rate",
            "allowance_to_loans",
        ]:
            self.assertTrue(((self.latest[column] >= 0) & (self.latest[column] <= 1)).all())

    def test_missing_source_value_stays_unknown(self):
        row = {column: 1.0 for column in model.FDIC_FIELDS if column not in {"REPDTE", "NAME"}}
        row.update({"REPDTE": "20251231", "NAME": "Test Bank", "LNRECONS": np.nan})
        metrics = model.add_metrics(pd.DataFrame([row]))
        self.assertFalse(bool(metrics.loc[0, "data_complete"]))
        self.assertIn("LNRECONS", metrics.loc[0, "missing_fdic_fields"])
        self.assertTrue(pd.isna(metrics.loc[0, "cre_proxy"]))
        self.assertTrue(pd.isna(metrics.loc[0, "severe_gross_loss_to_tce"]))


if __name__ == "__main__":
    unittest.main()
