#!/usr/bin/env python3
"""Build a bank-wide CRE and real-estate capital screen from FDIC data.

The screen is intentionally bank-wide: Call Reports provide reliable portfolio
categories but not property-level geography.  It complements, rather than
replaces, the HMDA tech-core residential analysis.
"""

from __future__ import annotations

import argparse
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import pipeline
import retained_exposure


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

FDIC_FIELDS = [
    "CERT",
    "REPDTE",
    "NAME",
    "ASSET",
    "EQ",
    "EQPP",
    "INTAN",
    "RBCT1J",
    "LNLSGR",
    "LNLSRES",
    "LNRE",
    "LNRECONS",
    "LNREMULT",
    "LNRENRES",
    "LNRENROW",
    "LNRENROT",
    "LNRERES",
    "NARE",
    "P9RE",
    "P3RE",
    "NARECONS",
    "NAREMULT",
    "NARENRES",
    "NARERES",
    "P9RECONS",
    "P9REMULT",
    "P9RENRES",
    "P9RERES",
]

STRESS_SCENARIOS = {
    "moderate": {
        "construction": 0.05,
        "multifamily": 0.02,
        "owner_occupied_nonres": 0.01,
        "other_nonres": 0.03,
    },
    "severe": {
        "construction": 0.10,
        "multifamily": 0.05,
        "owner_occupied_nonres": 0.03,
        "other_nonres": 0.08,
    },
}


def _fetch_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "tech-core-cre-research/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)


def fetch_history(refresh: bool = False) -> tuple[pd.DataFrame, dict[str, Any]]:
    cache_path = RAW_DIR / "fdic_bankfind_2023_2025_cre.json"
    if cache_path.exists() and not refresh:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        certs = sorted(set(retained_exposure.FDIC_CERT_BY_LEI.values()))
        cert_filter = "(" + " OR ".join(f"CERT:{cert}" for cert in certs) + ")"
        filters = cert_filter + " AND REPDTE:[20230101 TO 20251231]"
        params = urllib.parse.urlencode(
            {
                "filters": filters,
                "fields": ",".join(FDIC_FIELDS),
                "sort_by": "REPDTE",
                "sort_order": "ASC",
                "limit": 500,
                "format": "json",
            }
        )
        url = "https://api.fdic.gov/banks/financials?" + params
        payload = {
            "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "url": url,
            "financials": _fetch_json(url),
        }
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    rows = [item["data"] for item in payload["financials"].get("data", [])]
    data = pd.DataFrame(rows)
    if data.empty:
        raise RuntimeError("FDIC financial query returned no rows")
    missing_columns = set(FDIC_FIELDS) - set(data.columns)
    if missing_columns:
        raise RuntimeError(f"FDIC financial query omitted fields: {sorted(missing_columns)}")
    for column in FDIC_FIELDS:
        if column not in {"REPDTE", "NAME"}:
            data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[["CERT", "REPDTE"]].isna().any().any():
        raise RuntimeError("FDIC financial query has missing bank certificate or report date")
    return data.sort_values(["CERT", "REPDTE"]), payload


def add_metrics(data: pd.DataFrame) -> pd.DataFrame:
    df = data.copy()
    amount_columns = [column for column in FDIC_FIELDS if column not in {"CERT", "REPDTE", "NAME"}]
    df["missing_fdic_fields"] = df[amount_columns].apply(
        lambda row: ",".join(row.index[row.isna()]), axis=1
    )
    df["data_complete"] = df["missing_fdic_fields"].eq("")
    df[amount_columns] = df[amount_columns] * 1000.0
    df["tce_proxy"] = df["EQ"] - df["EQPP"] - df["INTAN"]
    df["cre_proxy"] = df["LNRECONS"] + df["LNREMULT"] + df["LNRENROW"] + df["LNRENROT"]
    df["investor_cre_proxy"] = df["LNRECONS"] + df["LNREMULT"] + df["LNRENROT"]
    df["real_estate_to_loans"] = df["LNRE"] / df["LNLSGR"].replace(0, np.nan)
    df["cre_to_loans"] = df["cre_proxy"] / df["LNLSGR"].replace(0, np.nan)
    df["cre_to_tce"] = df["cre_proxy"] / df["tce_proxy"].replace(0, np.nan)
    df["investor_cre_to_tce"] = df["investor_cre_proxy"] / df["tce_proxy"].replace(0, np.nan)
    df["one_to_four_family_to_tce"] = df["LNRERES"] / df["tce_proxy"].replace(0, np.nan)
    df["real_estate_noncurrent"] = df["NARE"] + df["P9RE"]
    df["real_estate_noncurrent_rate"] = df["real_estate_noncurrent"] / df["LNRE"].replace(0, np.nan)
    df["real_estate_early_delinquency_rate"] = df["P3RE"] / df["LNRE"].replace(0, np.nan)
    df["cre_category_noncurrent"] = (
        df["NARECONS"]
        + df["NAREMULT"]
        + df["NARENRES"]
        + df["P9RECONS"]
        + df["P9REMULT"]
        + df["P9RENRES"]
    )
    df["cre_category_noncurrent_rate"] = df["cre_category_noncurrent"] / df[
        "cre_proxy"
    ].replace(0, np.nan)
    df["allowance_to_loans"] = df["LNLSRES"] / df["LNLSGR"].replace(0, np.nan)

    category_columns = {
        "construction": "LNRECONS",
        "multifamily": "LNREMULT",
        "owner_occupied_nonres": "LNRENROW",
        "other_nonres": "LNRENROT",
    }
    for scenario, loss_rates in STRESS_SCENARIOS.items():
        loss = sum(df[category_columns[key]] * rate for key, rate in loss_rates.items())
        df[f"{scenario}_gross_loss"] = loss
        df[f"{scenario}_gross_loss_to_tce"] = loss / df["tce_proxy"].replace(0, np.nan)
        df[f"allowance_coverage_of_{scenario}_loss"] = df["LNLSRES"] / loss.replace(0, np.nan)
    return df


def candidate_identity() -> pd.DataFrame:
    rows = []
    for candidate in pipeline.CANDIDATE_CATALOG:
        rows.append(
            {
                "ticker": candidate["ticker"],
                "lei": candidate["lei"],
                "institution": candidate["institution"],
                "parent": candidate["parent"],
                "fdic_cert": retained_exposure.FDIC_CERT_BY_LEI[candidate["lei"]],
            }
        )
    return pd.DataFrame(rows)


def build_latest_and_trends(metrics: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    identities = candidate_identity()
    metrics = metrics.rename(columns={"CERT": "fdic_cert"})
    metrics = metrics.merge(identities, on="fdic_cert", how="inner")
    metrics["year"] = metrics["REPDTE"].astype(str).str[:4].astype(int)

    annual = metrics.loc[metrics["REPDTE"].astype(str).str.endswith("1231")].copy()
    latest = metrics.sort_values(["fdic_cert", "REPDTE"]).groupby("fdic_cert", as_index=False).tail(1)
    # Preserve HomeStreet's last filing even though it is not a calendar-year-end row.
    latest = latest.sort_values("severe_gross_loss_to_tce", ascending=False)

    trend_rows = []
    for _, row in latest.iterrows():
        history = annual.loc[annual["fdic_cert"].eq(row["fdic_cert"])].sort_values("REPDTE")
        start = history.loc[history["year"].eq(2023)]
        if start.empty:
            start = metrics.loc[metrics["fdic_cert"].eq(row["fdic_cert"])].sort_values("REPDTE").head(1)
        start_row = start.iloc[-1]
        trend_rows.append(
            {
                "ticker": row["ticker"],
                "fdic_cert": row["fdic_cert"],
                "start_report_date": start_row["REPDTE"],
                "end_report_date": row["REPDTE"],
                "cre_proxy_growth": row["cre_proxy"] / start_row["cre_proxy"] - 1 if start_row["cre_proxy"] else np.nan,
                "tce_growth": row["tce_proxy"] / start_row["tce_proxy"] - 1 if start_row["tce_proxy"] else np.nan,
                "cre_to_tce_change": row["cre_to_tce"] - start_row["cre_to_tce"],
                "real_estate_noncurrent_rate_change": row["real_estate_noncurrent_rate"] - start_row["real_estate_noncurrent_rate"],
            }
        )
    return latest, pd.DataFrame(trend_rows)


def write_report(latest: pd.DataFrame, trends: pd.DataFrame) -> None:
    ranked = latest.sort_values("severe_gross_loss_to_tce", ascending=False)
    def fmt_ratio(value: float, digits: int) -> str:
        return "unknown" if pd.isna(value) else f"{value:.{digits}%}"

    lines = [
        "# Bank-wide CRE and real-estate capital screen",
        "",
        "## Headline ranking",
        "",
        "This stage uses FDIC bank-level portfolio categories. It measures balance-sheet "
        "sensitivity, not tech-core geographic purity.",
        "",
        "| Ticker | CRE proxy | CRE / TCE | Investor CRE / TCE | RE noncurrent | Severe gross loss / TCE | Missing FDIC fields | Report date |",
        "|---|---:|---:|---:|---:|---:|---|---:|",
    ]
    for _, row in ranked.iterrows():
        lines.append(
            f"| {row['ticker']} | {'unknown' if pd.isna(row['cre_proxy']) else pipeline.fmt_money(row['cre_proxy'])} | "
            f"{fmt_ratio(row['cre_to_tce'], 1)} | {fmt_ratio(row['investor_cre_to_tce'], 1)} | "
            f"{fmt_ratio(row['real_estate_noncurrent_rate'], 2)} | "
            f"{fmt_ratio(row['severe_gross_loss_to_tce'], 1)} | {row['missing_fdic_fields'] or 'none'} | {row['REPDTE']} |"
        )

    lines += [
        "",
        "CRE proxy = construction and land development + multifamily + owner-occupied "
        "nonfarm nonresidential + other nonfarm nonresidential. Investor CRE excludes the "
        "owner-occupied category. TCE is the same bank-level proxy used in stage 2.",
        "Missing FDIC source fields remain unknown rather than being treated as zero; "
        "affected ratios and stress results are also unknown.",
        "",
        "## Standardized stress scenarios",
        "",
        "The moderate gross-loss rates are 5% construction, 2% multifamily, 1% owner-occupied "
        "nonresidential, and 3% other nonresidential. The severe rates are 10%, 5%, 3%, and "
        "8%, respectively. These are transparent comparative haircuts, not forecasts. Reported "
        "allowances are shown separately and are not automatically netted against the losses.",
        "",
        "## Geographic limitation",
        "",
        "Call Report categories do not reveal whether a property is in Bellevue, Redmond, "
        "Palo Alto, or elsewhere. A high CRE/TCE ratio therefore identifies capital sensitivity "
        "but cannot validate the AI-tech-city geography thesis. SEC filings and bank investor "
        "materials are still required for metro/county/property-type splits.",
        "",
        "## HomeStreet comparability",
        "",
        "HomeStreet's last independent 2025 row is 2025-06-30. It should be treated as a "
        "historical entity observation, not a currently shortable standalone bank balance sheet.",
        "",
        "## Official source",
        "",
        "- FDIC BankFind Suite API documentation and financial definitions: https://api.fdic.gov/banks/docs/",
    ]
    (OUTPUT_DIR / "third_stage_cre_findings.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(refresh_fdic: bool = False) -> None:
    pipeline.ensure_dirs()
    history, _ = fetch_history(refresh=refresh_fdic)
    metrics = add_metrics(history)
    latest, trends = build_latest_and_trends(metrics)
    metrics.to_csv(OUTPUT_DIR / "fdic_cre_metrics_quarterly_2023_2025.csv", index=False)
    latest.to_csv(OUTPUT_DIR / "candidate_cre_capital_screen_latest.csv", index=False)
    trends.to_csv(OUTPUT_DIR / "candidate_cre_trends_2023_2025.csv", index=False)
    write_report(latest, trends)
    print("stage 3 done")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-fdic", action="store_true", help="Refresh cached FDIC history")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(refresh_fdic=args.refresh_fdic)
