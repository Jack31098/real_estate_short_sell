"""Minimum normalized refinancing proceeds; no claim of loan-level loss."""
import itertools
import json
import pandas as pd
from research_sources import ROOT,OUT,write_json

def debt_constant(rate,years):
    if years==0:return rate
    if rate==0:return 1/years
    m=rate/12
    return 12*m/(1-(1+m)**(-12*years))

def calculate(principal,ltv,cap0,noi_change,cap_bps,rate,max_ltv,min_dscr,years):
    noi0=principal/ltv*cap0
    noi=noi0*(1+noi_change);cap=cap0+cap_bps/10000
    value=noi/cap
    ltv_capacity=max_ltv*value
    dscr_capacity=noi/(min_dscr*debt_constant(rate,years))
    capacity=min(ltv_capacity,dscr_capacity)
    return dict(noi0=noi0,noi_stressed=noi,collateral_value=value,ltv_capacity=ltv_capacity,
        dscr_capacity=dscr_capacity,max_new_principal=capacity,
        equity_gap=max(0,principal-capacity),binding_constraint='LTV' if ltv_capacity<=dscr_capacity else 'DSCR',
        price_change_pct=(value/(principal/ltv)-1)*100,
        max_noi_decline_without_gap_pct=(1-max(ltv*cap/(max_ltv*cap0),
            principal*min_dscr*debt_constant(rate,years)/noi0))*100)

def run(code):
    a=json.loads((ROOT/'config/colb_refi_assumptions.json').read_text())
    hist=json.loads((OUT/'core_history_observations.json').read_text())
    refs=[r for r in hist if r['entity_id']=='COLB' and r['period_end']=='2026-06-30' and r['metric'] in ['office_ltv_pct','office_nonowner_dscr']]
    assert {r['metric']:r['value'] for r in refs}=={'office_ltv_pct':57.0,'office_nonowner_dscr':1.76}
    rows=[]
    for cap0,noi,capbps,rate,maxltv,years in itertools.product(a['baseline_cap_rates'],a['noi_changes'],a['cap_rate_changes_bps'],a['refinance_rates'],a['maximum_ltv'],a['amortization_years']):
        rows.append(dict(baseline_cap_rate=cap0,noi_change=noi,cap_change_bps=capbps,refinance_rate=rate,
            maximum_ltv=maxltv,minimum_dscr=a['minimum_dscr'],amortization_years=years,
            **calculate(a['principal'],a['ltv_anchor'],cap0,noi,capbps,rate,maxltv,a['minimum_dscr'],years),
            status='scenario',unit='USD_per_100_existing_principal',scope_match=a['scope_match'],
            assumption_set_id=a['assumption_set_id'],metric_definition_version='refi-gap@1',transform_code_version=code,
            input_observation_ids=';'.join(r['observation_id'] for r in refs)))
    f=pd.DataFrame(rows);f.to_csv(OUT/'colb_refi_grid.csv',index=False)
    write_json(OUT/'colb_refi_run.json',dict(assumptions=a,reference_observations=refs,
        grid_cells=len(f),transform_code_version=code,not_loss_estimate=True,
        actual_2027_cohort_gap=None,reason='Missing joint distribution of 2027 office loan LTV, NOI, debt service and borrower resources'))
    return f

if __name__=='__main__':
    from research_contract import code_manifest
    run(code_manifest('core_'))
