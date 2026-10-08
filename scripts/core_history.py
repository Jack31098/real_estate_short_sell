"""Original-quarter credit/funding series, with a locator for every extracted cell.

Only the current-quarter column is read. Historical comparison columns in later
releases are never relabelled as information available at the original date.
"""
import json
import re
import pandas as pd
from research_sources import ROOT, OUT, digest, write_json
from research_contract import available_date, scope, code_manifest

COLB_DATES = ['2024-04-25','2024-07-25','2024-10-24','2025-01-23','2025-04-23',
              '2025-07-24','2025-10-30','2026-01-22','2026-04-23','2026-07-23']

def pages(meta):
    text = (ROOT/meta['text_path']).read_text(encoding='utf-8')
    return {int(p.split(' ===')[0]): '\n'.join(re.sub(r'\s+',' ',s).strip() for s in p.splitlines()[1:])
            for p in text.split('=== PDF PAGE ')[1:]}

def cells(t):
    # Retain signs on parentheses and zero dashes; footnote suffixes are removed
    # by the row expression, not by blindly discarding parenthesized integers.
    return [0.0 if v in ['—','–'] else float(v.replace(',','').replace('(','-').replace(')',''))
            for v in re.findall(r'\(?-?\d[\d,]*(?:\.\d+)?\)?|—|–',t)]

def find_row(pp, pattern, contains=None, min_cells=1):
    for pg,text in pp.items():
        if contains and contains not in text: continue
        ls=text.splitlines()
        for i,line in enumerate(ls):
            m=re.match(pattern,line,re.I)
            if not m: continue
            tail=line[m.end():]
            if not cells(tail) and i+1<len(ls):
                tail+=' '+ls[i+1]
                line+=' '+ls[i+1]
            ns=cells(tail)
            if len(ns)>=min_cells: return pg,line,ns
    raise ValueError(f'Row absent: {pattern} / {contains}')

def run():
    sources=json.loads((OUT/'core_source_manifest.json').read_text(encoding='utf-8'))
    code=code_manifest('core_')
    periods=sorted({s['period_end'] for s in sources if s['ticker']=='COLB'})
    dates=dict(zip(periods,COLB_DATES))
    rows=[]; gaps=[]
    for meta in sources:
        if meta['document_type'] in ['10-Q','10-K']:continue
        pp=pages(meta); ticker=meta['ticker']; period=meta['period_end']
        published=meta.get('published_at',dates.get(period))
        def add(metric,value,unit,pg,evidence,portfolio='all',measurement='stock',note='',status='observed',inputs=None):
            identity=f"{meta['source_id']}|{metric}|{period}|{pg}"
            row={'observation_id':'core_'+digest(identity.encode())[:24], 'entity_id':ticker,
                 'entity_scope':'consolidated','period_end':period,'fiscal_label':period+' calendar quarter',
                 'published_at':published,'available_at':available_date(published),'retrieved_at':meta['retrieved_at'],
                 'source_id':meta['source_id'],'source_sha256':meta['sha256'],'source_url':meta['url'],
                 'page_or_table':f'PDF page {pg}','metric':metric,'value':value,'unit':unit,
                 'denominator':'see metric and source row','portfolio_scope':portfolio,'geography':'all',
                 'status':status,'missing_reason':None,'metric_definition_version':metric+'@core-1',
                 'assumption_set_id':None,'transform_code_version':code,
                 'scope':scope(ticker,period,portfolio=portfolio,measurement=measurement),
                 'source_row':evidence,'notes':note,'input_observation_ids':inputs or [],
                 'comparability_segment':('post_PPBI_2025-08-31' if period>='2025-09-30' else 'pre_PPBI') if ticker=='COLB' else 'post_LBC_2024-02-29'}
            rows.append(row);return row
        def read(metric,pattern,unit='USD_million',contains=None,index=0,scale=None,negate=False,**kwargs):
            try:
                pg,line,ns=find_row(pp,pattern,contains)
                factor=scale if scale is not None else (0.001 if ticker=='WAFD' or '($ in thousands' in pp[pg] else 1)
                v=ns[index]*(factor if unit=='USD_million' else 1)
                return add(metric,-v if negate else v,unit,pg,line,**kwargs)
            except (ValueError,IndexError) as e:
                gaps.append({'ticker':ticker,'period_end':period,'metric':metric,'reason':str(e),'source_id':meta['source_id']})
        if ticker=='WAFD':
            credit=next(p for p,t in pp.items() if 'CREDIT QUALITY' in t and re.search('Criticized|criticized',t))
            for metric,pat,unit in [
                ('criticized_to_net_loans_pct',r'^(?:Total )?criticized loans to net loans\s+','percent'),
                ('classified_to_net_loans_pct',r'^Total adversely classified loans to net loans\s+','percent'),
                ('substandard_to_net_loans_pct',r'^Substandard loans to net loans\s+','percent'),
                ('past_due_to_net_loans_pct',r'^Delinquencies to net loans\s+','percent'),
                ('nonaccrual_to_net_loans_pct',r'^Non-accrual loans to net loans\s+','percent'),
                ('acl_total',r'^Allowance for credit losses \("ACL"\)\s+','USD_million'),
                ('borrowings_including_subordinated',r'^Borrowings(?:, senior debt and junior| and junior subordinated)?\s*(?:debentures)?\s*','USD_million'),
                ('loans_net',r'^Loans receivable, net\s+','USD_million'),
                ('deposits',r'^Total deposits\s+','USD_million')]:
                old=pp;pp={credit:pp[credit]};read(metric,pat,unit);pp=old
            if not any(r['entity_id']==ticker and r['period_end']==period and r['metric']=='deposits' for r in rows):
                read('deposits',r'^Total customer deposits\s+')
            read('nim_gaap_pct',r'^Net interest margin\s+','percent')
            pretax=read('pretax_income',r'^Income before income taxes\s+',measurement='quarter_flow')
            provision=read('provision',r'^Provision (?:\(release\) )?for credit losses\s+',measurement='quarter_flow')
            read('nonaccrual',r'^Total non-accrual loans\s+',index=-2)
            read('nco',r'^Total net charge-offs \(recoveries\)\s+',index=-2,measurement='quarter_flow')
            read('nib_deposits',r'^Non-Interest Checking\s+',index=-2)
            read('uninsured_uncollateralized_deposits',r'^Non-collatera(?:l)?ized - EOP\s+',index=-2,
                 note='Uninsured AND uncollateralized; not all uninsured deposits')
            read('afs',r'^Available-for-sale securities, at fair value\s+')
            read('htm',r'^Held-to-maturity securities, at amortized cost\s+')
            read('cash',r'^Cash(?: and cash equivalents)?\s+\$')
            for pg,t in pp.items():
                if 'Delinquency Summary' not in t:continue
                line=next(l for l in t.splitlines() if re.match(r'^\d[\d,]* \d[\d,]* \$',l))
                ns=cells(line)
                add('past_due_amortized',ns[-2]/1000,'USD_million',pg,line,
                    note='Total dollars delinquent; excludes loans held for sale. Not just accruing past due.')
                add('past_due_to_amortized_loans_pct',ns[-1],'percent',pg,line,
                    note='Delinquency-summary amortized-cost denominator; kept distinct from release net-loan denominator.')
                break
        elif meta['document_type']=='earnings-result':
            # Tables switched from thousands to rounded millions in 2025 Q3.
            for metric,pat,section,unit,ab in [
                ('deposits',r'^Total deposits\s+','Consolidated Balance Sheets','USD_million',False),
                ('borrowings_ex_subordinated',r'^Borrowings\s+','Consolidated Balance Sheets','USD_million',False),
                ('nib_deposits',r'^Non-interest-bearing\s+','Consolidated Balance Sheets','USD_million',False),
                ('loans_gross',r'^Loans and leases\s+','Consolidated Balance Sheets','USD_million',False),
                ('aoci',r'^Accumulated other comprehensive loss\s+','Consolidated Balance Sheets','USD_million',False),
                ('afs',r'^Available for sale, at fair value\s+','Consolidated Balance Sheets','USD_million',False),
                ('htm',r'^Held to maturity, at amortized cost\s+','Consolidated Balance Sheets','USD_million',False),
                ('nonaccrual',r'^Total loans and leases on non-accrual status\s+',None,'USD_million',False),
                ('npl',r'^Total non-performing loans and leases(?: \(1\),? ?\(2\))?\s+',None,'USD_million',False),
                ('past_due_31_89',r'^Loans and leases past due 31-89 days\s+\$',None,'USD_million',False),
                ('past_due_90_accruing',r'^accruing(?: \(2\))?\s+', 'Credit Quality','USD_million',False),
                ('acl_loans',r'^Balance, end of period\s+\$','Allowance for Credit Losses','USD_million',False),
                ('nco',r'^Total net charge-offs\s+','Allowance for Credit Losses','USD_million',True),
                ('nii',r'^Net interest income\s+', 'Quarter Ended','USD_million',False),
                ('nie',r'^Total non-interest expense\s+', 'Quarter Ended','USD_million',False),
                ('nim_te_pct',r'^Net interest margin(?: \(2\))?\s+', 'Financial Highlights','percent',False)]:
                read(metric,pat,unit,contains=section,negate=ab,
                     measurement='quarter_flow' if metric in ['nco','nii','nie','nim_te_pct'] else 'stock')
            pretax=read('pretax_income',r'^Income(?: \(loss\))? before (?:provision (?:\(benefit\) )?for )?income taxes\s+',contains='Quarter Ended',measurement='quarter_flow')
            provision=read('provision',r'^Provision for credit losses\s+',contains='Quarter Ended',measurement='quarter_flow')
        else:
            office=next(p for p,t in pp.items() if 'Office Portfolio Details' in t)
            for metric,pat,unit in [('office_ltv_pct',r'^Average LTV\s+','percent'),
                ('office_nonowner_dscr',r'^DSC \(non-owner occupied\)\s+','multiple'),
                ('office_nonaccrual',r'^Nonaccrual\s+','USD_million'),
                ('office_special_mention',r'^Special mention\s+','USD_million'),
                ('office_classified',r'^Classified\s+','USD_million'),
                ('office_past_due_30_89',r'^Past due 30-89 days\s+','USD_million')]:
                old=pp;pp={office:pp[office]};read(metric,pat,unit,scale=1,portfolio='office',
                    note='DSCR is non-owner occupied; LTV and credit balances are all-office. Not matched 2027 maturity cohort.');pp=old
            continue
        if pretax and provision:
            add('ppnr_gaap',pretax['value']+provision['value'],'USD_million',pretax['page_or_table'].split()[-1],
                'Pretax income + provision for credit losses',measurement='quarter_flow',status='derived',
                inputs=[pretax['observation_id'],provision['observation_id']],note='Includes GAAP merger and other nonrecurring effects; not adjusted PPNR')
    write_json(OUT/'core_history_observations.json',rows)
    f=pd.DataFrame(rows); f.drop(columns=['scope','input_observation_ids']).to_csv(OUT/'core_history_long.csv',index=False)
    wide=f.pivot(index=['entity_id','period_end','published_at','comparability_segment'],columns='metric',values='value').reset_index()
    wide.to_csv(OUT/'core_history_quarterly.csv',index=False)
    found={(r['entity_id'],r['period_end'],r['metric']) for r in rows}
    gaps=[g for g in gaps if (g['ticker'],g['period_end'],g['metric']) not in found]
    write_json(OUT/'core_history_gaps.json',gaps)
    print('OBSERVATIONS',len(rows),'GAPS',len(gaps))
    return f

if __name__=='__main__':run()
