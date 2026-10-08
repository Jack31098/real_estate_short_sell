"""Targeted original-quarter documents for the October 2026 research pass."""
import json
from research_sources import ROOT, OUT, download, extract, write_json, source_id

WAFD = [('2024-03-31','20240422','press'),('2024-06-30','20240716','press'),
        ('2024-09-30','20241017','earnings'),('2024-12-31','20250116','press'),
        ('2025-03-31','20250411','press'),('2025-06-30','20250717','press'),
        ('2025-09-30','20251016','press'),('2025-12-31','20260115','press'),
        ('2026-03-31','20260416','press'),('2026-06-30','20260716','press')]

def fetch(specs):
    path = OUT/'core_source_manifest.json'
    prior = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    rows = {x['source_id']:x for x in prior}
    for spec in specs:
        meta = extract(download(spec['url']))
        row = {**spec, **meta, 'source_id':source_id(spec,meta['sha256'])}
        rows[row['source_id']] = row
        write_json(path,list(rows.values()))
        print(spec['key'],meta.get('text_path',meta['raw_path']),flush=True)
    return list(rows.values())

if __name__ == '__main__':
    specs = [{'key':'wafd_history_'+end,'ticker':'WAFD','period_end':end,
              'published_at':f'{d[:4]}-{d[4:6]}-{d[6:]}','document_type':'earnings_release',
              'url':f'https://www.wafdbank.com/documents/financial-news/{d[:4]}/wafd-bank-{kind}-release-{d}.pdf'}
             for end,d,kind in WAFD]
    extra = ROOT/'config/core_path_sources.json'
    if extra.exists(): specs += json.loads(extra.read_text(encoding='utf-8'))
    fetch(specs)
