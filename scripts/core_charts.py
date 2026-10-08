"""Standalone scientific figures from the generated, source-linked panels."""
import sys
from research_sources import ROOT,OUT
try:
    import matplotlib
except ImportError:
    sys.path.append(str(ROOT/'data/runtime'))
    import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

FIG=OUT/'figures'
COLORS=['#146E87','#A44829','#6E5AA6','#397C45','#C39126','#777777']
CORE_REGIONS=['King County, WA','Snohomish County, WA','Pierce County, WA','Santa Clara County, CA']

def save(fig,name):
    FIG.mkdir(exist_ok=True)
    fig.savefig(FIG/(name+'.png'),dpi=160,bbox_inches='tight',facecolor='white')
    plt.close(fig)

def decorate(ax):
    ax.grid(alpha=.2);ax.spines[['top','right']].set_visible(False)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))

def run():
    plt.rcParams.update({'font.size':10,'axes.titlesize':11,'figure.titlesize':16})
    f=pd.read_csv(OUT/'property_redfin_selected.csv');f['date']=pd.to_datetime(f['PERIOD END'])
    fig,axes=plt.subplots(2,3,figsize=(15,8),layout='constrained')
    metrics=[('PENDING SALES','Pending sales'),('HOMES SOLD','Closed sales'),('INVENTORY','Inventory'),
        ('MEDIAN DAYS ON MARKET (DAYS)','Median days on market'),('MONTHS OF SUPPLY','Months of supply'),('PERCENT ACTIVE WITH PRICE DROPS (%)','Active listings with price cuts (%)')]
    for ax,(metric,title) in zip(axes.flat,metrics):
        for region,color in zip(CORE_REGIONS,COLORS):
            z=f[f['REGION NAME']==region].sort_values('date')
            ax.plot(z.date,z[metric],label=region.split(' County')[0],color=color,lw=1.7)
        ax.set_title(title);decorate(ax)
    axes[0,0].legend(ncol=2,fontsize=9)
    fig.suptitle('Residential liquidity: raw monthly series | Jan 2024 - Aug 2026')
    fig.supxlabel('Source: Redfin, Oct 7 2026 revised vintage. Vendor monthly series; no composite, no city weights.',fontsize=10)
    save(fig,'property_liquidity')
    h=pd.read_csv(OUT/'property_hpi_quarterly.csv');h['date']=pd.to_datetime(h.period_end)
    fig,axes=plt.subplots(1,2,figsize=(14,5.3),layout='constrained')
    for region,color in zip(CORE_REGIONS,COLORS):
        z=f[f['REGION NAME']==region].sort_values('date')
        axes[0].plot(z.date,z['MEDIAN SALE PRICE NSA YOY (%)'],label=region.split(' County')[0],color=color)
    for name,color in zip(['Seattle','Tacoma','San Jose'],[COLORS[0],COLORS[2],COLORS[3]]):
        z=h[h.metro_name.str.startswith(name)]
        axes[1].plot(z.date,z.yoy_nsa_pct,label=name+' metro/division',marker='o',color=color)
    for ax,title in zip(axes,['Transaction median: year-over-year (%)','FHFA repeat-sale HPI: year-over-year (%)']):
        ax.set_title(title);ax.axhline(0,color='black',lw=.7);decorate(ax);ax.legend(fontsize=9)
    fig.suptitle('Residential collateral indicators | Geography and property mix differ')
    fig.supxlabel('Redfin and FHFA current revised vintages. These are residential prices, not office collateral values.',fontsize=10)
    save(fig,'property_collateral')
    b=pd.read_csv(OUT/'core_history_quarterly.csv');b['date']=pd.to_datetime(b.period_end)
    fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    for i,ticker in enumerate(['WAFD','COLB']):
        z=b[b.entity_id==ticker].sort_values('date')
        if ticker=='WAFD':
            ms=[('criticized_to_net_loans_pct','Criticized / net loans (%)'),('classified_to_net_loans_pct','Classified / net loans (%)'),('substandard_to_net_loans_pct','Substandard only (%)')]
        else:ms=[('criticized_amortized','Criticized ($m)'),('classified_amortized','Classified ($m)')]
        for (metric,label),color in zip(ms,COLORS):axes[0,i].plot(z.date,z[metric],label=label,color=color,marker='o')
        axes[0,i].set_title(ticker+' credit ratings (overlapping categories)');axes[0,i].legend(fontsize=9)
        for metric,label,color in [('deposits','Deposits',COLORS[0]),('nib_deposits','Non-interest deposits',COLORS[2]),('borrowings_including_subordinated' if ticker=='WAFD' else 'borrowings_ex_subordinated','Borrowings',COLORS[1])]:
            y=z[metric]/z[metric].iloc[0]*100
            axes[1,i].plot(z.date,y,label=label,color=color)
        axes[1,i].set_title(ticker+' funding: 2024Q1 = 100 (not a stress score)');axes[1,i].legend(fontsize=9)
        for ax in axes[:,i]:
            decorate(ax)
            if ticker=='COLB':ax.axvline(pd.Timestamp('2025-08-31'),ls='--',color='#666',lw=1)
    fig.suptitle('Original-quarter bank history | 2024Q1 - 2026Q2')
    fig.supxlabel('COLB dashed line: PPBI acquisition, Aug 2025. WAFD LBC closed Feb 2024. Ratio definitions differ; no cross-bank ranking from levels.',fontsize=9)
    save(fig,'bank_history')
    g=pd.read_csv(OUT/'colb_refi_grid.csv')
    fig,axes=plt.subplots(1,4,figsize=(15,4.6),layout='constrained')
    for ax,rate in zip(axes,[.06,.07,.08,.09]):
        z=g[(g.baseline_cap_rate==.065)&(g.maximum_ltv==.65)&(g.amortization_years==25)&(g.refinance_rate==rate)]
        a=z.pivot(index='noi_change',columns='cap_change_bps',values='equity_gap').sort_index(ascending=False)
        im=ax.imshow(a.values,vmin=0,vmax=50,cmap='YlOrRd',aspect='auto')
        ax.set_xticks(range(3),['0','+100','+200']);ax.set_yticks(range(4),['0%','-10%','-20%','-30%'])
        ax.set_title(f'Refinance rate {rate:.0%}');ax.set_xlabel('Cap-rate change (bps)')
        for (i,j),v in np.ndenumerate(a.values):ax.text(j,i,f'{v:.1f}',ha='center',va='center',color='white' if v>35 else '#222')
    axes[0].set_ylabel('NOI change');fig.colorbar(im,ax=axes,label='Gap per $100 existing principal',shrink=.8)
    fig.suptitle('COLB-inspired hypothetical loan: refinancing gap, not bank loss')
    fig.supxlabel('Assumed initial LTV 57%, cap 6.5%; new max LTV 65%, min DSCR 1.25, 25-year amortization. Actual 2027 cohort unknown.',fontsize=9)
    save(fig,'colb_refi_gap')
    d=pd.read_csv(OUT/'hpp_debt_bridge.csv');x=np.arange(len(d))
    fig,ax=plt.subplots(figsize=(10,5),layout='constrained')
    ax.bar(x-.19,d.june_maturity,.38,label='June 30 schedule',color=COLORS[0])
    ax.bar(x+.19,d.june_anchor_known_events,.38,label='June anchor + executed Hollywood extension',color=COLORS[1])
    ax.set_xticks(x,d.year);ax.set_ylabel('HPP ownership share ($m)');ax.set_title('HPP: near-term relief moves the maturity wall into 2027')
    ax.legend(fontsize=9);ax.grid(axis='y',alpha=.2);ax.spines[['top','right']].set_visible(False)
    fig.supxlabel('June balances net of acquired CMBS; includes JVs/amortization. Announced tender and unallocated sale proceeds NOT deducted.',fontsize=9)
    save(fig,'hpp_maturity_bridge')

if __name__=='__main__':run()
