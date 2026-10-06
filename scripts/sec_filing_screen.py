#!/usr/bin/env python3
"""Download and index the latest SEC 10-K and 10-Q for candidate banks."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
import urllib.request
from pathlib import Path
from typing import Any

import pandas as pd
from lxml import etree, html


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "sec"
DERIVED_DIR = PROJECT_ROOT / "data" / "derived" / "sec_text"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

TICKERS = ["FSBW", "WAFD", "BMRC", "BCML", "CVBF", "COLB", "EWBC"]
SEC_HEADERS = {
    "User-Agent": "Codex research automation support@openai.com",
    "Accept-Language": "en-US,en;q=0.9",
}

KEYWORDS = [
    "geographic concentration",
    "market area",
    "Seattle",
    "Puget Sound",
    "King County",
    "Snohomish",
    "Bellevue",
    "Redmond",
    "Washington",
    "San Francisco Bay Area",
    "Bay Area",
    "Silicon Valley",
    "Santa Clara",
    "San Mateo",
    "Marin",
    "Sonoma",
    "office",
    "multifamily",
    "non-owner occupied",
    "owner-occupied",
    "commercial real estate",
    "construction and land development",
    "concentration",
]


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers=SEC_HEADERS)
    with urllib.request.urlopen(request, timeout=90) as response:
        return response.read()


def fetch_json(url: str) -> dict[str, Any]:
    return json.loads(fetch_bytes(url).decode("utf-8"))


def latest_filing_rows() -> list[dict[str, Any]]:
    ticker_payload = fetch_json("https://www.sec.gov/files/company_tickers.json")
    ticker_map = {row["ticker"].upper(): row for row in ticker_payload.values()}
    rows: list[dict[str, Any]] = []
    for ticker in TICKERS:
        company = ticker_map[ticker]
        cik = int(company["cik_str"])
        submissions_url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        submissions = fetch_json(submissions_url)
        recent = submissions["filings"]["recent"]
        selected: set[str] = set()
        for index, form in enumerate(recent["form"]):
            if form not in {"10-K", "10-Q"} or form in selected:
                continue
            accession = recent["accessionNumber"][index]
            accession_compact = accession.replace("-", "")
            primary_document = recent["primaryDocument"][index]
            document_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                f"{accession_compact}/{primary_document}"
            )
            index_url = (
                f"https://www.sec.gov/Archives/edgar/data/{cik}/"
                f"{accession_compact}/{accession}-index.html"
            )
            rows.append(
                {
                    "ticker": ticker,
                    "company": company["title"],
                    "cik": cik,
                    "form": form,
                    "filing_date": recent["filingDate"][index],
                    "report_date": recent["reportDate"][index],
                    "accession": accession,
                    "primary_document": primary_document,
                    "document_url": document_url,
                    "index_url": index_url,
                    "submissions_url": submissions_url,
                }
            )
            selected.add(form)
            if len(selected) == 2:
                break
        time.sleep(0.15)
    return rows


def html_to_text(payload: bytes) -> str:
    document = html.fromstring(payload)
    # Inline-XBRL namespaces are not always bound consistently across issuers.
    # local-name() also removes hidden ix:header blocks when the prefix binding
    # differs from the canonical 2013 namespace.
    for node in document.xpath(
        "//script|//style|//*[local-name()='header' and "
        "(contains(namespace-uri(), 'inlineXBRL') or starts-with(name(), 'ix:'))]"
    ):
        parent = node.getparent()
        if parent is not None:
            parent.remove(node)
    text = etree.tostring(document, method="text", encoding="unicode")
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip() + "\n"


def keyword_hits(text: str, row: dict[str, Any], window: int = 360) -> list[dict[str, Any]]:
    normalized = re.sub(r"\s+", " ", text)
    hits: list[dict[str, Any]] = []
    for keyword in KEYWORDS:
        positions = [match.start() for match in re.finditer(re.escape(keyword), normalized, flags=re.I)]
        selected: list[int] = []
        for position in positions:
            if not selected or position - selected[-1] > window:
                selected.append(position)
            if len(selected) >= 8:
                break
        for position in selected:
            start = max(0, position - window)
            end = min(len(normalized), position + len(keyword) + window)
            hits.append(
                {
                    "ticker": row["ticker"],
                    "form": row["form"],
                    "report_date": row["report_date"],
                    "keyword": keyword,
                    "character_offset": position,
                    "snippet": normalized[start:end],
                    "document_url": row["document_url"],
                }
            )
    return hits


def run(refresh: bool = False) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = latest_filing_rows()
    hits: list[dict[str, Any]] = []
    for row in rows:
        stem = f"{row['ticker']}_{row['form'].replace('-', '')}_{row['report_date']}"
        html_path = RAW_DIR / f"{stem}.html"
        text_path = DERIVED_DIR / f"{stem}.txt"
        if refresh or not html_path.exists():
            print(f"download: {row['ticker']} {row['form']} {row['report_date']}")
            payload = fetch_bytes(row["document_url"])
            html_path.write_bytes(payload)
            time.sleep(0.15)
        else:
            payload = html_path.read_bytes()
        text = html_to_text(payload)
        text_path.write_text(text, encoding="utf-8")
        row["html_path"] = str(html_path.relative_to(PROJECT_ROOT))
        row["text_path"] = str(text_path.relative_to(PROJECT_ROOT))
        row["html_bytes"] = len(payload)
        row["sha256"] = hashlib.sha256(payload).hexdigest()
        hits.extend(keyword_hits(text, row))

    pd.DataFrame(rows).sort_values(["ticker", "form"]).to_csv(
        OUTPUT_DIR / "sec_filings_manifest.csv", index=False
    )
    pd.DataFrame(hits).sort_values(["ticker", "form", "keyword", "character_offset"]).to_csv(
        OUTPUT_DIR / "sec_keyword_hits.csv", index=False
    )
    print(f"indexed {len(rows)} filings and {len(hits)} keyword contexts")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="Replace cached filing HTML")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(refresh=args.refresh)
