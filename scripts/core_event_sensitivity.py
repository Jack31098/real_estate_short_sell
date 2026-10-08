"""Descriptive event sensitivity, using exactly the previously audited sessions."""
import pandas as pd
from research_sources import OUT,write_json
from market_replay import factor_fit

def run(code):
    daily=pd.read_csv(OUT/'market_daily.csv')
    series=daily.pivot(index='date',columns='ticker',values='total_return')
    rates=pd.read_csv(OUT/'treasury_daily.csv',index_col='date').reindex(series.index).ffill()
    series['d2y']=rates.DGS2.diff();series['d10y']=rates.DGS10.diff()
    rows=[]
    for ticker in ['WAFD','COLB']:
        for window in [252,126]:
            for end in ['2026-09-08','2026-09-10','2026-09-30']:
                for spec,factors in [('KRE_only',['KRE']),('KRE_rates',['KRE','d2y','d10y']),('legacy_KRE_SPY_rates',['KRE','SPY','d2y','d10y'])]:
                    rows.append(dict(specification=spec,**factor_fit(series,ticker,'2026-09-08',end,window,factors),
                        transform_code_version=code,metric_definition_version='event-OLS@2',
                        assumption_set_id='pre-event-OLS-iid@1'))
    write_json(OUT/'event_specification_sensitivity.json',rows)
    f=pd.DataFrame(rows)
    group=['ticker','training_sessions','event_start','event_end']
    ranges=f.groupby(group).sum_daily_residual_pct.agg(['min','max']).reset_index()
    ranges['matched_peer_specification']='not computed: no matched ex-target peer basket yet'
    ranges['range_scope']='three available specifications, not all requested specifications'
    ranges.to_csv(OUT/'event_residual_ranges.csv',index=False)
    return f
