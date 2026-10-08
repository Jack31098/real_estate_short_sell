"""Financial acceptance checks for the October critical-path research slice."""
import json
import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from colb_refi import calculate,debt_constant
from research_contract import validate_observation,as_of
from market_replay import factor_fit

OUT=ROOT/'outputs/v2'

class CorePathTests(unittest.TestCase):
    def test_refi_independent_ltv_example(self):
        # NOI .9, 6.5% -> 7.5% cap, 57% -> max65% LTV.
        z=calculate(100,.57,.065,-.1,100,.07,.65,1.25,25)
        self.assertAlmostEqual(z['equity_gap'],11.05263157894737)
        self.assertEqual(z['binding_constraint'],'LTV')
        self.assertAlmostEqual(debt_constant(0,25),.04)

    def test_refi_cashflow_and_monotonicity(self):
        a=calculate(100,.57,.065,0,0,.07,.65,1.25,25)
        # Independently calculate required NOI using a standard monthly annuity.
        payment=100*(.07/12)/(1-(1+.07/12)**(-300))
        self.assertAlmostEqual(a['max_noi_decline_without_gap_pct'],(1-payment*12*1.25/a['noi0'])*100)
        for rate in [.06,.07,.08,.09]:
            gaps=[calculate(100,.57,.065,n,100,rate,.65,1.25,25)['equity_gap'] for n in [0,-.1,-.2,-.3]]
            self.assertEqual(gaps,sorted(gaps))
            io=calculate(100,.57,.065,-.1,100,rate,.65,1.25,0)['equity_gap']
            self.assertLessEqual(io,gaps[1])

    def test_original_quarter_units_and_ratings(self):
        f=pd.read_csv(OUT/'core_history_quarterly.csv').set_index(['entity_id','period_end'])
        # Original source cells: old table is $000, new table is $m.
        self.assertAlmostEqual(f.loc[('COLB','2024-03-31'),'ppnr_gaap'],186.203)
        self.assertEqual(f.loc[('COLB','2026-06-30'),'deposits'],52056)
        self.assertEqual(f.loc[('COLB','2026-06-30'),'nonaccrual'],180)
        self.assertEqual(f.loc[('COLB','2026-06-30'),'nco'],30)
        self.assertAlmostEqual(f.loc[('COLB','2024-09-30'),'office_classified'],94.1)
        self.assertAlmostEqual(f.loc[('WAFD','2025-06-30'),'borrowings_including_subordinated'],1991.087)
        self.assertTrue(pd.isna(f.loc[('WAFD','2024-03-31'),'classified_to_net_loans_pct']))
        self.assertEqual(f.loc[('WAFD','2024-03-31'),'substandard_to_net_loans_pct'],1.48)
        for r in json.loads((OUT/'core_rating_reconciliation.json').read_text()):
            self.assertLessEqual(abs(r['sum_ratings']-r['reported_grand_total']),r['tolerance'])

    def test_original_dates_and_lineage(self):
        rows=json.loads((OUT/'core_history_observations.json').read_text())
        definitions=json.loads((OUT/'core_metric_definitions.json').read_text())
        sources={r['source_id']:r for r in json.loads((OUT/'core_source_manifest.json').read_text())}
        ids={r['observation_id'] for r in rows}
        ids.update(c['cell_id'] for rec in json.loads((OUT/'core_rating_reconciliation.json').read_text()) for c in rec['cells'])
        for row in rows:
            validate_observation(row,definitions,sources)
            self.assertTrue(set(row['input_observation_ids'])<=ids)
        r=next(r for r in rows if r['metric']=='classified_amortized' and r['period_end']=='2025-09-30')
        self.assertEqual(r['published_at'],'2025-11-06')
        self.assertEqual(as_of([r],'2025-11-06T23:59:59Z'),[])
        self.assertEqual(len(as_of([r],'2025-11-07T12:00:00Z')),1)

    def test_property_coverage_and_vintage(self):
        f=pd.read_csv(OUT/'property_monthly_long.csv')
        self.assertEqual(f.geography.nunique(),6)
        self.assertEqual(f.groupby('geography').period_end.nunique().min(),32)
        self.assertTrue(f.available_at.eq(f.retrieved_at).all())
        self.assertTrue(f.available_at.str.startswith('2026-10-08').all())
        nw=pd.read_csv(OUT/'property_nwmls_september.csv').set_index('property_type')
        self.assertEqual(nw.loc['residential_and_condo','active_listings'],8058)
        self.assertAlmostEqual(nw.loc['condo','closed_yoy_pct'],(352/464-1)*100,places=2)

    def test_hpp_bridge_does_not_repay_announced_tender(self):
        d=pd.read_csv(OUT/'hpp_debt_bridge.csv').set_index('year')
        self.assertAlmostEqual(d.june_maturity.sum(),2831.042)
        self.assertAlmostEqual(d.june_anchor_known_events.sum(),2831.042)
        self.assertAlmostEqual(d.loc[2027,'june_anchor_known_events'],1033.962)
        self.assertEqual(d.completed_tender_reduction.sum(),0)
        self.assertTrue(d.unallocated_sale_debt_repayment.isna().all())
        h=json.loads((OUT/'hpp_current_bridge.json').read_text())
        self.assertAlmostEqual(h['lease_2027_identified_sale_adjusted_current_ABR'],60.462271)
        self.assertFalse(h['remaining_lease_roll_is_complete'])
        self.assertAlmostEqual(h['tender_full_acceptance_cash_scenario'],197.125)

    def test_factor_specification_known_residual(self):
        rng=np.random.default_rng(41);n=80
        x=rng.normal(0,.01,n); y=.0001+1.4*x
        y[-2:]-=.03
        f=pd.DataFrame({'KRE':x,'TARGET':y},index=pd.date_range('2024-01-01',periods=n).strftime('%Y-%m-%d'))
        result=factor_fit(f,'TARGET',f.index[-2],f.index[-1],60,['KRE'])
        self.assertAlmostEqual(result['sum_daily_residual_pct'],-6)
        with self.assertRaises(ValueError):factor_fit(f,'TARGET',f.index[-2],f.index[-1],60,['TARGET'])

if __name__=='__main__':unittest.main()
