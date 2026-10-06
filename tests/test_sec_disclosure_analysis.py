from pathlib import Path
import sys

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from sec_disclosure_analysis import credit_rows, filing_urls, geo_rows, pct, portfolio_rows


def test_pct():
    assert pct(1, 4) == 25.0


def test_sec_manifest_has_latest_10k_and_10q_for_each_ticker():
    manifest = pd.read_csv(PROJECT_ROOT / "outputs" / "sec_filings_manifest.csv")
    assert len(manifest) == 14
    assert set(manifest["form"]) == {"10-K", "10-Q"}
    assert (manifest.groupby("ticker")["form"].nunique() == 2).all()
    assert manifest["document_url"].str.startswith("https://www.sec.gov/Archives/edgar/data/").all()


def test_curated_metrics_are_bounded_and_cover_all_tickers():
    urls = filing_urls()
    geo = pd.DataFrame(geo_rows(urls))
    portfolio = pd.DataFrame(portfolio_rows(urls))
    credit = pd.DataFrame(credit_rows(urls))
    expected = {"FSBW", "WAFD", "BMRC", "BCML", "CVBF", "COLB", "EWBC"}
    assert set(geo.ticker) == expected
    assert geo.exposure_pct.dropna().between(0, 100).all()
    assert portfolio.portfolio_pct.between(0, 100).all()
    assert credit.current_pct.between(0, 100).all()


def test_key_geographic_ratios():
    geo = pd.DataFrame(geo_rows(filing_urls()))
    bmrc = geo.query("ticker == 'BMRC' and precision == 'county'").iloc[0]
    bcml = geo.query("ticker == 'BCML' and denominator_name == 'total loans'").iloc[0]
    cvbf = geo.query("ticker == 'CVBF' and denominator_name == 'total loans'").iloc[0]
    assert round(bmrc.exposure_pct, 1) == 15.9
    assert round(bcml.exposure_pct, 1) == 18.9
    assert round(cvbf.exposure_pct, 1) == 13.8
