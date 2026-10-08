"""Residential liquidity and collateral vectors, deliberately not an office proxy."""
import json
import pandas as pd
from research_sources import ROOT, OUT, digest, write_json
from core_history import pages,cells

COUNTIES=['King County, WA','Snohomish County, WA','Pierce County, WA',
          'Santa Clara County, CA','San Francisco County, CA','San Mateo County, CA']
FIELDS={
 'pending_sales':('PENDING SALES','count','LiquidityStress'),
 'closed_sales':('HOMES SOLD','count','LiquidityStress'),
 'inventory':('INVENTORY','count','LiquidityStress'),
 'active_listings':('ACTIVE LISTINGS','count','LiquidityStress'),
 'new_listings':('NEW LISTINGS','count','LiquidityStress'),
 'dom':('MEDIAN DAYS ON MARKET (DAYS)','days','LiquidityStress'),
 'months_supply':('MONTHS OF SUPPLY','months','LiquidityStress'),
 'price_cut_share':('PERCENT ACTIVE WITH PRICE DROPS (%)','percent','LiquidityStress'),
 'median_price':('MEDIAN SALE PRICE NSA ($)','USD','CollateralStress'),
 'price_per_sf':('MEDIAN SALE PRICE PER SQ.FT. ($)','USD_per_sqft','CollateralStress'),
 'sale_list_ratio':('AVERAGE SALE TO LIST RATIO (%)','percent','CollateralStress')}

def load(key):return json.loads((OUT/(key+'_source.json')).read_text())

def run(code):
    housing=load('redfin_housing');cuts=load('redfin_price_drops')
    h=pd.read_csv(ROOT/housing['raw_path'],low_memory=False); c=pd.read_csv(ROOT/cuts['raw_path'],low_memory=False)
    h=h[h['REGION NAME'].isin(COUNTIES)].copy();c=c[c['REGION NAME'].isin(COUNTIES)].copy()
    keys=['REGION NAME','PERIOD END']
    z=h.merge(c,on=keys,validate='one_to_one',suffixes=('','_cuts')).sort_values(keys)
    rows=[]
    for _,r in z.iterrows():
        for metric,(col,unit,state) in FIELDS.items():
            meta=cuts if metric=='price_cut_share' else housing
            value=None if pd.isna(r[col]) else float(r[col])
            period=r['PERIOD END'];region=r['REGION NAME']
            oid='property_'+digest(f"{meta['sha256']}|{region}|{period}|{metric}".encode())[:24]
            rows.append(dict(observation_id=oid,geography=region,geography_type='county',period_end=period,
                entity_id=region,entity_scope='residential market',portfolio_scope='residential',metric=metric,value=value,unit=unit,
                state=state,status='observed',source_url=meta['url'],source_sha256=meta['sha256'],
                page_or_table=f'CSV row REGION NAME={region}, PERIOD END={period}; column {col}',
                published_at=r['LAST UPDATED'],available_at=meta['retrieved_at'],retrieved_at=meta['retrieved_at'],
                vintage='current revised download, not original historical vintage',
                seasonal_adjustment='NSA' if metric=='median_price' else 'Vendor monthly series; seasonal adjustment not identified in download column; no additional adjustment',
                metric_definition_version=metric+'@redfin-2026-05',assumption_set_id=None,transform_code_version=code,
                missing_reason='vendor missing' if value is None else None))
    f=pd.DataFrame(rows);f.to_csv(OUT/'property_monthly_long.csv',index=False)
    z.to_csv(OUT/'property_redfin_selected.csv',index=False)
    latest=z.groupby('REGION NAME',sort=False).tail(1).copy()
    cols=['REGION NAME','PERIOD END','PENDING SALES YOY (%)','HOMES SOLD YOY (%)','INVENTORY YOY (%)',
          'MEDIAN DAYS ON MARKET (DAYS)','MONTHS OF SUPPLY','PERCENT ACTIVE WITH PRICE DROPS (%)',
          'MEDIAN SALE PRICE NSA YOY (%)','MEDIAN SALE PRICE PER SQ.FT. YOY (%)','AVERAGE SALE TO LIST RATIO (%)']
    latest[cols].to_csv(OUT/'property_latest.csv',index=False)
    fhfa=load('fhfa_purchase');hpi=pd.read_csv(ROOT/fhfa['raw_path'],sep='\t',na_values=['.'])
    hpi=hpi[hpi.metro_name.str.contains('Seattle|Tacoma|San Jose|San Francisco|Oakland',regex=True)].copy()
    hpi=hpi.sort_values(['cbsa','yr','qtr'])
    hpi['yoy_nsa_pct']=hpi.groupby('cbsa').index_nsa.pct_change(4,fill_method=None)*100
    hpi['qoq_sa_pct']=hpi.groupby('cbsa').index_sa.pct_change(1,fill_method=None)*100
    hpi=hpi[hpi.yr>=2024].copy()
    hpi['period_end']=[pd.Period(year=y,quarter=q,freq='Q').end_time.date().isoformat() for y,q in zip(hpi.yr,hpi.qtr)]
    hpi['source_url']=fhfa['url'];hpi['source_sha256']=fhfa['sha256'];hpi['retrieved_at']=fhfa['retrieved_at']
    hpi['available_at']=fhfa['retrieved_at'];hpi['published_at']=None
    hpi['metric_definition_version']='FHFA-purchase-only-metro@1';hpi['transform_code_version']=code
    hpi['assumption_set_id']=None;hpi['vintage']='current revised; historical publication unavailable'
    hpi.to_csv(OUT/'property_hpi_quarterly.csv',index=False)
    # September NWMLS independently measured, unadjusted; never splice into Redfin.
    nw=load('nwmls_king');nr=[]
    for pg,t in pages(nw).items():
        line=next(l for l in t.splitlines() if l.startswith('All King Co '))
        ns=cells(line);assert len(ns)==15,(pg,ns)
        nr.append(dict(property_type={1:'residential_and_condo',2:'residential',3:'condo'}[pg],
            period_end='2026-09-30',new_listings=ns[0],active_listings=ns[2],active_yoy_pct=ns[4],
            pending=ns[5],pending_yoy_pct=ns[7],closed=ns[8],closed_yoy_pct=ns[10],median_price=ns[11],
            median_price_yoy_pct=ns[13],months_supply=ns[14],source_url=nw['url'],source_sha256=nw['sha256'],
            source_row=line,page=pg,published_at='2026-10-06',available_at='2026-10-07T12:00:00+00:00',
            retrieved_at=nw['retrieved_at'],transform_code_version=code,metric_definition_version='NWMLS-King-monthly@1',
            seasonal_adjustment='NSA',geography='King County, WA'))
    pd.DataFrame(nr).to_csv(OUT/'property_nwmls_september.csv',index=False)
    write_json(OUT/'property_state.json',{
        'LiquidityStress':'raw vector available; no composite or hand-labelled city score',
        'CollateralStress':'residential raw price and repeat-sale vector; office collateral prices not observed here',
        'coverage':COUNTIES,'redfin_months_per_county':z.groupby('REGION NAME').size().to_dict(),
        'historical_PIT_supported':False,'note':'Download vintage is October 7 Pacific. Cannot reconstruct September investor information from these revised property histories.',
        'county_sales_deed_records':'not yet ingested; NWMLS is MLS closed transactions, not the county recorder',
        'transform_code_version':code})
    print(latest[cols].to_string(index=False))
    print(hpi.groupby('metro_name').tail(1)[['metro_name','period_end','yoy_nsa_pct','qoq_sa_pct']].to_string(index=False))
    return f,hpi

if __name__=='__main__':
    from research_contract import code_manifest
    run(code_manifest('core_'))
