"""Targeted COLB rating and funding cells from original 10-Q/K vintages."""
import json
import re
from copy import deepcopy
import pandas as pd
from core_history import pages, cells
from research_contract import available_date
from research_sources import ROOT, OUT, digest, write_json

# Official IR filing-list dates, checked October 7, 2026 Pacific.
# In particular Q3 2025 was FILED November 6, although signed November 5.
FILINGS = dict(zip(
    ['2024-03-31','2024-06-30','2024-09-30','2024-12-31','2025-03-31',
     '2025-06-30','2025-09-30','2025-12-31','2026-03-31','2026-06-30'],
    [('2024-05-07',17518711),('2024-08-06',17735591),('2024-11-05',17943480),
     ('2025-02-25',18220609),('2025-05-06',18439293),('2025-08-06',18671198),
     ('2025-11-06',18897295),('2026-02-26',19191691),('2026-05-05',19412677),('2026-08-04',19664788)]))

def run():
    rows=json.loads((OUT/'core_history_observations.json').read_text())
    rows=[r for r in rows if not r.get('filing_extension')]
    sources=json.loads((OUT/'core_source_manifest.json').read_text())
    reconciliations=[]; audit=[]
    for meta in sources:
        if meta['ticker']!='COLB' or meta['document_type'] not in ['10-Q','10-K']: continue
        period=meta['period_end']; published,fid=FILINGS[period]
        pp=pages(meta)
        base=next(r for r in rows if r['entity_id']=='COLB' and r['period_end']==period)
        def add(metric,value,pg,evidence,status='observed',inputs=None,note=''):
            r=deepcopy(base)
            r.update(observation_id='core_'+digest(f"{meta['source_id']}|{metric}|{pg}".encode())[:24],
                source_id=meta['source_id'],source_sha256=meta['sha256'],source_url=meta['url'],
                published_at=published,available_at=available_date(published),retrieved_at=meta['retrieved_at'],
                metric=metric,value=value,unit='USD_million',page_or_table=f'PDF page(s) {pg}',
                source_row=evidence,status=status,input_observation_ids=inputs or [],notes=note,
                metric_definition_version=metric+'@core-1',filing_extension=True,
                publication_evidence=f'https://www.columbiabankingsystem.com/sec-filings/sec-filings/sec-filings-details/default.aspx?FilingId={fid}')
            rows.append(r);return r
        longdate=pd.Timestamp(period).strftime('%B %d, %Y').replace(' 0',' ')
        ratingrows=[]; total=None; used=[]
        for pg,t in pp.items():
            if 'Term Loans Amortized Cost Basis by Origination Year' not in t:continue
            # Match the table header, not a mention of the date in the next note.
            header=t[:t.index('Credit quality indicator:')] if 'Credit quality indicator:' in t else t[:800]
            if not re.search('^'+re.escape(longdate)+r'\s',header,re.M):continue
            scale=.001 if '(in thousands)' in t else 1.0
            used.append(pg)
            for line in t.splitlines():
                m=re.match(r'^(Pass/Watch|Special mention|Substandard|Doubtful|Loss)\s+(.+)$',line)
                if m:
                    ratingrows.append((m[1],cells(m[2])[-1]*scale,pg,line))
                if line.startswith('Grand total '):total=cells(line)[-1]*scale
        if not used or total is None:raise ValueError(f'No complete current-quarter rating table: {period}, {used}')
        summed=sum(v for _,v,_,_ in ratingrows)
        # Rounded-million disclosure can differ by one per displayed class cell.
        tolerance=.002 if period<'2025-09-30' else len(ratingrows)*.5
        if abs(summed-total)>tolerance:raise ValueError(f'Rating reconciliation {period}: {summed} != {total}')
        parts={}
        for label in ['Special mention','Substandard','Doubtful','Loss']:
            rr=[x for x in ratingrows if x[0]==label]
            parts[label]=add('rating_'+label.lower().replace(' ','_'),sum(x[1] for x in rr),','.join(map(str,used)),
                'Sum of Total column across distinct loan classes: '+label, status='derived',
                # Source cell IDs below are persisted alongside the reconciliations.
                inputs=[f"{meta['source_id']}:p{x[2]}:rating_cell_{i}" for i,x in enumerate(ratingrows) if x[0]==label],
                note='All loan classes at amortized cost; includes guarantee-backed loans and fair-value marks. Not gross loans or a commercial-only portfolio.')
        classified=add('classified_amortized',sum(parts[k]['value'] for k in ['Substandard','Doubtful','Loss']),','.join(map(str,used)),
            'Substandard + Doubtful + Loss',status='derived',inputs=[parts[k]['observation_id'] for k in ['Substandard','Doubtful','Loss']])
        add('criticized_amortized',classified['value']+parts['Special mention']['value'],','.join(map(str,used)),
            'Special mention + Classified',status='derived',inputs=[classified['observation_id'],parts['Special mention']['observation_id']])
        reconciliations.append({'period_end':period,'source_id':meta['source_id'],'pages':used,
            'sum_ratings':summed,'reported_grand_total':total,'rounding_difference':summed-total,
            'unit':'USD_million','tolerance':tolerance,
            'cells':[{'cell_id':f"{meta['source_id']}:p{x[2]}:rating_cell_{i}", 'rating':x[0],'value':x[1],'page':x[2],'source_row':x[3]} for i,x in enumerate(ratingrows)]})
        # Original-quarter deposit tables, when they exist. Narrative fallbacks
        # retain their reported $0.1bn precision; no future comparison column.
        found=set()
        for pg,t in pp.items():
            scale=.001 if period<'2025-09-30' else 1
            for line in t.splitlines():
                for metric,pat in [('uninsured_deposits',r'^Uninsured deposits \(1\)\s+'),
                                   ('brokered_deposits',r'^Brokered(?: deposits)?\s+(?=[\d$])')]:
                    m=re.match(pat,line)
                    if m and metric not in found:
                        add(metric,cells(line[m.end():])[0]*scale,pg,line);found.add(metric)
            flat=' '.join(t.split())
            for metric,pat in [('uninsured_deposits',r'(?:Estimated )?[Uu]ninsured deposits were \$([\d.]+) billion'),
                               ('brokered_deposits',r"[Bb]rokered deposits (?:totaled|were) \$([\d.]+)(?: billion)?")]:
                m=re.search(pat,flat)
                if m and metric not in found:
                    add(metric,float(m[1])*1000,pg,flat[max(0,m.start()-40):m.end()+160],note='Rounded to $0.1bn in original narrative.');found.add(metric)
            if period=='2024-12-31' and 'uninsured_deposits' not in found:
                m=re.search(r'Uninsured deposits as of December 31, 2024, totaled \$([\d.]+) billion',flat)
                if m:
                    add('uninsured_deposits',float(m[1])*1000,pg,m[0],note='Rounded to $0.1bn in original narrative.');found.add('uninsured_deposits')
        audit.append({'period_end':period,'published_at':published,'filing_id':fid,'funding_extracted':sorted(found)})
    write_json(OUT/'core_history_observations.json',rows)
    f=pd.DataFrame(rows)
    f.drop(columns=['scope','input_observation_ids']).to_csv(OUT/'core_history_long.csv',index=False)
    # Publication differs by metric; the long file remains the authoritative PIT table.
    f.pivot(index=['entity_id','period_end'],columns='metric',values='value').reset_index().to_csv(OUT/'core_history_quarterly.csv',index=False)
    write_json(OUT/'core_rating_reconciliation.json',reconciliations)
    write_json(OUT/'core_filing_dates.json',audit)
    print('Filing series:',len(reconciliations),'quarters;',len(rows),'total observations')
    return f

if __name__=='__main__':run()
