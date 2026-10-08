"""Run the four research priorities; no complete-document-backfill prerequisite.

Default: rebuild original-quarter and property panels from cached source bytes.
--from-panels: on another computer, reproduce scenarios, events, figures and
report using tracked extracted panels, without downloading the ignored raw cache.
"""
import argparse
import json
import platform
from datetime import datetime,timezone
import pandas as pd
from research_sources import ROOT,OUT,digest,write_json
from research_contract import code_manifest

def run(from_panels=False):
    code=code_manifest('core_')
    if not from_panels:
        import core_history,core_filing_history,property_core
        sources=json.loads((OUT/'core_source_manifest.json').read_text())
        for m in sources:
            if digest((ROOT/m['raw_path']).read_bytes())!=m['sha256']:raise ValueError('Raw source hash changed: '+m['key'])
        for key in ['redfin_housing','redfin_price_drops','fhfa_purchase','nwmls_king']:
            m=json.loads((OUT/(key+'_source.json')).read_text())
            if digest((ROOT/m['raw_path']).read_bytes())!=m['sha256']:raise ValueError('Raw source hash changed: '+key)
        core_history.run();core_filing_history.run();property_core.run(code)
    import colb_refi,hpp_bridge,core_event_sensitivity,core_charts,core_report
    colb_refi.run(code);hpp_bridge.run(code);core_event_sensitivity.run(code);core_charts.run()
    rows=json.loads((OUT/'core_history_observations.json').read_text())
    definitions={r['metric_definition_version']:{'metric':r['metric'],'unit':r['unit'],
        'definition':'See source_row, notes and input_observation_ids in core_history_observations.json.'} for r in rows}
    write_json(OUT/'core_metric_definitions.json',definitions)
    inputs=['core_history_observations.json','core_source_manifest.json','property_redfin_selected.csv',
        'property_monthly_long.csv','property_hpi_quarterly.csv','property_nwmls_september.csv',
        'market_daily.csv','treasury_daily.csv','source_manifest.json']
    write_json(OUT/'core_run_manifest.json',dict(transform_code_version=code,
        executed_at=datetime.now(timezone.utc).isoformat(),data_as_of='2026-10-07 America/Los_Angeles',
        mode='tracked extracted panels' if from_panels else 'raw-source rebuild',python=platform.python_version(),
        pandas=pd.__version__,source_document_count=len(json.loads((OUT/'core_source_manifest.json').read_text())),
        bank_observations=len(rows),input_hashes={n:digest((OUT/n).read_bytes()) for n in inputs},
        property_vintage='October 7 current revised snapshot; not a historical point-in-time archive',
        coverage_notes=['WAFD early substandard is not relabelled classified.','HPP is a June-anchor known-event bridge, not an observed October balance sheet.',
        'No validated matched peer basket; no causal AI attribution or dollar credit-loss estimate.']))
    core_report.run()
    print('Wrote outputs/v2/core_path_report_zh.md and five figures.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--from-panels',action='store_true')
    run(p.parse_args().from_panels)
