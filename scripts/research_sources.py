#!/usr/bin/env python3
"""Content-addressed V2 evidence cache and historical SEC document discovery.

No reviewed observations are inferred from keyword matches. Network failures are
recorded, not silently replaced with stale or invented observations.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

from lxml import html
from sec_filing_screen import html_to_text

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / 'data/raw/v2'
TEXT = ROOT / 'data/derived/v2_text'
OUT = ROOT / 'outputs/v2'
CIKS = {'WAFD': 936528, 'COLB': 887343, 'HPP': 1482512, 'KRC': 1025996}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def download(url: str, refresh=False) -> dict:
    """URL index is mutable; underlying downloaded revisions are immutable."""
    RAW.mkdir(parents=True, exist_ok=True)
    key = digest(url.encode())
    meta_path = RAW / f'{key}.json'
    if meta_path.exists() and not refresh:
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        if digest((ROOT / meta['raw_path']).read_bytes()) != meta['sha256']:
            raise ValueError(f'Cached source hash mismatch: {url}')
        return meta
    ua = os.environ.get('SEC_USER_AGENT', 'Research Jack31098 github.com/Jack31098')
    request = urllib.request.Request(url, headers={'User-Agent': ua, 'Accept-Language': 'en-US,en;q=0.9'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
        content_type = response.headers.get('Content-Type', '')
        final_url = response.url
    sha = digest(data)
    suffix = '.pdf' if data.startswith(b'%PDF') else ('.json' if 'json' in content_type else '.html')
    if 'image/' in content_type:
        suffix = Path(urlparse(url).path).suffix
    raw_path = RAW / f'{sha}{suffix}'
    raw_path.write_bytes(data)
    meta = {'url': url, 'resolved_url': final_url, 'sha256': sha, 'bytes': len(data),
            'content_type': content_type, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'raw_path': raw_path.relative_to(ROOT).as_posix()}
    write_json(meta_path, meta)
    time.sleep(0.15)  # Stay well below SEC's per-second request limit.
    return meta


def extract(meta: dict) -> dict:
    path = ROOT / meta['raw_path']
    data = path.read_bytes()
    if data.startswith(b'%PDF'):
        from pypdf import PdfReader
        pages = [page.extract_text(extraction_mode='layout') for page in PdfReader(io.BytesIO(data)).pages]
        text = '\n'.join(f'\n=== PDF PAGE {i+1} ===\n{v}' for i, v in enumerate(pages))
        kind = 'pdf_text'
    elif 'html' in meta['content_type'] or path.suffix == '.html':
        tree = html.fromstring(data)
        text = html_to_text(data)
        # SEC slide decks often carry embedded alt text; preserve it explicitly.
        alts = tree.xpath('//img/@alt')
        if alts:
            text += '\n=== IMAGE ALT TEXT (requires visual review) ===\n' + '\n'.join(alts)
        kind = 'html_text_and_alt'
    else:
        return {**meta, 'extraction_status': 'not_text'}
    TEXT.mkdir(parents=True, exist_ok=True)
    target = TEXT / f"{meta['sha256']}.txt"
    target.write_text(text, encoding='utf-8')
    return {**meta, 'text_path': target.relative_to(ROOT).as_posix(), 'extraction_status': kind}


def source_id(spec, sha):
    # Includes URL/document identity even when two documents have identical bytes.
    identity = '|'.join(str(spec.get(x, '')) for x in ('cik','accession','url')) + '|' + sha
    return 'src_' + digest(identity.encode())[:24]


def fetch_catalog(refresh=False):
    specs = json.loads((ROOT / 'config/v2_sources.json').read_text(encoding='utf-8'))
    path = OUT / 'source_manifest.json'
    previous = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    existing = {x['source_id']: x for x in previous}
    errors = []
    for spec in specs:
        try:
            if spec.get('import_path') and (ROOT / spec['import_path']).exists() and not refresh:
                payload = (ROOT / spec['import_path']).read_bytes()
                if digest(payload) != spec['expected_sha256']:
                    raise ValueError('Reviewed legacy cache hash mismatch')
                meta = extract({'url':spec['url'], 'sha256':digest(payload), 'bytes':len(payload),
                                'raw_path':spec['import_path'], 'content_type':'text/html',
                                'retrieved_at':None, 'cache_imported_at':datetime.now(timezone.utc).isoformat(),
                                'retrieval_note':'Legacy cache; original retrieval timestamp unknown'})
            else:
                meta = extract(download(spec['url'], refresh))
            row = {**spec, **meta, 'source_id': source_id(spec, meta['sha256'])}
            existing[row['source_id']] = row
            print(f"source {spec['key']}: {meta['bytes']} bytes", flush=True)
        except Exception as e:
            errors.append({'key': spec['key'], 'url': spec['url'], 'error': str(e)})
            print(f"FAILED {spec['key']}: {e}", flush=True)
    write_json(path, list(existing.values()))
    write_json(OUT / 'source_download_errors.json', errors)
    return list(existing.values())


def filing_rows(block, ticker, cik, start, end):
    rows = []
    for i, form in enumerate(block.get('form', [])):
        filed = block['filingDate'][i]
        if form not in {'10-K','10-Q','8-K','10-K/A','10-Q/A','8-K/A'} or not start <= filed <= end:
            continue
        accession = block['accessionNumber'][i]
        base = f'https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace("-", "")}/'
        rows.append({'ticker': ticker, 'cik': cik, 'form': form, 'filing_date': filed,
                     'report_date': block.get('reportDate', ['']*len(block['form']))[i],
                     'accepted_at': block.get('acceptanceDateTime', ['']*len(block['form']))[i],
                     'items': block.get('items', ['']*len(block['form']))[i], 'accession': accession,
                     'document_url': base + block['primaryDocument'][i],
                     'index_url': base + accession + '-index.html'})
    return rows


def discover(tickers, start, end, exhibits=False):
    result, documents, failures = [], [], []
    for ticker in tickers:
        cik = CIKS[ticker]
        try:
            meta = download(f'https://data.sec.gov/submissions/CIK{cik:010d}.json')
            sub = json.loads((ROOT / meta['raw_path']).read_bytes())
            rows = filing_rows(sub['filings']['recent'], ticker, cik, start, end)
            for old in sub['filings'].get('files', []):
                if old['filingTo'] < start or old['filingFrom'] > end:
                    continue
                oldmeta = download('https://data.sec.gov/submissions/' + old['name'])
                rows += filing_rows(json.loads((ROOT / oldmeta['raw_path']).read_bytes()), ticker, cik, start, end)
            unique = {x['accession']: x for x in rows}
            result += list(unique.values())
            print(f'{ticker}: {len(unique)} historical filings', flush=True)
            if exhibits:
                for row in unique.values():
                    try:
                        idx = download(row['index_url'])
                        tree = html.fromstring((ROOT / idx['raw_path']).read_bytes())
                        for tr in tree.xpath('//table[contains(@class,"tableFile")]/tr'):
                            cells = tr.xpath('./td')
                            if len(cells) < 4:
                                continue
                            typ = cells[3].text_content().strip()
                            links = cells[2].xpath('.//a/@href')
                            if links and (typ.startswith('EX-99') or typ in {'10-K','10-Q','8-K','10-K/A','10-Q/A','8-K/A'}):
                                documents.append({**row, 'document_type':typ, 'description':cells[1].text_content().strip(),
                                                  'document_url': urljoin(row['index_url'], links[0]),
                                                  'review_status':'discovered_unreviewed'})
                    except Exception as e:
                        failures.append({'ticker':ticker, 'url':row['index_url'], 'error':str(e)})
        except Exception as e:
            failures.append({'ticker':ticker, 'error':str(e)})
    write_json(OUT / 'sec_historical_filings.json', result)
    write_json(OUT / 'sec_historical_documents.json', documents)
    write_json(OUT / 'sec_discovery_errors.json', failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--discover', action='store_true')
    parser.add_argument('--exhibits', action='store_true')
    parser.add_argument('--refresh', action='store_true')
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default='2026-10-07')
    parser.add_argument('--tickers', nargs='+', default=['WAFD','COLB'])
    args = parser.parse_args()
    if args.discover:
        discover(args.tickers, args.start, args.end, args.exhibits)
    else:
        fetch_catalog(args.refresh)
