#!/usr/bin/env python3
"""Daily market replay with explicit windows and strictly pre-event factor fits."""
from __future__ import annotations

import argparse
import io
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from research_sources import ROOT, OUT, download, write_json

SYMBOLS = ['WAFD', 'COLB', 'HPP', 'KRC', 'KRE', 'SPY']


def parse_chart(payload, ticker, end):
    chart = payload['chart']['result'][0]
    stamps = chart['timestamp']
    quote = chart['indicators']['quote'][0]
    adjusted = chart['indicators'].get('adjclose', [{}])[0].get('adjclose')
    if adjusted is None or len(adjusted) != len(stamps):
        raise ValueError('Adjusted close absent or misaligned')
    dates = pd.to_datetime(stamps, unit='s', utc=True).tz_convert('America/New_York').strftime('%Y-%m-%d')
    frame = pd.DataFrame({'ticker':ticker, 'date':dates, 'close':quote['close'],
                          'adjusted_close':adjusted, 'volume':quote['volume']})
    frame = frame.loc[frame.date <= end].copy()
    if frame.date.duplicated().any():
        raise ValueError('Duplicate market session')
    frame['dividend'] = 0.0
    actions = []
    for typ, events in chart.get('events', {}).items():
        for ev in events.values():
            date = datetime.fromtimestamp(ev['date'], timezone.utc).astimezone(__import__('zoneinfo').ZoneInfo('America/New_York')).date().isoformat()
            if date > end:
                continue
            actions.append({'ticker':ticker,'date':date,'type':typ,**ev,'event_timestamp':ev['date']})
            actions[-1]['date'] = date
            if typ == 'dividends':
                frame.loc[frame.date == date, 'dividend'] += ev['amount']
    frame['price_return'] = frame.close.pct_change(fill_method=None)
    frame['total_return'] = frame.adjusted_close.pct_change(fill_method=None)
    frame['cash_dividend_return_check'] = (frame.close + frame.dividend) / frame.close.shift() - 1
    return frame, actions


def window_return(frame, start, end):
    """Exact session endpoints only; no hidden nearest-date substitution."""
    z = frame.set_index('date')
    if start not in z.index or end not in z.index:
        raise ValueError(f'Missing endpoint {start} or {end}')
    a, b = z.loc[start], z.loc[end]
    return {'start':start, 'end':end, 'start_close':float(a.close), 'end_close':float(b.close),
            'price_return_pct':float((b.close / a.close - 1) * 100),
            'total_return_pct':float((b.adjusted_close / a.adjusted_close - 1) * 100)}


def factor_fit(data, ticker, event_date, end, window=252):
    factors = ['KRE','SPY','d2y','d10y']
    complete = data[[ticker,*factors]].dropna()
    train = complete.loc[complete.index < event_date].tail(window)
    test = complete.loc[(complete.index >= event_date) & (complete.index <= end)]
    expected = data.loc[(data.index >= event_date)&(data.index <= end)]
    if len(test)!=len(expected):
        raise ValueError('Missing event-window target or factor; do not silently drop event sessions')
    if len(train) != window or len(test) == 0:
        raise ValueError(f'Insufficient pre-event observations: {len(train)}/{window}')
    x = np.column_stack([np.ones(len(train)), train[factors]])
    y = train[ticker].to_numpy()
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise ValueError('Rank-deficient factor design')
    beta = np.linalg.lstsq(x,y,rcond=None)[0]
    resid = y-x@beta
    sigma2 = float(resid@resid/(len(y)-x.shape[1]))
    xt = np.column_stack([np.ones(len(test)), test[factors]])
    prediction = xt@beta
    residual = test[ticker].to_numpy()-prediction
    # Descriptive iid interval; autocorrelation/event heteroskedasticity remain limitations.
    xs = xt.sum(axis=0)
    se = np.sqrt(sigma2*(len(test)+xs@np.linalg.inv(x.T@x)@xs))
    return {'ticker':ticker,'training_sessions':window,'training_start':train.index[0],
            'training_end':train.index[-1], 'event_start':test.index[0], 'event_end':test.index[-1],
            'event_sessions':len(test),'coefficients':dict(zip(['intercept',*factors],beta.tolist())),
            'sum_daily_residual_pct':float(residual.sum()*100),
            'iid_95_half_width_pct':float(1.96*se*100),
            'actual_total_return_pct':float((np.prod(1+test[ticker])-1)*100),
            'model_cumulative_return_pct':float((np.prod(1+prediction)-1)*100),
            'inference':'descriptive; iid prediction interval; not causal attribution',
            'condition_number':float(np.linalg.cond(x))}


def run(end='2026-10-06', refresh=False):
    frames, actions, sources, failures = [], [], [], []
    start_stamp = int(datetime(2024,1,1,tzinfo=timezone.utc).timestamp())
    stop_stamp = int((pd.Timestamp(end,tz='UTC')+pd.Timedelta(days=1)).timestamp())
    for ticker in SYMBOLS:
        url = f'https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?period1={start_stamp}&period2={stop_stamp}&interval=1d&events=div%2Csplits'
        try:
            meta = download(url,refresh)
            frame, acts = parse_chart(json.loads((ROOT/meta['raw_path']).read_bytes()),ticker,end)
            frame['source_sha256'] = meta['sha256']
            frame['retrieved_at'] = meta['retrieved_at']
            frames.append(frame); actions += acts; sources.append({'ticker':ticker,**meta})
            print(f'{ticker}: {len(frame)} complete session rows',flush=True)
        except Exception as e:
            failures.append({'ticker':ticker,'error':str(e)})
    OUT.mkdir(parents=True, exist_ok=True)
    write_json(OUT/'market_sources.json',sources)
    write_json(OUT/'corporate_actions.json',actions)
    write_json(OUT/'market_download_errors.json',failures)
    if len(frames) != len(SYMBOLS):
        raise RuntimeError('Market series incomplete; see market_download_errors.json')
    daily = pd.concat(frames,ignore_index=True)
    daily.to_csv(OUT/'market_daily.csv',index=False)
    summaries = []
    for ticker in SYMBOLS:
        f = daily.loc[daily.ticker==ticker]
        for label,a,b in [('september_month','2026-08-31','2026-09-30'),
                          ('merger_first_session','2026-09-04','2026-09-08'),
                          ('announcement_to_month_end','2026-09-04','2026-09-30'),
                          ('month_end_to_latest','2026-09-30',end)]:
            summaries.append({'ticker':ticker,'window':label,**window_return(f,a,b)})
        pre = f.loc[(f.date>='2026-08-01') & (f.date<='2026-09-30')].set_index('date')
        dd = pre.close/pre.close.cummax()-1
        trough = dd.idxmin(); peak = pre.loc[:trough,'close'].idxmax()
        summaries.append({'ticker':ticker,'window':'aug_sep_max_close_drawdown',
                          **window_return(f,peak,trough)})
    summary = pd.DataFrame(summaries)
    # A benchmark difference, explicitly not the fitted event residual.
    for label in summary.window.unique():
        kre = summary.loc[(summary.ticker=='KRE')&(summary.window==label),'total_return_pct']
        if label != 'aug_sep_max_close_drawdown':
            mask = (summary.window==label)&summary.ticker.isin(['WAFD','COLB'])
            summary.loc[mask,'excess_vs_KRE_pp'] = summary.loc[mask,'total_return_pct']-float(kre.iloc[0])
    summary.to_csv(OUT/'market_window_returns.csv',index=False)
    series = daily.pivot(index='date',columns='ticker',values='total_return')
    yields = []
    for year in range(2024,int(end[:4])+1):
        url = f'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{year}/all?_format=csv&field_tdr_date_value={year}&page=&type=daily_treasury_yield_curve'
        meta = download(url,refresh)
        z = pd.read_csv(ROOT/meta['raw_path'])[['Date','2 Yr','10 Yr']]
        z.columns = ['date','DGS2','DGS10']
        z.date = pd.to_datetime(z.date).dt.strftime('%Y-%m-%d')
        yields.append(z.loc[z.date<=end].set_index('date'))
        sources.append({'series':'Treasury par yield curve 2Y/10Y','year':year,**meta})
    rates = pd.concat(yields).sort_index()
    if rates.index.duplicated().any():
        raise ValueError('Duplicate Treasury date')
    rates.to_csv(OUT/'treasury_daily.csv')
    # Changes across consecutive equity sessions. Do not forward-fill future values.
    rate_aligned = rates.reindex(series.index).ffill()
    series['d2y'] = rate_aligned.DGS2.diff()
    series['d10y'] = rate_aligned.DGS10.diff()
    results = []
    for ticker in ['WAFD','COLB']:
        for n in [252,126]:
            for stop in ['2026-09-08','2026-09-10','2026-09-30']:
                results.append(factor_fit(series,ticker,'2026-09-08',stop,n))
    write_json(OUT/'event_factor_results.json',results)
    checks=[]
    for ticker in ['WAFD','COLB']:
        meta=download(f'https://stockanalysis.com/stocks/{ticker.lower()}/history/',refresh)
        tables=pd.read_html(io.StringIO((ROOT/meta['raw_path']).read_text(encoding='utf-8')))
        other=next(t for t in tables if 'Date' in t and 'Close' in t)
        other['date']=pd.to_datetime(other.Date,format='mixed').dt.strftime('%Y-%m-%d')
        for date in ['2026-08-31','2026-09-04','2026-09-08','2026-09-30',end]:
            close=float(daily.loc[(daily.ticker==ticker)&(daily.date==date),'close'].iloc[0])
            match=other.loc[other.date==date,'Close']
            independent=None if match.empty else float(match.iloc[0])
            checks.append({'ticker':ticker,'date':date,'yahoo_close':close,'independent_close':independent,
                           'match_to_cent':None if independent is None else abs(close-independent)<0.005,
                           'source_sha256':meta['sha256']})
        sources.append({'series':ticker+' independent historical close','vendor':'StockAnalysis / S&P Global',**meta})
    write_json(OUT/'market_endpoint_checks.json',checks)
    if any(x['match_to_cent'] is False for x in checks):
        raise ValueError('Independent close endpoint mismatch')
    write_json(OUT/'market_sources.json',sources)
    differences = (daily.total_return-daily.cash_dividend_return_check).abs()
    dividend_checks=daily.loc[differences>0.0001,['ticker','date','dividend','total_return','cash_dividend_return_check']].copy()
    dividend_checks['difference_pp']=(daily.total_return-daily.cash_dividend_return_check)*100
    dividend_checks.to_csv(OUT/'dividend_return_convention_differences.csv',index=False)
    write_json(OUT/'market_validation.json',{
        'end_date':end,'intraday_excluded':True,'return_convention':'Yahoo adjusted close: split and dividend adjusted; reconstructed vintage',
        'maximum_daily_adjusted_vs_cash_dividend_difference':float(differences.max()),
        'dividend_convention_note':'Vendor adjusted-close factors and adding a cash dividend at closing price have different reinvestment conventions; differences retained, not forced to zero. No second split adjustment applied.',
        'independent_endpoint_check':checks,
        'rate_forward_filled_sessions':series.index[rates.reindex(series.index).DGS2.isna()].tolist(),
        'not_point_in_time_archive':True,'factors':['KRE total return','SPY total return','2Y yield change percentage points','10Y yield change percentage points'],
        'sources_snapshot_retrieved_now':True})
    print(summary.loc[summary.ticker.isin(['WAFD','COLB'])].to_string(index=False))


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--end',default='2026-10-06');p.add_argument('--refresh',action='store_true')
    args=p.parse_args();run(args.end,args.refresh)
