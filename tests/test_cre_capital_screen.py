import sys
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))


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


if __name__ == "__main__":
    unittest.main()
