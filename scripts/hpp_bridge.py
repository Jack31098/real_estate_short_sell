"""Event bridge on a June anchor; preserve announced versus completed actions."""
import json
import pandas as pd
from research_sources import ROOT,OUT,write_json

def run(code):
    a=json.loads((ROOT/'config/hpp_bridge_facts.json').read_text())
    sources={s['key']:s for s in json.loads((OUT/'source_manifest.json').read_text())}
    h=a['hollywood'];moved=h['gross_principal']*h['ownership']-h['hpp_acquired_debt_offset']
    rows=[]
    for year,balance in a['maturity_baseline'].items():
        change=-moved if year=='2026' else moved if year=='2027' else 0
        rows.append(dict(year=int(year),june_maturity=balance,executed_extension_shift=change,
            completed_tender_reduction=0,unallocated_sale_debt_repayment=None,
            june_anchor_known_events=balance+change,status='derived',unit=a['unit'],
            source_id=sources['hpp_2026q2_supplement']['source_id'],page=14,
            extension_source_id=sources[h['key']]['source_id'],assumption_set_id=a['assumption_set_id'],
            transform_code_version=code,metric_definition_version='HPP-known-event-maturity@1'))
    f=pd.DataFrame(rows);f.to_csv(OUT/'hpp_debt_bridge.csv',index=False)
    assert abs(f.june_maturity.sum()-f.june_anchor_known_events.sum())<1e-8
    lease=a['lease']; remaining=lease['2027_current_ABR_june']-lease['2027_current_ABR_identified_sold_glu']
    tender=a['tender']
    write_json(OUT/'hpp_current_bridge.json',dict(facts=a,hollywood_hpp_net_shift=moved,
        total_hpp_share_debt_june=float(f.june_maturity.sum()),
        maturity_2027_known_events=float(f.loc[f.year==2027,'june_anchor_known_events'].iloc[0]),
        lease_2027_identified_sale_adjusted_current_ABR=remaining,
        lease_scope_match='exact',lease_scope_evidence='Both cells: June current ABR, HPP ownership share; Glu Mobile expires 2027 at disposed 875 Howard.',
        remaining_lease_roll_is_complete=False,
        tender_completed_principal_reduction=0,
        tender_full_acceptance_cash_scenario=(tender['principal_2027_target']*tender['price_2027_per_100']+tender['principal_2028_target']*tender['price_2028_per_100'])/100,
        tender_scenario_note='Conditional $197.125m purchase cash, before accrued interest/fees; may use revolver, so not an automatic $200m net-debt reduction.',
        sources=[sources[k] for k in ['hpp_2026q2_supplement',h['key'],a['sale']['key'],tender['key']]],
        transform_code_version=code,metric_definition_version='HPP-known-event-bridge@1'))
    return f

if __name__=='__main__':
    from research_contract import code_manifest
    run(code_manifest('core_'))
