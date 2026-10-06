#!/usr/bin/env python3
"""Re-rank observed candidate residential originations under place-list scenarios.

These scenarios change the inclusion threshold or exclude named places from the
manually scored geography. The legacy-city scenario removes San Jose and Santa
Clara to reproduce the earlier place list after their mapping was added.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

import pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "outputs"
TRACT_SCORES = PROJECT_ROOT / "data" / "derived" / "tract_scores.csv"

BASE_THRESHOLD = pipeline.core_threshold()
BASE_SCENARIO = f"baseline_t{BASE_THRESHOLD:g}"
SCENARIOS = (
    (BASE_SCENARIO, BASE_THRESHOLD, ()),
    ("legacy_exclude_new_cities", BASE_THRESHOLD, ("San Jose", "Santa Clara")),
    ("inclusive_t0.4", 0.4, ()),
    ("narrow_t0.9", 0.9, ()),
    ("exclude_Seattle", BASE_THRESHOLD, ("Seattle",)),
    ("exclude_San_Francisco", BASE_THRESHOLD, ("San Francisco",)),
)
REGION_BY_SLUG = {
    "bay-area": "Bay Area",
    "seattle-puget-sound": "Seattle/Puget Sound",
}


def scenario_mask(
    frame: pd.DataFrame, threshold: float, excluded_places: tuple[str, ...] | str
) -> pd.Series:
    mask = frame["tech_score"].ge(threshold)
    if isinstance(excluded_places, str):
        excluded_places = (excluded_places,) if excluded_places else ()
    if excluded_places:
        mask &= ~frame["place"].isin(excluded_places)
    return mask


def run() -> pd.DataFrame:
    scores = pd.read_csv(TRACT_SCORES, dtype={"census_tract": "string"})[
        ["census_tract", "region", "place", "tech_score"]
    ]
    if scores["census_tract"].duplicated().any():
        raise ValueError("Tract scores contain duplicate census tracts")
    files = sorted(RAW_DIR.glob("hmda_*_originated.csv.gz"))
    if len(files) != 6:
        raise FileNotFoundError("Expected six cached 2023–2025 HMDA files; run pipeline.py first")
    known_leis = set(pipeline.CANDIDATES)
    parts: list[pd.DataFrame] = []
    place_parts: list[pd.DataFrame] = []
    for path in files:
        year = int(path.name.split("_")[1])
        slug = path.name[len(f"hmda_{year}_") : -len("_originated.csv.gz")]
        region = REGION_BY_SLUG[slug]
        for chunk in pd.read_csv(
            path,
            compression="gzip",
            usecols=pipeline.USECOLS,
            dtype={"lei": "string", "census_tract": "string"},
            chunksize=100_000,
            low_memory=False,
        ):
            clean = pipeline.clean_chunk(chunk.loc[chunk["lei"].isin(known_leis)].copy())
            if clean.empty:
                continue
            scored = clean.merge(scores, on="census_tract", how="inner", validate="many_to_one")
            scored = scored.loc[scored["region"].eq(region)]
            if scored.empty:
                continue
            by_place = scored.groupby(["lei", "place"], as_index=False).agg(
                loan_count=("loan_amount", "size"),
                originated_amount=("loan_amount", "sum"),
            )
            by_place["activity_year"] = year
            by_place["region"] = region
            place_parts.append(by_place)
            for scenario, threshold, excluded_places in SCENARIOS:
                subset = scored.loc[scenario_mask(scored, threshold, excluded_places)]
                if subset.empty:
                    continue
                grouped = subset.groupby("lei", as_index=False).agg(
                    core_loan_count=("loan_amount", "size"),
                    core_origination_amount=("loan_amount", "sum"),
                )
                grouped["scenario"] = scenario
                grouped["region"] = region
                parts.append(grouped)
    if not parts:
        raise RuntimeError("No candidate mortgage originations in sensitivity scenarios")
    totals = pd.concat(parts).groupby(["scenario", "region", "lei"], as_index=False).sum(numeric_only=True)
    catalog = pd.DataFrame(pipeline.CANDIDATE_CATALOG)[["lei", "ticker", "institution"]]
    grid = pd.MultiIndex.from_product(
        [[item[0] for item in SCENARIOS], REGION_BY_SLUG.values(), catalog["lei"]],
        names=["scenario", "region", "lei"],
    ).to_frame(index=False)
    result = grid.merge(totals, on=["scenario", "region", "lei"], how="left", validate="one_to_one")
    result = result.merge(catalog, on="lei", how="left", validate="many_to_one")
    result[["core_loan_count", "core_origination_amount"]] = result[
        ["core_loan_count", "core_origination_amount"]
    ].fillna(0)
    result["origination_rank"] = result.groupby(["scenario", "region"])[
        "core_origination_amount"
    ].rank(method="min", ascending=False).where(result["core_origination_amount"].gt(0))
    result = result.sort_values(["scenario", "region", "origination_rank", "ticker"])

    by_place = pd.concat(place_parts).groupby(
        ["activity_year", "region", "lei", "place"], as_index=False
    ).sum(numeric_only=True)
    by_place = by_place.merge(catalog, on="lei", how="left", validate="many_to_one")
    by_place.sort_values(["activity_year", "region", "ticker", "place"]).to_csv(
        OUTPUT_DIR / "candidate_originations_by_place_2023_2025.csv", index=False
    )

    baseline = result.loc[result["scenario"].eq(BASE_SCENARIO)]
    prior = pd.read_csv(OUTPUT_DIR / "candidate_banks_2023_2025.csv")
    check = baseline.merge(prior[["region", "ticker", "core_amount"]], on=["region", "ticker"], validate="one_to_one")
    if len(check) != len(baseline) or not (
        (check["core_origination_amount"] - check["core_amount"]).abs() < 1.0
    ).all():
        raise RuntimeError("Sensitivity baseline does not reconcile to the original candidate screen")
    result.to_csv(OUTPUT_DIR / "residential_geography_sensitivity.csv", index=False)
    return result


if __name__ == "__main__":
    result = run()
    print(f"wrote {len(result)} residential geography sensitivity rows")
