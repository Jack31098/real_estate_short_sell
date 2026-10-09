"""Compare HPP common and Series C short scenarios; no inferred fair NAV.

All returns use equal initial short notional, not broker margin capital. Terminal
yield prices assume uninterrupted perpetual dividends, no call and no arrears.
Liquidation allocation is a separate conditional issuer pool after every senior
claim. It must not be mistaken for an observed current asset valuation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def finite(*values):
    if any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError('Finite numeric inputs required')

def yield_price(annual_dividend, required_yield):
    finite(annual_dividend, required_yield)
    if annual_dividend < 0 or required_yield <= 0:
        raise ValueError('Dividend must be nonnegative and yield positive')
    return annual_dividend / required_yield

def short_return(entry, exit_price, years, annual_dividend=0, borrow_rate=0,
                 paid_fraction=1, roundtrip_cost=0):
    finite(entry, exit_price, years, annual_dividend, borrow_rate, paid_fraction, roundtrip_cost)
    if entry <= 0 or min(exit_price, years, annual_dividend, borrow_rate, roundtrip_cost) < 0 or not 0 <= paid_fraction <= 1:
        raise ValueError('Invalid short inputs')
    gross = 1 - exit_price / entry
    dividend_cost = annual_dividend * years * paid_fraction / entry
    borrow_cost = borrow_rate * years
    return dict(gross_price_return=gross, cash_dividend_cost=dividend_cost,
                borrow_cost=borrow_cost, roundtrip_cost=roundtrip_cost,
                net_return=gross-dividend_cost-borrow_cost-roundtrip_cost)

def required_preferred_exit(preferred_entry, dividend, years, preferred_borrow, common_net_return,
                            roundtrip_cost=0):
    finite(preferred_entry, dividend, years, preferred_borrow, common_net_return, roundtrip_cost)
    if preferred_entry <= 0 or min(dividend, years, preferred_borrow, roundtrip_cost) < 0:
        raise ValueError('Invalid comparison inputs')
    exit_price = preferred_entry * (1-common_net_return-preferred_borrow*years-roundtrip_cost) - dividend*years
    return exit_price if exit_price > 0 else None

def liquidation_pool(available_pool_m, preferred_shares_m, par=25, arrears_per_share=0, parity_claims_m=0):
    finite(available_pool_m, preferred_shares_m, par, arrears_per_share, parity_claims_m)
    if available_pool_m < 0 or preferred_shares_m <= 0 or par <= 0 or min(arrears_per_share, parity_claims_m) < 0:
        raise ValueError('Invalid liquidation pool')
    c_claim = preferred_shares_m*(par+arrears_per_share)
    total_claim = c_claim+parity_claims_m
    available = min(available_pool_m, total_claim)
    c_allocation = available*c_claim/total_claim
    return dict(preferred_recovery_per_share=c_allocation/preferred_shares_m,
                common_residual_m=max(0, available_pool_m-total_claim),
                total_preferred_claim_m=total_claim)

def tender_effect(principal, purchase_cash, revolver_fraction, status):
    finite(principal, purchase_cash, revolver_fraction)
    if min(principal, purchase_cash) < 0 or not 0 <= revolver_fraction <= 1:
        raise ValueError('Invalid tender funding')
    if status != 'settled':
        return dict(observed_gross_debt_change_m=0.0, observed_net_debt_change_m=0.0)
    # Purchase consumes cash or creates new debt; both increase net debt by
    # purchase_cash before extinguishment. No assumed $200m net reduction.
    return dict(observed_gross_debt_change_m=-principal+purchase_cash*revolver_fraction,
                observed_net_debt_change_m=-principal+purchase_cash)

def validate_config(cfg):
    if cfg['price_date'] > cfg['research_date']:
        raise ValueError('Price date is after research cutoff')
    p=cfg['prices']; pref=cfg['preferred']; finite(p['common'],p['preferred'])
    if min(p['common'],p['preferred']) <= 0:
        raise ValueError('Positive entry prices required')
    if pref['annual_dividend'] != pref['quarterly_dividend']*4:
        raise ValueError('Dividend terms inconsistent')
    if cfg['known_event_bridge']['tender_status'] != 'settled' and cfg['known_event_bridge']['observed_completed_principal_reduction'] != 0:
        raise ValueError('Announced tender cannot reduce observed debt')

def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8-sig') as handle:
        writer=csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)

def calculate(cfg):
    validate_config(cfg)
    c,p=cfg['prices']['common'],cfg['prices']['preferred']
    d=cfg['preferred']['annual_dividend']; a=cfg['scenario_assumptions']
    cost=a['roundtrip_cost_fraction'];central_paid=a['cash_dividend_paid_fraction']
    yp=[]; full=[]; thresholds=[]
    for y in a['preferred_required_yields']:
        exit_price=yield_price(d,y)
        sr=short_return(p,exit_price,1,d,a['central_preferred_borrow'],central_paid,cost)
        yp.append(dict(required_yield=y, exit_price=exit_price, **sr, status='scenario',assumption_set_id=cfg['assumption_set_id']))
    for years in a['horizons_years']:
        for f in a['preferred_borrow_rates']:
            for r in yp:
                for paid in [0,0.5,1]:
                    full.append(dict(security='preferred',horizon_years=years,entry_price=p,exit_price=r['exit_price'],required_yield=r['required_yield'] if paid==1 else None,borrow_rate=f,cash_dividend_paid_fraction=paid,unpaid_cumulative_dividend_per_share=d*years*(1-paid),terminal_pricing_assumption='Uninterrupted no-call perpetuity' if paid==1 else 'Exogenous terminal quote including unresolved arrears value; D/y is NOT an arrears valuation',**short_return(p,r['exit_price'],years,d,f,paid,cost),status='scenario',assumption_set_id=cfg['assumption_set_id']))
        for f in a['common_borrow_rates']:
            for exit_price in a['common_exit_prices']:
                full.append(dict(security='common',horizon_years=years,entry_price=c,exit_price=exit_price,required_yield=None,borrow_rate=f,cash_dividend_paid_fraction=1,unpaid_cumulative_dividend_per_share=0,terminal_pricing_assumption='Exogenous terminal common quote',**short_return(c,exit_price,years,cfg['common']['annual_dividend_assumption'],f,1,cost),status='scenario',assumption_set_id=cfg['assumption_set_id']))
                px=required_preferred_exit(p,d*central_paid,years,a['central_preferred_borrow'],short_return(c,exit_price,years,cfg['common']['annual_dividend_assumption'],f,1,cost)['net_return'],cost)
                thresholds.append(dict(horizon_years=years,common_exit_price=exit_price,common_borrow_rate=f,preferred_borrow_rate=a['central_preferred_borrow'],preferred_exit_to_match=px,preferred_yield_to_match=d/px if px else None,match_possible=px is not None,status='scenario'))
    central_common=short_return(c,a['central_common_exit'],1,cfg['common']['annual_dividend_assumption'],a['central_common_borrow'],1,cost)
    px=required_preferred_exit(p,d*central_paid,1,a['central_preferred_borrow'],central_common['net_return'],cost)
    pool=[]
    for value in [0,85,170,245.82,340,425,600,1000]:
        result=liquidation_pool(value,cfg['preferred']['june_shares_million'])
        pool.append(dict(available_after_all_senior_claims_m=value,**result,status='conditional allocation; not estimated NAV'))
    return dict(preferred_yield_scenarios=yp,short_scenarios=full,comparison_thresholds=thresholds,liquidation_pool_scenarios=pool,
        headline=dict(price_date=cfg['price_date'],preferred_current_yield=d/p,
            preferred_discount_to_par=1-p/cfg['preferred']['liquidation_preference'],call_short_gross_return=1-cfg['preferred']['liquidation_preference']/p,
            common_target=a['central_common_exit'],common_one_year_net=central_common['net_return'],
            preferred_exit_to_match_common=px,preferred_yield_to_match_common=d/px if px and central_paid==1 else None,
            preferred_one_year_breakeven_exit=p-d*central_paid-p*(a['central_preferred_borrow']+cost),
            preferred_one_year_max_gain_with_full_dividends=1-d/p-a['central_preferred_borrow']-cost,
            common_one_year_max_gain=1-cfg['common']['annual_dividend_assumption']/c-a['central_common_borrow']-cost),
        facts=cfg, limitations=cfg['unresolved'])

def run(config_path, out):
    cfg=json.loads(config_path.read_text(encoding='utf-8'))
    results=calculate(cfg)
    out.mkdir(parents=True,exist_ok=True)
    for key in ['preferred_yield_scenarios','short_scenarios','comparison_thresholds','liquidation_pool_scenarios']:
        write_csv(out/(key+'.csv'),results[key])
    (out/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        git_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError,FileNotFoundError):
        git_base=None
    manifest=dict(executed_at=datetime.now(timezone.utc).isoformat(),model_version='HPP-security-comparison@1',git_base=git_base,
                  config_sha256=hashlib.sha256(config_path.read_bytes()).hexdigest(),
                  model_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  input_price_date=cfg['price_date'],research_date=cfg['research_date'],
                  scenario_count=len(results['short_scenarios']),expected_return_computed=False,
                  absolute_nav_computed=False,broker_executable_comparison=False)
    (out/'run_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(results['headline'],indent=2)); print('Scenario rows:',len(results['short_scenarios']))
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=ROOT/'config/hpp_security_inputs.json')
    parser.add_argument('--output',type=Path,default=ROOT/'outputs/v2/hpp_security_comparison')
    args=parser.parse_args();run(args.config,args.output)
