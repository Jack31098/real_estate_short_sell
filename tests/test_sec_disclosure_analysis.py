from pathlib import Path
import sys
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from sec_disclosure_analysis import (  # noqa: E402
    credit_rows,
    filing_urls,
    geo_rows,
    pct,
    portfolio_rows,
    validated_manifest,
)


class SecDisclosureTests(unittest.TestCase):
    def test_pct(self):
        self.assertEqual(pct(1, 4), 25.0)

    def test_reviewed_manifest_has_10k_and_10q_for_each_ticker(self):
        manifest = validated_manifest()
        self.assertEqual(len(manifest), 14)
        self.assertEqual(set(manifest["form"]), {"10-K", "10-Q"})
        self.assertTrue((manifest.groupby("ticker")["form"].nunique() == 2).all())
        self.assertTrue(manifest["document_url"].str.startswith("https://www.sec.gov/Archives/edgar/data/").all())

    def test_changed_accession_fails_closed(self):
        manifest = pd.read_csv(PROJECT_ROOT / "outputs" / "sec_filings_manifest.csv", dtype="string")
        manifest.loc[0, "accession"] = "0000000000-00-000000"
        with self.assertRaisesRegex(ValueError, "differs from reviewed"):
            validated_manifest(manifest_override=manifest)

    def test_curated_metrics_are_bounded_and_cover_all_tickers(self):
        urls = filing_urls()
        geo = pd.DataFrame(geo_rows(urls))
        portfolio = pd.DataFrame(portfolio_rows(urls))
        credit = pd.DataFrame(credit_rows(urls))
        expected = {"FSBW", "WAFD", "BMRC", "BCML", "CVBF", "COLB", "EWBC"}
        self.assertEqual(set(geo.ticker), expected)
        self.assertTrue(geo.exposure_pct.dropna().between(0, 100).all())
        self.assertTrue(portfolio.portfolio_pct.between(0, 100).all())
        self.assertTrue(credit.current_pct.between(0, 100).all())

    def test_key_geographic_ratios(self):
        geo = pd.DataFrame(geo_rows(filing_urls()))
        bmrc = geo.query("ticker == 'BMRC' and precision == 'county'").iloc[0]
        bcml = geo.query("ticker == 'BCML' and denominator_name == 'total loans'").iloc[0]
        cvbf = geo.query("ticker == 'CVBF' and denominator_name == 'total loans'").iloc[0]
        self.assertEqual(round(bmrc.exposure_pct, 1), 15.9)
        self.assertEqual(round(bcml.exposure_pct, 1), 18.9)
        self.assertEqual(round(cvbf.exposure_pct, 1), 13.8)

    def test_bcml_report_uses_credit_ratio(self):
        credit = pd.read_csv(PROJECT_ROOT / "outputs" / "sec_credit_metrics.csv")
        bcml = credit.loc[(credit.ticker == "BCML") & (credit.metric == "Nonperforming loans")].iloc[0]
        report = (PROJECT_ROOT / "outputs" / "fourth_stage_sec_findings_zh.md").read_text(encoding="utf-8")
        self.assertIn(f"NPL 比率从 {bcml.prior_pct:.2f}% 降至 {bcml.current_pct:.2f}%", report)


if __name__ == "__main__":
    unittest.main()
