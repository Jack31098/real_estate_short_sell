#!/usr/bin/env python3
"""Build reviewed, dated V2 panels and report from immutable source revisions.

This is the first execution slice, not a completed causal AI model. Cell entry is
human-reviewed. Downloads, hashes, arithmetic, as-of filtering and reports run in
code. It intentionally emits nulls where evidence has not been reviewed.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import datetime, timezone

import pandas as pd

from research_sources import ROOT, OUT, digest, write_json
from research_contract import available_date, as_of, scope, validate_observation, code_manifest, exact_arithmetic
from reviewed_v2_facts import facts, PERIODS


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def fiscal_label(entity,period):
    year,month=int(period[:4]),int(period[5:7])
    if entity=='WAFD':
        return f'FY{year+int(month>9)}Q{(month//3)%4+1}'
    return f'CY{year}Q{month//3}'


def write_table(name,rows):
    flat=[{k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(dict,list)) else v for k,v in r.items()} for r in rows]
    pd.DataFrame(flat).to_csv(OUT/name,index=False)


def build_observations(version):
    manifest=read_json(OUT/'source_manifest.json')
    sources={s['source_id']:s for s in manifest}
    locks=read_json(ROOT/'config/v2_review_locks.json')
    selected={k:sources[v['source_id']] for k,v in locks.items()}
    pages={}
    for key,s in selected.items():
        if s['sha256']!=locks[key]['sha256'] or digest((ROOT/s['raw_path']).read_bytes())!=s['sha256']:
            raise ValueError('Reviewed source changed: '+key)
        if s.get('text_path'):
            text=(ROOT/s['text_path']).read_text(encoding='utf-8')
            pages[key]={int(n):t for n,t in re.findall(r'=== PDF PAGE (\d+) ===\n(.*?)(?==== PDF PAGE |\Z)',text,re.S)}
    rows=[]; definitions={}
    def define(metric,unit):
        dv=metric+'.v1'
        if dv in definitions and definitions[dv]['unit']!=unit:
            raise ValueError('Definition unit collision')
        definitions[dv]={'metric':metric,'unit':unit,'definition':'Source table label with mandatory denominator/scope/notes on each observation; amounts normalized without imputing missing values.'}
        return dv
    for f in facts():
        s=selected[f['source_key']]; page=pages[f['source_key']][f['page']]
        numbers=[float(n.replace(',','')) for n in re.findall(r'(?<![\w.])[+-]?\d[\d,]*(?:\.\d+)?',page)]
        visual=f['source_key']=='colb_2026q2_deck' and f['metric'] in {'office_geography_pct','office_contractual_maturity_2027_pct','office_repricing_2027_pct'}
        visual=visual or (f['source_key']=='hpp_2026q2_supplement' and f['metric'] in {'secured_maturity_2026','secured_maturity_2027','unsecured_maturity_2027'})
        if not visual and not any(abs(abs(n)-abs(f['raw_value']))<1e-8 for n in numbers):
            raise ValueError(f"Reviewed token absent from source page: {f}")
        entity=s['ticker']; period=f['period_end']
        sc=scope(entity,period,f['portfolio'],f['measurement'],f['basis'],geography=f['geography'],ownership=f['ownership'])
        row=dict(observation_id='obs_'+digest(json.dumps([s['source_id'],f],sort_keys=True).encode())[:24],
            entity_id=entity,entity_scope='reported consolidated issuer' if entity!='OFFICE_MARKET' else f['geography'],
            period_end=period,fiscal_label=fiscal_label(entity,period),published_at=s['published_at'],
            available_at=available_date(s['published_at']),retrieved_at=s['retrieved_at'],source_id=s['source_id'],
            source_sha256=s['sha256'],source_url=s['url'],page_or_table=f"PDF page {f['page']}",
            metric=f['metric'],value=f['value'],unit=f['unit'],denominator=f['denominator'],
            portfolio_scope=f['portfolio'],geography=f['geography'],status='observed',missing_reason=None,
            metric_definition_version=define(f['metric'],f['unit']),assumption_set_id=None,
            transform_code_version=version,scope=sc,notes=f['notes'],
            review_method='human visual chart review' if visual else 'human table review; numeric token presence check',
            raw_value=f['raw_value'],normalization_multiplier=f['scale'],input_observation_ids=[],
            source_page_text_sha256=digest(page.encode()),vintage_status='reconstructed from currently retrieved published document; not an archived contemporaneous download')
        rows.append(row)
    # One filing-table cell anchors the deliberately blocked cross-document calculation.
    from lxml import html
    s=selected['colb_2026q2_10q']
    tree=html.fromstring((ROOT/s['raw_path']).read_bytes())
    matches=[' '.join(t.text_content().split()) for t in tree.xpath('//tr')
             if ' '.join(t.text_content().split()).startswith('Office3,559')]
    if len(matches)!=1:
        raise ValueError('Reviewed COLB 10-Q office table row changed')
    base=next(r for r in rows if r['entity_id']=='COLB' and r['metric']=='loans_net' and r['period_end']=='2026-06-30')
    office={**base,'observation_id':'obs_'+digest((s['source_id']+'office_10q_3559.v1').encode())[:24],
        'source_id':s['source_id'],'source_sha256':s['sha256'],'source_url':s['url'],
        'published_at':s['published_at'],'available_at':available_date(s['published_at']),
        'retrieved_at':s['retrieved_at'],'page_or_table':'10-Q CRE by property type, Office row / June 30 Outstanding',
        'metric':'office_balance_10q','metric_definition_version':define('office_balance_10q','USD_million'),
        'value':3559,'raw_value':3559,'normalization_multiplier':1,'portfolio_scope':'office 10-Q',
        'scope':scope('COLB','2026-06-30','office 10-Q',basis='10-Q loan carrying basis'),
        'source_page_text_sha256':digest(matches[0].encode()),'reviewed_table_row':matches[0],
        'notes':'10-Q Outstanding column; $30m nonaccrual adjacent. Deck denominator not reconciled.',
        'review_method':'human HTML table review; exact row check'}
    rows.append(office)
    # Derived PPNR includes REO gains/losses in pretax earnings, avoiding their accidental omission.
    for entity in ['WAFD','COLB']:
        for period in PERIODS:
            group={r['metric']:r for r in rows if r['entity_id']==entity and r['period_end']==period and r['geography']=='all'}
            a,b=group['pretax_income'],group['provision_total']
            if a['scope']!=b['scope'] or a['unit']!=b['unit']:
                raise ValueError('PPNR scope mismatch')
            r={**a,'observation_id':'obs_'+digest((a['observation_id']+b['observation_id']+'ppnr.v1').encode())[:24],
                'metric':'ppnr_gaap_basis','metric_definition_version':define('ppnr_gaap_basis','USD_million'),
                'status':'derived','value':a['value']+b['value'],'input_observation_ids':[a['observation_id'],b['observation_id']],
                'notes':'Pretax income + total provision. Not issuer adjusted/operating PPNR.',
                'raw_value':None,'normalization_multiplier':None}
            rows.append(r)
            if entity=='COLB':
                a,b=group['cash_due_from_banks'],group['interest_bearing_cash']
                if a['scope']!=b['scope'] or a['unit']!=b['unit']:
                    raise ValueError('Cash component scope mismatch')
                rows.append({**a,'observation_id':'obs_'+digest((a['observation_id']+b['observation_id']+'cash.v1').encode())[:24],
                    'metric':'cash','metric_definition_version':define('cash','USD_million'),'status':'derived',
                    'value':a['value']+b['value'],'input_observation_ids':[a['observation_id'],b['observation_id']],
                    'notes':'Cash/due from banks + interest-bearing cash/temporary investments. Not liquidity facilities.',
                    'raw_value':None,'normalization_multiplier':None})
    # Coverage placeholders explicitly distinguish unreviewed from disclosed zero.
    missing={
        'WAFD':{'brokered_deposits':'Not yet extracted/reviewed; not zero.',
            'uninsured_deposits':'Only uninsured AND uncollateralized intersection reviewed.',
            'fhlb_borrowings':'Deck debt percentage is rounded; exact dollar balance not reconciled.',
            'wholesale_funding':'No harmonized scope including all components yet.',
            'deposit_beta':'Matched policy-rate regime and quarterly deposit-cost series not yet reviewed.',
            'loan_beta':'Contractual floors/reset lags not yet extracted.',
            'loan_floor_share':'Not yet reviewed.', 'refi_wall_2027':'Maturity OR repricing table cannot identify contractual 2027 maturity.'},
        'COLB':{'fhlb_borrowings':'Facility utilization is not a verified borrowing balance.',
            'wholesale_funding':'Borrowings, repo, junior and brokered deposits retained separately pending common definition.',
            'deposit_beta':'Matched policy-rate regime not yet reviewed; Treasury yields are not the policy rate.',
            'loan_beta':'Loan yield change is not contractual loan beta.', 'loan_floor_share':'Not yet reviewed.',
            'criticized_to_net_loans':'Bank-wide criticized series not yet reconciled; office classifications are separate.',
            'refi_wall_2027':'Office maturity percentage available; denominator dollars not reconciled.'},
        'OFFICE_MARKET':{'direct_vacancy':'Report provides total vacancy and direct availability, not direct vacancy.',
            'effective_rent':'Market survey not yet ingested; owner rent is a different sample.',
            'free_rent':'No market concession series reviewed.', 'ti_allowance':'Owner TI/LC is not market allowance.',
            'lease_term':'Owner lease terms do not represent the market.'}}
    coverage=[]
    for entity,items in missing.items():
        for metric,reason in items.items():
            coverage.append({'entity_id':entity,'metric':metric,'value':None,'missing_reason':reason,'status':'unreviewed'})
    for row in rows:
        validate_observation(row,definitions,sources)
    ids=[r['observation_id'] for r in rows]
    if len(ids)!=len(set(ids)):
        raise ValueError('Duplicate observation identity')
    # Append immutable source revisions. Code-only reruns retain a stable economic observation id.
    path=OUT/'reviewed_observations.json'
    previous=read_json(path) if path.exists() else []
    combined={r['observation_id']:r for r in previous}
    combined.update({r['observation_id']:r for r in rows})
    write_json(path,list(combined.values()))
    definition_path=OUT/'metric_definitions.json'
    old_definitions=read_json(definition_path) if definition_path.exists() else {}
    for key,value in definitions.items():
        if key in old_definitions and old_definitions[key]!=value:
            raise ValueError('Metric definition changed without a version bump: '+key)
    write_json(definition_path,{**old_definitions,**definitions})
    write_table('coverage_gaps.csv',coverage)
    return list(combined.values()),coverage


def scope_audit(rows):
    fraction=next(r for r in rows if r['entity_id']=='COLB' and r['metric']=='office_geography_pct' and r['geography']=='Puget Sound')
    balance=next(r for r in rows if r['metric']=='office_balance_10q')
    reason='Deck excludes purchase accounting adjustments/deferred fees; reconciliation to 10-Q $3,559m not completed.'
    try:
        value=exact_arithmetic(fraction,balance,'multiply_fraction','approximate',reason,denominator_scope=fraction['scope'])
    except ValueError as e:
        value=None; rejection=str(e)
    else:
        raise AssertionError('Approximate geography multiplication escaped gate')
    return [{'entity_id':'COLB','period_end':'2026-06-30','numerator_scope':fraction['scope'],
        'denominator_scope':balance['scope'],'scope_match':'approximate','evidence':reason,
        'proposed_operation':'office geography percentages times 10-Q office carrying balance',
        'result_USD_million':value,'gate_result':'blocked','gate_reason':rejection,
        'input_observation_ids':[fraction['observation_id'],balance['observation_id']],
        'source_keys':['colb_2026q2_deck','colb_2026q2_10q']}]


def states(rows,cutoff):
    current=as_of(rows,cutoff); result=[]
    for entity in ['WAFD','COLB']:
        credit=[r for r in current if r['entity_id']==entity and any(k in r['metric'] for k in ['criticized','classified','nonaccrual','nonperforming','past_due','chargeoff'])]
        result.append({'entity_id':entity,'as_of':cutoff,'LiquidityStress':{'value':None,'status':'unknown',
            'reason':'Property transaction/pending/inventory/DOM series not ingested; deposit liquidity is separate.'},
            'CreditStress':{'value':None,'status':'observed_vector_no_composite',
                           'input_observation_ids':[r['observation_id'] for r in credit],
                           'note':'Overlapping classifications are not a Markov chain or summable totals.'},
            'funding_panel':'bank_funding_earnings_quarterly.csv','joint_score':None,
            'lag_correlation':None,'lag_test_status':'insufficient longitudinal property series; not tested'})
    return result


def run():
    version=code_manifest(); rows,gaps=build_observations(version)
    credit_words=['criticized','classified','nonaccrual','nonperforming','past_due','delinquenc','chargeoff','acl','provision']
    bank=[r for r in rows if r['entity_id'] in ['WAFD','COLB']]
    write_table('bank_credit_quarterly.csv',[r for r in bank if any(w in r['metric'] for w in credit_words)])
    write_table('bank_funding_earnings_quarterly.csv',[r for r in bank if not any(w in r['metric'] for w in credit_words)])
    write_table('office_owner_quarterly.csv',[r for r in rows if r['entity_id'] in ['HPP','KRC']])
    write_table('office_market_quarterly.csv',[r for r in rows if r['entity_id']=='OFFICE_MARKET'])
    required={
        'uninsured_deposits':{}, 'nib_deposits':{}, 'deposits':{}, 'brokered_deposits':{},
        'fhlb_borrowings':{}, 'wholesale_funding':{}, 'cash':{},
        'liquidity_capacity':{'COLB':'potential_liquidity'}, 'afs_fair_value':{},'htm_amortized_cost':{},
        'aoci':{},'securities_duration':{'COLB':'afs_duration'}, 'loan_beta':{},'loan_floor_share':{},
        'deposit_beta':{},'nim':{'WAFD':'nim_gaap','COLB':'nim_tax_equivalent'},
        'noninterest_expense':{},'ppnr_gaap_basis':{}, 'nonaccrual_loans':{}, 'net_chargeoffs':{},
        'criticized':{'WAFD':'criticized_to_net_loans'},'classified':{'WAFD':'classified_to_net_loans'},
        'refi_wall_2027':{}}
    coverage=[]
    for entity in ['WAFD','COLB']:
        for period in PERIODS:
            for field,mapping in required.items():
                metric=mapping.get(entity,field)
                found=[r for r in rows if r['entity_id']==entity and r['period_end']==period and r['metric']==metric]
                reason=next((g['missing_reason'] for g in gaps if g['entity_id']==entity and g['metric']==metric),'Not yet extracted/reconciled for this quarter; not zero.')
                coverage.append({'entity_id':entity,'period_end':period,'required_field':field,'reported_metric':metric,
                    'status':'reviewed' if found else 'missing','value':found[0]['value'] if found else None,
                    'unit':found[0]['unit'] if found else None,'missing_reason':None if found else reason,
                    'observation_ids':[r['observation_id'] for r in found]})
    write_table('required_field_coverage.csv',coverage)
    write_json(OUT/'scope_reconciliation.json',scope_audit(rows))
    cutoffs=['2026-09-01T23:59:59+00:00','2026-09-08T23:59:59+00:00','2026-09-30T23:59:59+00:00','2026-10-06T23:59:59+00:00']
    snapshots=[{'as_of':c,'observations':as_of(rows,c),'states':states(rows,c)} for c in cutoffs]
    write_json(OUT/'asof_snapshots.json',snapshots)
    write_json(OUT/'dual_states.json',[s for c in cutoffs for s in states(rows,c)])
    market_hashes={name:digest((OUT/name).read_bytes()) for name in ['market_daily.csv','market_window_returns.csv','event_factor_results.json','treasury_daily.csv']}
    run_id='run_'+digest((version+json.dumps(sorted(r['observation_id'] for r in rows))+json.dumps(market_hashes,sort_keys=True)).encode())[:24]
    import platform
    from importlib.metadata import version as package_version
    write_json(OUT/'run_manifest.json',{'run_id':run_id,'executed_at':datetime.now(timezone.utc).isoformat(),
        'transform_code_version':version,'observations':len(rows),'coverage_gaps':len(gaps),
        'market_input_sha256':market_hashes,'python_version':platform.python_version(),
        'package_versions':{p:package_version(p) for p in ['pandas','numpy','lxml','pypdf','tzdata']},
        'run_type':'first execution slice; manually reviewed facts with automated validation',
        'input_observation_ids':[r['observation_id'] for r in rows],
        'completed':['source hash locks','three-quarter banks','funding equal priority','market replay','owner and market pilot','four historical cutoffs','scope gate'],
        'pending':['2024-onward filing backfill','property LiquidityStress series','matched controls and AI attribution','refi/collateral scenario','complete borrower and tenant exposure mapping']})
    from research_v2_report import write_report
    write_report(rows,cutoffs,version,run_id)
    print(f'Validated {len(rows)} observations; {len(gaps)} explicit gaps. Report: outputs/v2/research_report_zh.md')


if __name__=='__main__':
    run()
