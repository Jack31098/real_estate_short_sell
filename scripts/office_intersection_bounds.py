#!/usr/bin/env python3
"""Bound regional office CRE from reported geographic and property-type margins.

Legacy margins-only bounds. COLB's Q2 earnings deck separately discloses office
geography; its scope reconciliation is in outputs/v2/scope_reconciliation.json.
These incomplete-source bounds are not the best available regional disclosure.
The independence estimate is an explicit scenario, not an observed loan balance.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
GEOGRAPHIES = {
    "COLB": "Puget Sound + Bay Area",
    "CVBF": "Santa Clara + San Mateo CRE",
    "EWBC": "Northern California + Washington CRE",
}


def intersection_bounds(regional_cre: float, office_cre: float, total_cre: float) -> tuple[float, float, float]:
    if total_cre <= 0 or min(regional_cre, office_cre) < 0:
        raise ValueError("CRE margins must be nonnegative and total CRE positive")
    if max(regional_cre, office_cre) > total_cre:
        raise ValueError("A CRE margin cannot exceed total CRE")
    return (
        max(0.0, regional_cre + office_cre - total_cre),
        min(regional_cre, office_cre),
        regional_cre * office_cre / total_cre,
    )


def run() -> pd.DataFrame:
    geo = pd.read_csv(OUTPUT / "sec_geographic_exposure_summary.csv")
    portfolio = pd.read_csv(OUTPUT / "sec_portfolio_metrics.csv")
    rows = []
    for ticker, region in GEOGRAPHIES.items():
        location = geo.loc[(geo.ticker == ticker) & (geo.geography == region)].iloc[0]
        office = portfolio.loc[(portfolio.ticker == ticker) & (portfolio.metric == "Office")].iloc[0]
        if location.accession != office.accession or location.report_date != office.report_date:
            raise ValueError(f"{ticker} CRE margins come from different filing snapshots")
        if location.amount_unit != "USD millions" or office.amount_unit != "USD millions":
            raise ValueError(f"{ticker} CRE margins have inconsistent units")
        regional_cre = float(location.exposure_usd_m)
        office_cre = float(office.balance_usd_m)
        total_cre = float(office.denominator_usd_m)
        if abs(total_cre - float(location.denominator_usd_m)) > 1.0:
            raise ValueError(f"{ticker} geographic and property-type CRE denominators differ")
        lower, upper, independent = intersection_bounds(regional_cre, office_cre, total_cre)
        rows.append({
            "ticker": ticker,
            "geography": region,
            "report_date": location.report_date,
            "regional_cre_usd_m": regional_cre,
            "office_cre_usd_m": office_cre,
            "total_cre_usd_m": total_cre,
            "regional_office_lower_bound_usd_m": lower,
            "regional_office_upper_bound_usd_m": upper,
            "independence_scenario_usd_m": independent,
            "observed_regional_office_usd_m": pd.NA,
            "assumption": "Independence scenario assumes geography and property type are independent; not observed",
            "geography_precision": location.precision,
            "source_coverage_status": "legacy margins only; see V2 office geography and scope audit" if ticker == "COLB" else "legacy margins only; full joint disclosure review pending",
        })
    result = pd.DataFrame(rows)
    result.to_csv(OUTPUT / "office_intersection_bounds.csv", index=False)
    return result


if __name__ == "__main__":
    print(run().to_string(index=False))
