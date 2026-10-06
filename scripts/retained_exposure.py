#!/usr/bin/env python3
"""Estimate an originated-cohort residential balance proxy.

This second-stage model starts with the first-stage HMDA residential screen and
adds two deliberately limited retention proxies:

* strict: purchaser_type == 0 (not reported sold during the HMDA calendar year)
* expanded: purchaser_type in {0, 8} (strict plus affiliate purchaser)

It then rolls each origination forward to 2025-12-31 with scheduled
amortization and three constant-prepayment-rate assumptions.  The result is
compared with bank-level tangible common equity proxies from FDIC BankFind
Suite data.  It is not a measurement of current holdings and excludes CRE.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

AS_OF_YEAR = 2025
FALLBACK_TERM_MONTHS = 360.0
FALLBACK_RATE_PERCENT = 6.5
CPR_SCENARIOS = {"slow_4pct": 0.04, "base_8pct": 0.08, "fast_15pct": 0.15}

FDIC_CERT_BY_LEI = {
    "5493003T5D4N1CM46J77": 57633,
    "D38AC76TAMYI50NBPX33": 28088,
    "549300EGL1VV7LY0QU69": 32779,
    "549300L36QZWPHM6FP31": 21716,
    "F28JOQ8OBWCFUYM0UX93": 31628,
    "IFQSIUC9AGQV2NE8CN25": 17266,
    "01KWVG908KE7RKPTNP46": 32489,
    # BayCom Corp.'s bank subsidiary.  There is no matched HMDA LEI in stage 1.
    "": 57716,
}

PURCHASER_LABELS = {
    0: "Not applicable / not reported sold in calendar year",
    1: "Fannie Mae",
    2: "Ginnie Mae",
    3: "Freddie Mac",
    4: "Farmer Mac",
    5: "Private securitizer",
    6: "Commercial bank, savings bank, or savings association",
    71: "Credit union, mortgage company, or finance company",
    72: "Life insurance company",
    8: "Affiliate institution",
    9: "Other purchaser",
}

MODEL_USECOLS = pipeline.USECOLS + ["purchaser_type", "loan_term", "interest_rate"]


def amortization_factor(
    term_months: pd.Series, interest_rate_percent: pd.Series, age_months: pd.Series
) -> np.ndarray:
    """Return scheduled principal balance as a fraction of original principal."""
    term = pd.to_numeric(term_months, errors="coerce").to_numpy(dtype=float)
    rate = pd.to_numeric(interest_rate_percent, errors="coerce").to_numpy(dtype=float)
    age = pd.to_numeric(age_months, errors="coerce").to_numpy(dtype=float)

    term = np.where((term >= 12) & (term <= 600), term, FALLBACK_TERM_MONTHS)
    rate = np.where((rate >= 0) & (rate <= 25), rate, FALLBACK_RATE_PERCENT)
    age = np.maximum(age, 0)
    monthly_rate = rate / 1200.0

    factor = np.zeros(len(term), dtype=float)
    alive = age < term
    zero_rate = alive & np.isclose(monthly_rate, 0)
    factor[zero_rate] = 1.0 - age[zero_rate] / term[zero_rate]

    normal = alive & ~zero_rate
    growth_term = np.power(1.0 + monthly_rate[normal], term[normal])
    growth_age = np.power(1.0 + monthly_rate[normal], age[normal])
    factor[normal] = (growth_term - growth_age) / (growth_term - 1.0)
    return np.clip(factor, 0.0, 1.0)


def fdic_tce_proxy(eq_thousands: float, preferred_thousands: float, intan_thousands: float) -> float:
    """Bank-level tangible common equity proxy in dollars."""
    return (eq_thousands - preferred_thousands - intan_thousands) * 1000.0


def source_files() -> list[tuple[int, str, Path]]:
    result: list[tuple[int, str, Path]] = []
    region_names = {
        "bay-area": "Bay Area",
        "seattle-puget-sound": "Seattle/Puget Sound",
    }
    for path in sorted(RAW_DIR.glob("hmda_*_originated.csv.gz")):
        parts = path.name.split("_")
        year = int(parts[1])
        # The filename embeds the canonical region name before "_originated".
        slug = path.name[len(f"hmda_{year}_") : -len("_originated.csv.gz")]
        region = region_names[slug]
        result.append((year, region, path))
    if not result:
        raise FileNotFoundError("No cached HMDA files found; run scripts/pipeline.py first")
    return result


def load_candidate_core_loans(
    files: list[tuple[int, str, Path]], tract_scores: pd.DataFrame
) -> pd.DataFrame:
    score_columns = tract_scores[["census_tract", "region", "place", "tech_score"]]
    threshold = pipeline.core_threshold()
    known_leis = set(pipeline.CANDIDATES)
    parts: list[pd.DataFrame] = []

    for year, region_name, path in files:
        print(f"retention analyze: {path.name}")
        for chunk in pd.read_csv(
            path,
            compression="gzip",
            usecols=MODEL_USECOLS,
            dtype={"lei": "string", "census_tract": "string"},
            chunksize=100_000,
            low_memory=False,
        ):
            chunk = chunk.loc[chunk["lei"].isin(known_leis)].copy()
            if chunk.empty:
                continue
            clean = pipeline.clean_chunk(chunk)
            if clean.empty:
                continue
            clean = clean.merge(score_columns, on="census_tract", how="inner")
            clean = clean.loc[
                clean["region"].eq(region_name) & clean["tech_score"].ge(threshold)
            ].copy()
            if clean.empty:
                continue

            clean["purchaser_type"] = pd.to_numeric(
                clean["purchaser_type"], errors="coerce"
            ).astype("Int64")
            clean["age_months"] = (AS_OF_YEAR - year) * 12 + 6
            clean["scheduled_factor"] = amortization_factor(
                clean["loan_term"], clean["interest_rate"], clean["age_months"]
            )
            clean["strict_retained"] = clean["purchaser_type"].eq(0)
            clean["expanded_retained"] = clean["purchaser_type"].isin([0, 8])

            for label, cpr in CPR_SCENARIOS.items():
                survival = np.power(1.0 - cpr, clean["age_months"] / 12.0)
                modeled_balance = clean["loan_amount"] * clean["scheduled_factor"] * survival
                clean[f"strict_balance_{label}"] = modeled_balance.where(
                    clean["strict_retained"], 0.0
                )
                clean[f"expanded_balance_{label}"] = modeled_balance.where(
                    clean["expanded_retained"], 0.0
                )

            keep_columns = [
                "activity_year",
                "region",
                "lei",
                "place",
                "loan_amount",
                "purchaser_type",
                "strict_retained",
                "expanded_retained",
                "scheduled_factor",
            ] + [
                f"{scope}_balance_{scenario}"
                for scope in ("strict", "expanded")
                for scenario in CPR_SCENARIOS
            ]
            parts.append(clean[keep_columns])

    if not parts:
        return pd.DataFrame()
    return pd.concat(parts, ignore_index=True)


def aggregate_retention(loans: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    balance_columns = [
        f"{scope}_balance_{scenario}"
        for scope in ("strict", "expanded")
        for scenario in CPR_SCENARIOS
    ]
    loans = loans.copy()
    loans["strict_originated_amount"] = loans["loan_amount"].where(
        loans["strict_retained"], 0.0
    )
    loans["expanded_originated_amount"] = loans["loan_amount"].where(
        loans["expanded_retained"], 0.0
    )
    loans["strict_loan_count"] = loans["strict_retained"].astype(int)
    loans["expanded_loan_count"] = loans["expanded_retained"].astype(int)

    aggregated = (
        loans.groupby(["region", "lei"], as_index=False)
        .agg(
            core_loan_count=("loan_amount", "size"),
            core_originated_amount=("loan_amount", "sum"),
            strict_loan_count=("strict_loan_count", "sum"),
            strict_originated_amount=("strict_originated_amount", "sum"),
            expanded_loan_count=("expanded_loan_count", "sum"),
            expanded_originated_amount=("expanded_originated_amount", "sum"),
            **{column: (column, "sum") for column in balance_columns},
        )
    )
    aggregated["strict_originated_share"] = (
        aggregated["strict_originated_amount"] / aggregated["core_originated_amount"]
    )
    aggregated["expanded_originated_share"] = (
        aggregated["expanded_originated_amount"] / aggregated["core_originated_amount"]
    )

    mix = (
        loans.groupby(["region", "lei", "purchaser_type"], dropna=False, as_index=False)
        .agg(core_loan_count=("loan_amount", "size"), core_originated_amount=("loan_amount", "sum"))
    )
    mix["purchaser_label"] = mix["purchaser_type"].map(PURCHASER_LABELS).fillna("Unknown")
    return aggregated, mix


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "tech-core-exposure-research/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def fetch_fdic_data(refresh: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_path = RAW_DIR / "fdic_bankfind_2025_capital.json"
    if cache_path.exists() and not refresh:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        certs = sorted(set(FDIC_CERT_BY_LEI.values()))
        cert_filter = "(" + " OR ".join(f"CERT:{cert}" for cert in certs) + ")"
        financial_filter = cert_filter + " AND REPDTE:[20250101 TO 20251231]"
        base = "https://api.fdic.gov/banks/"
        financial_params = urllib.parse.urlencode(
            {
                "filters": financial_filter,
                "fields": "CERT,REPDTE,ASSET,EQ,EQPP,INTAN,RBCT1J,NAME",
                "sort_by": "REPDTE",
                "sort_order": "ASC",
                "limit": 100,
                "format": "json",
            }
        )
        institution_params = urllib.parse.urlencode(
            {
                "filters": cert_filter,
                "fields": "CERT,NAME,ACTIVE,STALP,CITY,DATEUPDT,ASSET",
                "limit": 100,
                "format": "json",
            }
        )
        financial_url = base + "financials?" + financial_params
        institution_url = base + "institutions?" + institution_params
        payload = {
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "financial_url": financial_url,
            "institution_url": institution_url,
            "financials": _fetch_json(financial_url),
            "institutions": _fetch_json(institution_url),
        }
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    financial_rows = [item["data"] for item in payload["financials"].get("data", [])]
    institution_rows = [item["data"] for item in payload["institutions"].get("data", [])]
    financials = pd.DataFrame(financial_rows)
    institutions = pd.DataFrame(institution_rows)
    for column in ["CERT", "ASSET", "EQ", "EQPP", "INTAN", "RBCT1J"]:
        financials[column] = pd.to_numeric(financials[column], errors="coerce")
    financials = financials.sort_values(["CERT", "REPDTE"]).groupby("CERT", as_index=False).tail(1)
    financials["tce_proxy"] = financials.apply(
        lambda row: fdic_tce_proxy(row["EQ"], row["EQPP"], row["INTAN"]), axis=1
    )
    financials["assets"] = financials["ASSET"] * 1000.0
    financials["cet1_capital"] = financials["RBCT1J"] * 1000.0
    institutions["CERT"] = pd.to_numeric(institutions["CERT"], errors="coerce")
    institutions["ACTIVE"] = pd.to_numeric(institutions["ACTIVE"], errors="coerce")
    capital = financials.merge(
        institutions[["CERT", "ACTIVE", "DATEUPDT"]].rename(
            columns={"ACTIVE": "fdic_active", "DATEUPDT": "fdic_status_updated"}
        ),
        on="CERT",
        how="left",
    )
    return capital, payload


def complete_candidate_grid(retention: pd.DataFrame) -> pd.DataFrame:
    regions = ["Bay Area", "Seattle/Puget Sound"]
    rows: list[dict[str, Any]] = []
    numeric_columns = [column for column in retention.columns if column not in {"region", "lei"}]
    for candidate in pipeline.CANDIDATE_CATALOG:
        for region in regions:
            match = retention.loc[
                retention["region"].eq(region) & retention["lei"].eq(candidate["lei"])
            ]
            row = match.iloc[0].to_dict() if not match.empty else {column: 0.0 for column in numeric_columns}
            row.update(
                {
                    "region": region,
                    "lei": candidate["lei"],
                    "ticker": candidate["ticker"],
                    "institution": candidate["institution"],
                    "parent": candidate["parent"],
                    "fdic_cert": FDIC_CERT_BY_LEI[candidate["lei"]],
                    "hmda_scope_note": candidate["hmda_scope_note"],
                }
            )
            rows.append(row)
    return pd.DataFrame(rows)


def attach_capital(exposure: pd.DataFrame, capital: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "CERT",
        "REPDTE",
        "NAME",
        "fdic_active",
        "fdic_status_updated",
        "assets",
        "tce_proxy",
        "cet1_capital",
    ]
    result = exposure.merge(
        capital[columns].rename(
            columns={"CERT": "fdic_cert", "REPDTE": "capital_report_date", "NAME": "fdic_bank_name"}
        ),
        on="fdic_cert",
        how="left",
    )
    for scope in ("strict", "expanded"):
        for scenario in CPR_SCENARIOS:
            balance = f"{scope}_balance_{scenario}"
            result[f"{balance}_to_tce"] = result[balance] / result["tce_proxy"]
    return result


def write_report(by_region: pd.DataFrame, totals: pd.DataFrame, mix: pd.DataFrame) -> None:
    ranked = totals.sort_values("expanded_balance_base_8pct_to_tce", ascending=False)
    type8_count = int(mix.loc[mix["purchaser_type"].eq(8), "core_loan_count"].sum())
    lines = [
        "# Second-stage residential origination-cohort balance proxy",
        "",
        "## Headline result",
        "",
        "The purchaser-type screen materially reduces the first-stage origination footprint. "
        "The table below compares modeled 2025-12-31 balances in named tech-core places "
        "with bank-level tangible common equity (TCE) proxies.",
        "",
        "| Ticker | Core originations | Strict base balance | Expanded base balance | Expanded / TCE | Capital date |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for _, row in ranked.iterrows():
        lines.append(
            f"| {row['ticker']} | {pipeline.fmt_money(row['core_originated_amount'])} | "
            f"{pipeline.fmt_money(row['strict_balance_base_8pct'])} | "
            f"{pipeline.fmt_money(row['expanded_balance_base_8pct'])} | "
            f"{row['expanded_balance_base_8pct_to_tce']:.2%} | {row['capital_report_date']} |"
        )

    lines += [
        "",
        "Strict means HMDA purchaser type 0: an originated loan was not reported as sold "
        "during that reporting calendar year. Expanded adds purchaser type 8, sale to an "
        "affiliate. Type 8 does not establish that the bank subsidiary in the TCE denominator "
        "holds the loan. Neither field proves that the loan remained on a consolidated balance "
        f"sheet at 2025 year-end. The observed candidate sample contains {type8_count} type 8 loans.",
        "",
        "## Model assumptions",
        "",
        "- Scope is unchanged from stage 1: principal-residence, first-lien, 1–4 unit, "
        "non-commercial purchase/refinance loans whose Census tract point falls in a place "
        f"with a tech score of at least {pipeline.core_threshold():g}.",
        "- Each loan is assumed to originate at the midpoint of its HMDA year. Scheduled "
        "amortization uses reported rate and term; missing/invalid values use 6.5% and 360 months.",
        "- CPR scenarios are 4%, 8% (base), and 15%. This is a sensitivity analysis, not a "
        "loan-level servicing model.",
        "- Bank TCE proxy = FDIC total equity capital minus perpetual preferred stock minus "
        "intangible assets. FDIC amounts are converted from thousands of dollars.",
        "- HomeStreet's last 2025 FDIC financial report is 2025-06-30 and its current FDIC "
        "status is inactive. Its ratio is historical/entity-specific and not directly "
        "comparable with the surviving year-end banks.",
        "",
        "## What this does and does not establish",
        "",
        "This is a sharper residential screening metric than raw originations, but it is "
        "still not current loan holdings. HMDA lacks stable loan identifiers across years; "
        "refinancings, subsequent sales, repurchases, participations, charge-offs, and exact "
        "origination dates are unobserved. Most importantly, CRE and construction lending are "
        "outside this residential model and require Call Report/SEC portfolio data.",
        "",
        "The proxy can overstate exposure through later sales and repeat refinancing originations, "
        "or understate it by excluding pre-2023 cohorts, purchased loans and acquired portfolios. "
        "It is not a conservative bound. Balance / TCE is not loss / TCE: losses also depend on "
        "defaults, collateral recoveries, reserves, earnings and taxes.",
        "",
        "## Reproducible outputs",
        "",
        "- `candidate_retained_exposure_total.csv`: bank ranking across both observed regions.",
        "- `candidate_retained_exposure_by_region.csv`: same model split by region.",
        "- `candidate_purchaser_mix_2023_2025.csv`: purchaser-type audit trail.",
        "- `fdic_capital_2025.csv`: latest 2025 bank capital record used for each FDIC certificate.",
        "",
        "## Official sources",
        "",
        "- HMDA data and filing guides: https://ffiec.cfpb.gov/data-publication/",
        "- HMDA Data Browser API: https://ffiec.cfpb.gov/documentation/api/data-browser/",
        "- FDIC BankFind Suite API documentation: https://api.fdic.gov/banks/docs/",
    ]
    (OUTPUT_DIR / "second_stage_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_outputs(loans: pd.DataFrame, capital: pd.DataFrame) -> None:
    retention, mix = aggregate_retention(loans)
    by_region = attach_capital(complete_candidate_grid(retention), capital)

    sum_columns = [
        column
        for column in by_region.columns
        if column.endswith("_amount")
        or column.endswith("_count")
        or "_balance_" in column and not column.endswith("_to_tce")
    ]
    identity_columns = [
        "lei",
        "ticker",
        "institution",
        "parent",
        "fdic_cert",
        "hmda_scope_note",
        "capital_report_date",
        "fdic_bank_name",
        "fdic_active",
        "fdic_status_updated",
        "assets",
        "tce_proxy",
        "cet1_capital",
    ]
    totals = by_region.groupby(identity_columns, dropna=False, as_index=False)[sum_columns].sum()
    totals["strict_originated_share"] = totals["strict_originated_amount"] / totals[
        "core_originated_amount"
    ].replace(0, np.nan)
    totals["expanded_originated_share"] = totals["expanded_originated_amount"] / totals[
        "core_originated_amount"
    ].replace(0, np.nan)
    for scope in ("strict", "expanded"):
        for scenario in CPR_SCENARIOS:
            column = f"{scope}_balance_{scenario}"
            totals[f"{column}_to_tce"] = totals[column] / totals["tce_proxy"]

    label_columns = {lei: values for lei, values in pipeline.CANDIDATES.items()}
    mix["ticker"] = mix["lei"].map({lei: values["ticker"] for lei, values in label_columns.items()})
    mix["institution"] = mix["lei"].map({lei: values["institution"] for lei, values in label_columns.items()})
    mix = mix.sort_values(["region", "ticker", "purchaser_type"], na_position="last")

    by_region.sort_values(["region", "expanded_balance_base_8pct"], ascending=[True, False]).to_csv(
        OUTPUT_DIR / "candidate_retained_exposure_by_region.csv", index=False
    )
    totals.sort_values("expanded_balance_base_8pct_to_tce", ascending=False).to_csv(
        OUTPUT_DIR / "candidate_retained_exposure_total.csv", index=False
    )
    mix.to_csv(OUTPUT_DIR / "candidate_purchaser_mix_2023_2025.csv", index=False)
    capital.to_csv(OUTPUT_DIR / "fdic_capital_2025.csv", index=False)
    write_report(by_region, totals, mix)


def run(refresh_fdic: bool = False) -> None:
    pipeline.ensure_dirs()
    tract_scores = pd.read_csv(
        DERIVED_DIR / "tract_scores.csv", dtype={"census_tract": "string"}
    )
    loans = load_candidate_core_loans(source_files(), tract_scores)
    if loans.empty:
        raise RuntimeError("No candidate tech-core loans survived the stage-2 filters")
    capital, _ = fetch_fdic_data(refresh=refresh_fdic)
    write_outputs(loans, capital)
    print("stage 2 done")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-fdic", action="store_true", help="Refresh cached 2025 FDIC BankFind data"
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    run(refresh_fdic=args.refresh_fdic)
