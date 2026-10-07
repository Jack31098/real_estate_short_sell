from pathlib import Path
import copy
import json
import sys
import unittest

import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from research_contract import as_of, available_date, deposit_beta, exact_arithmetic, scope, validate_observation
from research_v2 import fiscal_label, states, scope_audit
from market_replay import parse_chart, window_return, factor_fit
from research_sources import filing_rows


class EvidenceTests(unittest.TestCase):
    def test_future_revision_excluded_and_old_revision_retained(self):
        a=dict(observation_id='old',entity_id='B',period_end='2026-06-30',metric='npl',scope={},
               metric_definition_version='npl.v1',available_at='2026-07-25T12:00:00+00:00',value=1)
        b={**a,'observation_id':'new','available_at':'2026-10-01T12:00:00+00:00','value':2}
        self.assertEqual(as_of([a,b],'2026-09-01T00:00:00+00:00'),[a])
        self.assertEqual(as_of([a,b],'2026-10-02T00:00:00+00:00'),[b])

    def test_timezone_comparison_not_string_order(self):
        r=dict(observation_id='a',entity_id='B',period_end='2026-06-30',metric='npl',scope={},
               metric_definition_version='npl.v1',available_at='2026-09-01T01:00:00-07:00')
        self.assertEqual(as_of([r],'2026-09-01T07:59:59Z'),[])
        self.assertEqual(as_of([r],'2026-09-01T08:00:00Z'),[r])

    def test_date_only_and_exact_publication_time(self):
        self.assertEqual(available_date('2026-09-07'),'2026-09-08T12:00:00+00:00')
        self.assertEqual(available_date('2026-09-07T10:00:00-07:00'),'2026-09-07T17:00:00+00:00')

    def test_fiscal_calendar_alignment(self):
        self.assertEqual(fiscal_label('WAFD','2025-12-31'),'FY2026Q1')
        self.assertEqual(fiscal_label('WAFD','2026-06-30'),'FY2026Q3')
        self.assertEqual(fiscal_label('COLB','2026-06-30'),'CY2026Q2')

    def test_exact_tag_cannot_override_incompatible_scope(self):
        sc=scope('B','2026-06-30','office',basis='gross before fees')
        pct={'value':15,'unit':'percent','scope':sc}
        amount={'value':100,'unit':'USD_million','scope':sc}
        self.assertEqual(exact_arithmetic(pct,amount,'multiply_fraction','exact','reviewed same table',sc),15)
        amount['scope']={**sc,'basis':'net after fees'}
        with self.assertRaisesRegex(ValueError,'Scope mismatch'):
            exact_arithmetic(pct,amount,'multiply_fraction','exact','claims exact',sc)
        for match in ['approximate','incompatible','unreviewed']:
            with self.assertRaises(ValueError):
                exact_arithmetic(pct,amount,'multiply_fraction',match,'reviewed',sc)

    def test_null_and_unreviewed_arithmetic_blocked(self):
        sc=scope('B','2026-06-30');a={'value':None,'unit':'percent','scope':sc};b={'value':100,'unit':'USD_million','scope':sc}
        with self.assertRaises(ValueError):exact_arithmetic(a,b,'multiply_fraction','exact','evidence',sc)
        a['value']=20; b['scope']={**sc,'ownership':'unknown'}
        with self.assertRaises(ValueError):exact_arithmetic(a,b,'multiply_fraction','exact','evidence',b['scope'])

    def test_beta_does_not_divide_by_flat_policy_rate(self):
        self.assertIsNone(deposit_beta(2,1.9,5,5))
        self.assertIsNone(deposit_beta(2,None,5,4))
        self.assertAlmostEqual(deposit_beta(2,1.5,5,4),.5)

    def test_historical_filing_discovery_includes_amendments_and_8k(self):
        block={'form':['10-Q','8-K','10-Q/A','4'],'filingDate':['2026-08-01']*4,
               'accessionNumber':['a','b','c','d'],'primaryDocument':['a.htm','b.htm','c.htm','d.htm']}
        rows=filing_rows(block,'B',1,'2024-01-01','2026-09-01')
        self.assertEqual([r['form'] for r in rows],['10-Q','8-K','10-Q/A'])


class MarketTests(unittest.TestCase):
    def test_dividends_and_split_not_counted_as_capital_gain(self):
        # Vendor closes are already split-adjusted; never divide again on split date.
        stamps=[int(pd.Timestamp(s,tz='UTC').timestamp()) for s in ['2026-09-01 20:00','2026-09-02 20:00','2026-09-03 20:00']]
        payload={'chart':{'result':[{'timestamp':stamps,'indicators':{'quote':[{'close':[50,49,49],'volume':[1,2,3]}],
          'adjclose':[{'adjclose':[49,49,49]}]},'events':{'dividends':{'x':{'date':stamps[1],'amount':1}},
          'splits':{'y':{'date':stamps[2],'numerator':2,'denominator':1,'splitRatio':'2:1'}}}}]}}
        f,actions=parse_chart(payload,'B','2026-09-03')
        self.assertAlmostEqual(f.iloc[1].total_return,0)
        self.assertAlmostEqual(f.iloc[2].price_return,0)
        self.assertEqual(len(actions),2)
        f,_=parse_chart(payload,'B','2026-09-02')
        self.assertEqual(len(f),2)

    def test_missing_endpoint_is_not_silently_shifted(self):
        f=pd.DataFrame({'date':['2026-09-01'],'close':[1],'adjusted_close':[1]})
        with self.assertRaises(ValueError):window_return(f,'2026-08-31','2026-09-01')

    def test_future_returns_cannot_change_event_coefficients(self):
        rng=np.random.default_rng(43); dates=pd.bdate_range('2025-01-01',periods=300).strftime('%Y-%m-%d')
        f=pd.DataFrame(rng.normal(0,.01,(300,5)),index=dates,columns=['B','KRE','SPY','d2y','d10y'])
        event=dates[280];end=dates[-1]
        before=factor_fit(f,'B',event,end,252)
        f.loc[event:,'B']+=.1
        after=factor_fit(f,'B',event,end,252)
        self.assertEqual(before['coefficients'],after['coefficients'])
        self.assertLess(before['training_end'],event)
        self.assertNotEqual(before['sum_daily_residual_pct'],after['sum_daily_residual_pct'])
        f.loc[event,'d2y']=np.nan
        with self.assertRaisesRegex(ValueError,'Missing event-window'):
            factor_fit(f,'B',event,end,252)


class PersistedPanelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows=json.loads((ROOT/'outputs/v2/reviewed_observations.json').read_text(encoding='utf-8'))
        cls.defs=json.loads((ROOT/'outputs/v2/metric_definitions.json').read_text(encoding='utf-8'))
        cls.sources={s['source_id']:s for s in json.loads((ROOT/'outputs/v2/source_manifest.json').read_text(encoding='utf-8'))}

    def test_source_substitution_and_unexplained_null_fail(self):
        r=copy.deepcopy(self.rows[0]);r['source_sha256']='different'
        with self.assertRaises(ValueError):validate_observation(r,self.defs,self.sources)
        r=copy.deepcopy(self.rows[0]);r['value']=None
        with self.assertRaises(ValueError):validate_observation(r,self.defs,self.sources)

    def test_intraday_publication_cannot_precede_availability(self):
        r=copy.deepcopy(self.rows[0]);r['published_at']='2026-07-16T21:00:00Z';r['available_at']='2026-07-16T20:00:00Z'
        with self.assertRaises(ValueError):validate_observation(r,self.defs,self.sources)

    def test_three_quarters_and_ppnr_bridge(self):
        for entity in ['WAFD','COLB']:
            for period in ['2025-12-31','2026-03-31','2026-06-30']:
                group={r['metric']:r for r in self.rows if r['entity_id']==entity and r['period_end']==period and r['geography']=='all'}
                self.assertIn('nonaccrual_loans',group);self.assertIn('deposits',group)
                self.assertAlmostEqual(group['ppnr_gaap_basis']['value'],group['pretax_income']['value']+group['provision_total']['value'])
                self.assertEqual(len(group['ppnr_gaap_basis']['input_observation_ids']),2)

    def test_colb_npl_is_not_nonaccrual_and_office_not_added(self):
        group={r['metric']:r['value'] for r in self.rows if r['entity_id']=='COLB' and r['period_end']=='2026-06-30' and r['geography']=='all'}
        self.assertEqual(group['nonperforming_loans'],group['nonaccrual_loans']+group['past_due_90plus_accruing'])
        self.assertEqual(group['nonperforming_loans'],268)
        self.assertEqual(scope_audit(self.rows)[0]['gate_result'],'blocked')

    def test_two_states_do_not_fill_unknown_with_zero_or_sum_classifications(self):
        for s in states(self.rows,'2026-09-01T23:59:59Z'):
            self.assertIsNone(s['LiquidityStress']['value']);self.assertIsNone(s['joint_score'])
            self.assertEqual(s['CreditStress']['status'],'observed_vector_no_composite')
            self.assertIsNone(s['CreditStress']['value'])

    def test_september_first_has_no_future_merger_or_owner_event(self):
        snapshots=json.loads((ROOT/'outputs/v2/four_layer_asof_inputs.json').read_text(encoding='utf-8'))
        self.assertEqual(snapshots[0]['event_ids'],[])
        self.assertIn('wafd_everbank_announcement_20260907',snapshots[1]['event_ids'])
        self.assertNotIn('hpp_tender_20261005',snapshots[2]['event_ids'])
        self.assertIn('hpp_tender_20261005',snapshots[3]['event_ids'])

    def test_no_post_outcome_control_declared_matched(self):
        r=json.loads((ROOT/'config/v2_control_registry.json').read_text())
        self.assertTrue(r['retrospective_design']);self.assertEqual(r['validated_matches'],[])
        self.assertTrue(all(c['verified_low_tech'] is None for c in r['bank_candidates']))


if __name__=='__main__':unittest.main()
