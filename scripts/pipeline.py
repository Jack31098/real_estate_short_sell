#!/usr/bin/env python3
"""Download and analyze HMDA mortgage originations in tech-core tracts.

The pipeline intentionally separates three layers:
1. official raw HMDA downloads (cached as gzip-compressed CSV),
2. Census tract-to-place scoring inputs, and
3. lender-level analytical outputs.

HMDA measures reported applications/originations, not current on-balance-sheet
loan holdings. The output must therefore be read as an origination footprint,
not as a direct estimate of credit exposure.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import http.cookiejar
import json
import math
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "config" / "tech_core_places.json"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

HMDA_BASE = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv"
HMDA_WARMUP = "https://ffiec.cfpb.gov/data-browser/data/"
TRACT_LAYER = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/Tracts_Blocks/MapServer/0/query"
)
PLACE_LAYER = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4/query"
)

YEARS = (2023, 2024, 2025)

HMDA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Referer": HMDA_WARMUP,
    "Origin": "https://ffiec.cfpb.gov",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}

USECOLS = [
    "activity_year",
    "lei",
    "state_code",
    "county_code",
    "census_tract",
    "derived_dwelling_category",
    "action_taken",
    "loan_purpose",
    "lien_status",
    "reverse_mortgage",
    "business_or_commercial_purpose",
    "loan_amount",
    "occupancy_type",
]

CANDIDATES = {
    "5493003T5D4N1CM46J77": {
        "ticker": "FSBW",
        "institution": "1st Security Bank of Washington",
        "parent": "FS Bancorp",
    },
    "D38AC76TAMYI50NBPX33": {
        "ticker": "WAFD",
        "institution": "WASHINGTON FEDERAL BANK",
        "parent": "WaFd, Inc.",
    },
    "549300EGL1VV7LY0QU69": {
        "ticker": "BMRC",
        "institution": "Bank of Marin",
        "parent": "Bank of Marin Bancorp",
    },
    "549300L36QZWPHM6FP31": {
        "ticker": "CVBF",
        "institution": "Citizens Business Bank",
        "parent": "CVB Financial Corp.",
    },
    "F28JOQ8OBWCFUYM0UX93": {
        "ticker": "EWBC",
        "institution": "East West Bank",
        "parent": "East West Bancorp",
    },
    "IFQSIUC9AGQV2NE8CN25": {
        "ticker": "COLB",
        "institution": "Umpqua Bank",
        "parent": "Columbia Banking System",
    },
    "01KWVG908KE7RKPTNP46": {
        "ticker": "HMST",
        "institution": "HomeStreet Bank",
        "parent": "HomeStreet, Inc.",
    },
}

CANDIDATE_CATALOG = [
    {
        "ticker": values["ticker"],
        "lei": lei,
        "institution": values["institution"],
        "parent": values["parent"],
        "hmda_scope_note": "Residential HMDA filer identified",
    }
    for lei, values in CANDIDATES.items()
] + [
    {
        "ticker": "BCML",
        "lei": "",
        "institution": "United Business Bank / BayCom Corp.",
        "parent": "BayCom Corp.",
        "hmda_scope_note": (
            "No matching 2025 HMDA filer identified in California; likely CRE-led "
            "exposure requires a separate source"
        ),
    }
]

FALLBACK_LENDER_NAMES = {
    "549300SBA6BX8HZZF585": "FIDELITY LENDING SOLUTIONS, INC.",
    "254900YZ174H294JW398": "Tri Pointe Connect, LLC",
}


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    for directory in (RAW_DIR, DERIVED_DIR, OUTPUT_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def make_hmda_opener() -> urllib.request.OpenerDirector:
    cookies = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookies)
    )
    request = urllib.request.Request(HMDA_WARMUP, headers=HMDA_HEADERS)
    with opener.open(request, timeout=120) as response:
        response.read()
    return opener


def iter_regions(config: dict[str, Any]) -> Iterable[tuple[str, dict[str, Any]]]:
    yield from config["regions"].items()


def hmda_url(year: int, region: dict[str, Any]) -> str:
    county_codes = [region["state_fips"] + c for c in region["counties"]]
    params = {
        "counties": ",".join(county_codes),
        "years": str(year),
        "actions_taken": "1",
    }
    return HMDA_BASE + "?" + urllib.parse.urlencode(params)


def download_hmda_file(
    opener: urllib.request.OpenerDirector,
    year: int,
    region_name: str,
    region: dict[str, Any],
    force: bool = False,
) -> Path:
    slug = region_name.lower().replace("/", "-").replace(" ", "-")
    destination = RAW_DIR / f"hmda_{year}_{slug}_originated.csv.gz"
    if destination.exists() and destination.stat().st_size > 1000 and not force:
        print(f"cached: {destination.name}")
        return destination

    temp_path = destination.with_suffix(destination.suffix + ".part")
    url = hmda_url(year, region)
    print(f"download: {year} {region_name}")
    request = urllib.request.Request(url, headers=HMDA_HEADERS)
    started = time.time()
    with opener.open(request, timeout=900) as response:
        content_type = response.headers.get("Content-Type", "")
        if "text" not in content_type and "csv" not in content_type:
            raise RuntimeError(f"Unexpected HMDA content type: {content_type}")
        with gzip.open(temp_path, "wb", compresslevel=6) as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
    os.replace(temp_path, destination)
    print(
        f"saved: {destination.name} ({destination.stat().st_size / 1e6:.1f} MB, "
        f"{time.time() - started:.1f}s)"
    )
    return destination


def arcgis_query(url: str, params: dict[str, str]) -> list[dict[str, Any]]:
    def fetch(query: dict[str, str]) -> dict[str, Any]:
        request_url = url + "?" + urllib.parse.urlencode({**query, "f": "json"})
        request = urllib.request.Request(
            request_url,
            headers={"User-Agent": HMDA_HEADERS["User-Agent"], "Accept": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=180) as response:
            payload = json.load(response)
        if "error" in payload:
            raise RuntimeError(f"ArcGIS error: {payload['error']}")
        return payload

    count_payload = fetch({**params, "returnCountOnly": "true"})
    if "count" not in count_payload:
        raise RuntimeError("ArcGIS count query returned no count")
    expected = int(count_payload["count"])
    features: list[dict[str, Any]] = []
    page_size = 1000
    offset = 0
    while len(features) < expected:
        payload = fetch({**params, "resultOffset": str(offset), "resultRecordCount": str(page_size)})
        page = payload.get("features")
        if not isinstance(page, list):
            raise RuntimeError("ArcGIS query returned no feature list")
        features.extend(page)
        if len(features) >= expected and payload.get("exceededTransferLimit", False):
            raise RuntimeError("ArcGIS count and pagination disagree")
        if not page and not payload.get("exceededTransferLimit", False):
            break
        offset += len(page) if page else page_size
        if offset > expected + page_size:
            raise RuntimeError("ArcGIS pagination did not converge")
    if len(features) != expected:
        raise RuntimeError(f"ArcGIS query incomplete: expected {expected}, got {len(features)}")
    geoids = [feature.get("attributes", {}).get("GEOID") for feature in features]
    if None in geoids or len(geoids) != len(set(geoids)):
        raise RuntimeError("ArcGIS query returned missing or duplicate GEOIDs")
    return features


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        crosses = (yi > y) != (yj > y)
        if crosses:
            x_at_y = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_at_y:
                inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, rings: list[list[list[float]]]) -> bool:
    # ArcGIS rings can include multiple outer rings and holes. The even-odd rule
    # across all rings handles both without relying on ring orientation.
    return sum(point_in_ring(x, y, ring) for ring in rings) % 2 == 1


def build_tract_scores(config: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for region_name, region in iter_regions(config):
        state = region["state_fips"]
        counties = ",".join(f"'{c}'" for c in region["counties"])
        tract_features = arcgis_query(
            TRACT_LAYER,
            {
                "where": f"STATE='{state}' AND COUNTY IN ({counties})",
                "outFields": (
                    "GEOID,STATE,COUNTY,TRACT,NAME,INTPTLAT,INTPTLON,"
                    "AREALAND,AREAWATER"
                ),
                "returnGeometry": "false",
            },
        )
        place_names = ",".join(
            "'" + name.replace("'", "''") + "'" for name in region["places"]
        )
        place_features = arcgis_query(
            PLACE_LAYER,
            {
                "where": f"STATE='{state}' AND BASENAME IN ({place_names})",
                "outFields": "GEOID,BASENAME,NAME,STATE,PLACE",
                "returnGeometry": "true",
                "outSR": "4326",
            },
        )
        places = []
        for feature in place_features:
            attrs = feature["attributes"]
            places.append(
                {
                    "name": attrs["BASENAME"],
                    "geoid": attrs["GEOID"],
                    "rings": feature["geometry"]["rings"],
                    "score": float(region["places"][attrs["BASENAME"]]),
                }
            )

        missing = sorted(set(region["places"]) - {p["name"] for p in places})
        if missing:
            raise RuntimeError(f"Missing TIGER places for {region_name}: {missing}")

        for feature in tract_features:
            attrs = feature["attributes"]
            lat = float(attrs["INTPTLAT"])
            lon = float(attrs["INTPTLON"])
            matches = [
                place for place in places if point_in_polygon(lon, lat, place["rings"])
            ]
            if len(matches) > 1:
                matches.sort(key=lambda p: abs(p["score"]), reverse=True)
            match = matches[0] if matches else None
            rows.append(
                {
                    "census_tract": str(attrs["GEOID"]),
                    "region": region_name,
                    "state_fips": str(attrs["STATE"]),
                    "county_fips": str(attrs["STATE"]) + str(attrs["COUNTY"]),
                    "tract_name": attrs["NAME"],
                    "place": match["name"] if match else "Outside named places",
                    "place_geoid": match["geoid"] if match else "",
                    "tech_score": match["score"] if match else 0.0,
                    "latitude": lat,
                    "longitude": lon,
                    "assignment_method": "tract interior point in incorporated place",
                }
            )
    result = pd.DataFrame(rows).sort_values(["region", "census_tract"])
    result.to_csv(DERIVED_DIR / "tract_scores.csv", index=False)
    return result


def clean_chunk(chunk: pd.DataFrame, require_tract: bool = True) -> pd.DataFrame:
    numeric_cols = [
        "activity_year",
        "action_taken",
        "loan_purpose",
        "lien_status",
        "reverse_mortgage",
        "business_or_commercial_purpose",
        "loan_amount",
        "occupancy_type",
    ]
    for column in numeric_cols:
        chunk[column] = pd.to_numeric(chunk[column], errors="coerce")

    tract = chunk["census_tract"].astype("string").str.replace(r"\.0$", "", regex=True)
    tract = tract.str.zfill(11)
    chunk["census_tract"] = tract

    dwelling = chunk["derived_dwelling_category"].astype("string")
    keep = (
        chunk["action_taken"].eq(1)
        & chunk["loan_purpose"].isin([1, 31, 32])
        & chunk["lien_status"].eq(1)
        & chunk["reverse_mortgage"].eq(2)
        & chunk["business_or_commercial_purpose"].eq(2)
        & chunk["occupancy_type"].eq(1)
        & dwelling.str.startswith("Single Family (1-4 Units)", na=False)
        & chunk["loan_amount"].gt(0)
    )
    if require_tract:
        keep = keep & chunk["census_tract"].str.fullmatch(r"\d{11}", na=False)
    return chunk.loc[keep].copy()


def aggregate_hmda(
    files: list[tuple[int, str, Path]], tract_scores: pd.DataFrame
) -> pd.DataFrame:
    score_columns = tract_scores[["census_tract", "region", "place", "tech_score"]]
    parts: list[pd.DataFrame] = []
    coverage_parts: list[pd.DataFrame] = []
    for year, region_name, path in files:
        print(f"analyze: {path.name}")
        region_tracts = set(score_columns.loc[score_columns["region"].eq(region_name), "census_tract"])
        for chunk in pd.read_csv(
            path,
            compression="gzip",
            usecols=USECOLS,
            dtype={"lei": "string", "census_tract": "string"},
            chunksize=100_000,
            low_memory=False,
        ):
            eligible = clean_chunk(chunk, require_tract=False)
            if eligible.empty:
                continue
            valid_tract = eligible["census_tract"].str.fullmatch(r"\d{11}", na=False)
            mapped = valid_tract & eligible["census_tract"].isin(region_tracts)
            eligible["invalid_tract_count"] = (~valid_tract).astype(int)
            eligible["unmapped_tract_count"] = (valid_tract & ~mapped).astype(int)
            eligible["mapped_count"] = mapped.astype(int)
            for status in ("invalid_tract", "unmapped_tract", "mapped"):
                eligible[f"{status}_amount"] = eligible["loan_amount"].where(
                    eligible[f"{status}_count"].eq(1), 0.0
                )
            coverage = eligible.groupby(["activity_year", "lei"], dropna=False).agg(
                selected_count=("loan_amount", "size"),
                selected_amount=("loan_amount", "sum"),
                invalid_tract_count=("invalid_tract_count", "sum"),
                invalid_tract_amount=("invalid_tract_amount", "sum"),
                unmapped_tract_count=("unmapped_tract_count", "sum"),
                unmapped_tract_amount=("unmapped_tract_amount", "sum"),
                mapped_count=("mapped_count", "sum"),
                mapped_amount=("mapped_amount", "sum"),
            ).reset_index()
            coverage["region"] = region_name
            coverage_parts.append(coverage)
            clean = eligible.loc[mapped, chunk.columns].copy()
            if clean.empty:
                continue
            clean = clean.merge(score_columns, on="census_tract", how="inner")
            clean = clean.loc[clean["region"].eq(region_name)]
            if clean.empty:
                continue
            clean["positive_score"] = clean["tech_score"].clip(lower=0)
            clean["weighted_amount"] = clean["loan_amount"] * clean["positive_score"]
            clean["core_amount"] = clean["loan_amount"].where(
                clean["tech_score"].ge(0.7), 0
            )
            clean["core_count"] = clean["tech_score"].ge(0.7).astype(int)
            clean["scored_amount"] = clean["loan_amount"].where(
                clean["tech_score"].ne(0), 0
            )
            clean["scored_count"] = clean["tech_score"].ne(0).astype(int)

            grouped = (
                clean.groupby(["activity_year", "region", "lei"], dropna=False)
                .agg(
                    loan_count=("loan_amount", "size"),
                    regional_amount=("loan_amount", "sum"),
                    core_count=("core_count", "sum"),
                    core_amount=("core_amount", "sum"),
                    scored_count=("scored_count", "sum"),
                    scored_amount=("scored_amount", "sum"),
                    weighted_amount=("weighted_amount", "sum"),
                )
                .reset_index()
            )
            parts.append(grouped)

    if not parts:
        raise RuntimeError("No HMDA records survived the analytical filters")
    coverage = pd.concat(coverage_parts).groupby(
        ["activity_year", "region", "lei"], as_index=False, dropna=False
    ).sum(numeric_only=True)
    coverage["unmapped_pct"] = (
        100.0 * (coverage["invalid_tract_count"] + coverage["unmapped_tract_count"])
        / coverage["selected_count"]
    )
    coverage.sort_values(["activity_year", "region", "lei"]).to_csv(
        OUTPUT_DIR / "hmda_geography_coverage_by_lender.csv", index=False
    )
    regional_coverage = coverage.groupby(["activity_year", "region"], as_index=False).sum(numeric_only=True)
    regional_coverage["unmapped_pct"] = (
        100.0 * (regional_coverage["invalid_tract_count"] + regional_coverage["unmapped_tract_count"])
        / regional_coverage["selected_count"]
    )
    regional_coverage.to_csv(OUTPUT_DIR / "hmda_geography_coverage_summary.csv", index=False)
    result = (
        pd.concat(parts, ignore_index=True)
        .groupby(["activity_year", "region", "lei"], as_index=False)
        .sum(numeric_only=True)
    )
    return result


def aggregate_candidate_raw_originations(
    files: list[tuple[int, str, Path]],
) -> pd.DataFrame:
    known_leis = set(CANDIDATES)
    parts: list[pd.DataFrame] = []
    for _, region_name, path in files:
        for chunk in pd.read_csv(
            path,
            compression="gzip",
            usecols=["lei", "loan_amount"],
            dtype={"lei": "string"},
            chunksize=100_000,
        ):
            chunk = chunk.loc[chunk["lei"].isin(known_leis)].copy()
            if chunk.empty:
                continue
            chunk["loan_amount"] = pd.to_numeric(chunk["loan_amount"], errors="coerce")
            grouped = (
                chunk.groupby("lei", as_index=False)
                .agg(
                    raw_originated_count=("loan_amount", "size"),
                    raw_originated_amount=("loan_amount", "sum"),
                )
            )
            grouped["region"] = region_name
            parts.append(grouped)
    if not parts:
        return pd.DataFrame(
            columns=[
                "region",
                "lei",
                "raw_originated_count",
                "raw_originated_amount",
            ]
        )
    return (
        pd.concat(parts, ignore_index=True)
        .groupby(["region", "lei"], as_index=False)
        .sum(numeric_only=True)
    )


def write_data_manifest(
    files: list[tuple[int, str, Path]], config: dict[str, Any]
) -> None:
    region_config = dict(iter_regions(config))
    entries = []
    for year, region_name, path in files:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            row_count = sum(1 for _ in stream) - 1
        entries.append(
            {
                "year": year,
                "region": region_name,
                "path": str(path.relative_to(PROJECT_ROOT)),
                "url": hmda_url(year, region_config[region_name]),
                "compressed_bytes": path.stat().st_size,
                "csv_rows": row_count,
                "sha256": digest.hexdigest(),
            }
        )
    (DERIVED_DIR / "data_manifest.json").write_text(
        json.dumps({"files": entries}, indent=2), encoding="utf-8"
    )


def fetch_filer_names(years: Iterable[int], config: dict[str, Any]) -> dict[str, str]:
    counties = []
    for _, region in iter_regions(config):
        counties.extend(region["state_fips"] + c for c in region["counties"])
    params = urllib.parse.urlencode(
        {"counties": ",".join(counties), "years": ",".join(map(str, years))}
    )
    url = "https://ffiec.cfpb.gov/v2/data-browser-api/view/filers?" + params
    opener = make_hmda_opener()
    request = urllib.request.Request(url, headers=HMDA_HEADERS)
    with opener.open(request, timeout=180) as response:
        payload = json.load(response)
    return {
        str(row["lei"]): str(row["name"])
        for row in payload.get("institutions", [])
    }


def add_metrics(aggregated: pd.DataFrame, lender_names: dict[str, str]) -> pd.DataFrame:
    df = aggregated.copy()
    resolved_names = {**FALLBACK_LENDER_NAMES, **lender_names}
    df["institution"] = df["lei"].map(resolved_names).fillna(df["lei"])
    df["ticker"] = df["lei"].map(
        {lei: values["ticker"] for lei, values in CANDIDATES.items()}
    )
    df["candidate_parent"] = df["lei"].map(
        {lei: values["parent"] for lei, values in CANDIDATES.items()}
    )
    df["core_share_of_regional"] = df["core_amount"] / df["regional_amount"]
    df["weighted_score"] = df["weighted_amount"] / df["regional_amount"]
    df["core_avg_loan"] = df["core_amount"] / df["core_count"].replace(0, pd.NA)

    totals = (
        df.groupby(["activity_year", "region"], as_index=False)[
            ["core_amount", "weighted_amount", "regional_amount"]
        ]
        .sum()
        .rename(
            columns={
                "core_amount": "region_core_amount",
                "weighted_amount": "region_weighted_amount",
                "regional_amount": "region_total_amount",
            }
        )
    )
    df = df.merge(totals, on=["activity_year", "region"], how="left")
    df["core_market_share"] = df["core_amount"] / df["region_core_amount"]
    df["weighted_market_share"] = df["weighted_amount"] / df["region_weighted_amount"]
    return df


def combined_years(metrics: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "loan_count",
        "regional_amount",
        "core_count",
        "core_amount",
        "scored_count",
        "scored_amount",
        "weighted_amount",
    ]
    combined = (
        metrics.groupby(
            ["region", "lei", "institution", "ticker", "candidate_parent"],
            dropna=False,
            as_index=False,
        )[columns]
        .sum()
    )
    combined["period"] = "2023-2025"
    combined["core_share_of_regional"] = (
        combined["core_amount"] / combined["regional_amount"]
    )
    combined["weighted_score"] = combined["weighted_amount"] / combined["regional_amount"]
    combined["core_avg_loan"] = combined["core_amount"] / combined["core_count"].replace(
        0, pd.NA
    )
    totals = (
        combined.groupby("region", as_index=False)[["core_amount", "weighted_amount"]]
        .sum()
        .rename(
            columns={
                "core_amount": "region_core_amount",
                "weighted_amount": "region_weighted_amount",
            }
        )
    )
    combined = combined.merge(totals, on="region", how="left")
    combined["core_market_share"] = combined["core_amount"] / combined["region_core_amount"]
    combined["weighted_market_share"] = (
        combined["weighted_amount"] / combined["region_weighted_amount"]
    )
    return combined


def fmt_money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def write_markdown_report(
    eligible: pd.DataFrame,
    candidates: pd.DataFrame,
    year_totals: pd.DataFrame,
) -> None:
    lines = [
        "# HMDA tech-core origination screen: first-stage findings",
        "",
        "Generated from 2023–2025 HMDA snapshot data and Census TIGERweb geography.",
        "",
        "## Executive read",
        "",
        (
            "This screen measures where lenders originated qualifying principal-residence "
            "mortgages. It does not measure loans currently retained on bank balance sheets."
        ),
        "",
        (
            "Among the Seattle candidates imported from the conversation, WAFD has the "
            "highest tech-core concentration, while FSBW has the largest observed tech-core "
            "origination footprint. Those are different claims: WAFD's qualifying regional "
            "originations are more geographically concentrated, but FSBW originated more "
            "qualifying tech-core dollars and loans over the three-year window."
        ),
        "",
        (
            "For the Bay Area candidates, residential HMDA is mostly non-diagnostic. EWBC "
            "has observable volume, while BMRC, CVBF, and BCML have no qualifying records in "
            "this screen. Their thesis is primarily a CRE/balance-sheet question and requires "
            "Call Report, SEC filing, and property-level work."
        ),
        "",
        "## Regional totals by year",
        "",
        "| Year | Region | Qualifying loans | Regional amount | Core amount | Weighted amount |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    for row in year_totals.itertuples(index=False):
        lines.append(
            f"| {int(row.activity_year)} | {row.region} | {int(row.loan_count):,} | "
            f"{fmt_money(row.regional_amount)} | {fmt_money(row.core_amount)} | "
            f"{fmt_money(row.weighted_amount)} |"
        )

    lines.extend(["", "## Candidate banks", ""])
    for region in sorted(candidates["region"].unique()):
        lines.extend(
            [
                f"### {region}",
                "",
                "| Ticker | HMDA filer | Loans | Core loans | Core amount | Weighted score | Weighted market share | Coverage |",
                "|---|---|---:|---:|---:|---:|---:|---|",
            ]
        )
        group = candidates.loc[candidates["region"].eq(region)].sort_values(
            "weighted_amount", ascending=False
        )
        for row in group.itertuples(index=False):
            lines.append(
                f"| {row.ticker} | {row.institution} | {int(row.loan_count):,} | "
                f"{int(row.core_count):,} | {fmt_money(row.core_amount)} | "
                f"{fmt_pct(row.weighted_score)} | {fmt_pct(row.weighted_market_share)} | "
                f"{row.coverage_status} |"
            )
        lines.append("")

    lines.extend(["## Largest weighted tech-core originators", ""])
    for region, group in eligible.groupby("region"):
        lines.extend(
            [
                f"### {region}",
                "",
                "| Rank | Institution | Loans | Core amount | Weighted score | Weighted market share |",
                "|---:|---|---:|---:|---:|---:|",
            ]
        )
        for rank, row in enumerate(
            group.nlargest(12, "weighted_amount").itertuples(index=False), start=1
        ):
            lines.append(
                f"| {rank} | {row.institution} | {int(row.loan_count):,} | "
                f"{fmt_money(row.core_amount)} | {fmt_pct(row.weighted_score)} | "
                f"{fmt_pct(row.weighted_market_share)} |"
            )
        lines.append("")

    lines.extend(
        [
            "## Interpretation limits",
            "",
            "1. HMDA is an origination-flow dataset, not a current stock-of-loans dataset.",
            "2. Originators may sell loans; purchaser and securitization behavior must be modeled before inferring retained exposure.",
            "3. CRE is not covered by this residential screen. BMRC, CVBF, and BCML cannot be ranked safely from these results.",
            "4. Tech scores are explicit scenario weights from the imported hypothesis, not fitted causal coefficients.",
            "5. Tracts are assigned by Census interior point; boundary tracts can be misclassified when a tract spans city limits.",
            "6. Candidate rankings depend on the named-city list and threshold; see residential_geography_sensitivity.csv for alternative definitions.",
            "",
            "## Next quantitative step",
            "",
            (
                "Estimate retained residential balances by lender and vintage using purchaser type, "
                "amortization, and prepayment assumptions; then join bank Call Report/SEC capital "
                "data to compute estimated tech-core retained mortgage exposure divided by tangible "
                "common equity. Build the CRE leg separately."
            ),
            "",
            "## Official sources",
            "",
            "- https://ffiec.cfpb.gov/documentation/api/data-browser/",
            "- https://ffiec.cfpb.gov/data-browser/data/",
            "- https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0",
            "- https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4",
        ]
    )
    (OUTPUT_DIR / "first_stage_findings.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_outputs(
    metrics: pd.DataFrame,
    combined: pd.DataFrame,
    tract_scores: pd.DataFrame,
    raw_candidate_totals: pd.DataFrame,
) -> None:
    metrics = metrics.sort_values(
        ["activity_year", "region", "weighted_amount"], ascending=[True, True, False]
    )
    combined = combined.sort_values(
        ["region", "weighted_amount"], ascending=[True, False]
    )
    metrics.to_csv(OUTPUT_DIR / "lender_metrics_by_year.csv", index=False)
    combined.to_csv(OUTPUT_DIR / "lender_metrics_2023_2025.csv", index=False)

    eligible = combined.loc[
        (combined["loan_count"] >= 60) & (combined["core_count"] >= 10)
    ].copy()
    eligible["concentration_rank"] = eligible.groupby("region")[
        "weighted_score"
    ].rank(method="min", ascending=False)
    eligible["market_share_rank"] = eligible.groupby("region")[
        "weighted_market_share"
    ].rank(method="min", ascending=False)
    eligible.to_csv(OUTPUT_DIR / "eligible_lender_ranking_2023_2025.csv", index=False)

    candidate_rows: list[dict[str, Any]] = []
    for catalog_row in CANDIDATE_CATALOG:
        for region in sorted(combined["region"].unique()):
            lei = catalog_row["lei"]
            raw_match = raw_candidate_totals.loc[
                raw_candidate_totals["region"].eq(region)
                & raw_candidate_totals["lei"].eq(lei)
            ]
            raw_count = int(raw_match.iloc[0]["raw_originated_count"]) if not raw_match.empty else 0
            raw_amount = float(raw_match.iloc[0]["raw_originated_amount"]) if not raw_match.empty else 0.0
            observed = combined.loc[
                combined["region"].eq(region) & combined["lei"].eq(lei)
            ]
            if observed.empty:
                row = {
                    "region": region,
                    "lei": lei,
                    "institution": catalog_row["institution"],
                    "ticker": catalog_row["ticker"],
                    "candidate_parent": catalog_row["parent"],
                    "loan_count": 0,
                    "regional_amount": 0.0,
                    "core_count": 0,
                    "core_amount": 0.0,
                    "scored_count": 0,
                    "scored_amount": 0.0,
                    "weighted_amount": 0.0,
                    "period": "2023-2025",
                    "core_share_of_regional": 0.0,
                    "weighted_score": 0.0,
                    "core_avg_loan": None,
                    "region_core_amount": None,
                    "region_weighted_amount": None,
                    "core_market_share": 0.0,
                    "weighted_market_share": 0.0,
                    "coverage_status": (
                        f"{raw_count} originated HMDA records in selected counties, but "
                        "none matched the residential screen; not evidence of zero "
                        "balance-sheet exposure"
                        if raw_count
                        else "No qualifying filtered HMDA originations observed; not "
                        "evidence of zero balance-sheet exposure"
                    ),
                    "hmda_scope_note": catalog_row["hmda_scope_note"],
                }
            else:
                row = observed.iloc[0].to_dict()
                row["coverage_status"] = "Observed qualifying HMDA originations"
                row["hmda_scope_note"] = catalog_row["hmda_scope_note"]
            row["raw_originated_count"] = raw_count
            row["raw_originated_amount"] = raw_amount
            ranked = eligible.loc[
                eligible["region"].eq(region) & eligible["lei"].eq(lei)
            ]
            row["concentration_rank"] = (
                float(ranked.iloc[0]["concentration_rank"]) if not ranked.empty else None
            )
            row["market_share_rank"] = (
                float(ranked.iloc[0]["market_share_rank"]) if not ranked.empty else None
            )
            candidate_rows.append(row)
    candidates = pd.DataFrame(candidate_rows).sort_values(
        ["region", "weighted_amount"], ascending=[True, False]
    )
    candidates.to_csv(OUTPUT_DIR / "candidate_banks_2023_2025.csv", index=False)

    year_totals = (
        metrics.groupby(["activity_year", "region"], as_index=False)
        .agg(
            loan_count=("loan_count", "sum"),
            regional_amount=("regional_amount", "sum"),
            core_count=("core_count", "sum"),
            core_amount=("core_amount", "sum"),
            weighted_amount=("weighted_amount", "sum"),
        )
        .sort_values(["region", "activity_year"])
    )
    year_totals.to_csv(OUTPUT_DIR / "regional_totals_by_year.csv", index=False)
    write_markdown_report(eligible, candidates, year_totals)

    top_by_region: dict[str, list[dict[str, Any]]] = {}
    for region, group in eligible.groupby("region"):
        display = group.nlargest(15, "weighted_amount")
        top_by_region[region] = json.loads(
            display[
                [
                    "institution",
                    "ticker",
                    "loan_count",
                    "regional_amount",
                    "core_count",
                    "core_amount",
                    "weighted_amount",
                    "weighted_score",
                    "weighted_market_share",
                ]
            ].to_json(orient="records")
        )

    summary = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "years": list(YEARS),
        "filters": {
            "action_taken": "1 (originated)",
            "loan_purpose": ["1 home purchase", "31 refinancing", "32 cash-out refinancing"],
            "lien_status": "1 (first lien)",
            "reverse_mortgage": "2 (not reverse)",
            "business_or_commercial_purpose": "2 (not business/commercial)",
            "occupancy_type": "1 (principal residence)",
            "dwelling": "Single Family (1-4 Units)",
        },
        "methodology_warning": (
            "HMDA reports originations/applications, not current loan holdings. "
            "This is an origination-footprint screen, not balance-sheet exposure."
        ),
        "tract_count": int(len(tract_scores)),
        "top_lenders": top_by_region,
        "candidate_banks": json.loads(
            candidates[
                [
                    "region",
                    "institution",
                    "ticker",
                    "loan_count",
                    "regional_amount",
                    "core_count",
                    "core_amount",
                    "weighted_amount",
                    "weighted_score",
                    "weighted_market_share",
                    "raw_originated_count",
                    "raw_originated_amount",
                    "coverage_status",
                    "hmda_scope_note",
                ]
            ].to_json(orient="records")
        ),
        "sources": [
            "https://ffiec.cfpb.gov/documentation/api/data-browser/",
            "https://ffiec.cfpb.gov/data-browser/data/",
            "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0",
            "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4",
        ],
    }
    (OUTPUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def run(force_download: bool = False) -> None:
    ensure_dirs()
    config = load_config()
    tract_scores = build_tract_scores(config)
    opener = make_hmda_opener()
    files: list[tuple[int, str, Path]] = []
    for year in YEARS:
        for region_name, region in iter_regions(config):
            path = download_hmda_file(
                opener, year, region_name, region, force=force_download
            )
            files.append((year, region_name, path))
    write_data_manifest(files, config)
    aggregated = aggregate_hmda(files, tract_scores)
    raw_candidate_totals = aggregate_candidate_raw_originations(files)
    lender_names = fetch_filer_names(YEARS, config)
    metrics = add_metrics(aggregated, lender_names)
    combined = combined_years(metrics)
    write_outputs(metrics, combined, tract_scores, raw_candidate_totals)
    print("done")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Replace cached HMDA downloads.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    run(force_download=args.force_download)
