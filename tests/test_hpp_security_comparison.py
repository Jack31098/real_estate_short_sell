import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from hpp_security_comparison import yield_price,short_return,required_preferred_exit,liquidation_pool,tender_effect,calculate,validate_config

class SecurityComparisonTests(unittest.TestCase):
    def test_carry_can_turn_a_price_decline_into_a_loss(self):
        result=short_return(14.46,13,1,1.1875,.05)
        self.assertGreater(result['gross_price_return'],0)
        self.assertLess(result['net_return'],0)

    def test_no_dividend_zero_fee_common_return(self):
        self.assertAlmostEqual(short_return(10,6,1)['net_return'],.4)

    def test_redemption_loss_exceeds_seventy_percent(self):
        self.assertLess(short_return(14.46,25,0)['net_return'],-.7)

    def test_yearly_cost_scales_with_horizon(self):
        one=short_return(14.46,10,1,1.1875,.05)
        two=short_return(14.46,10,2,1.1875,.05)
        self.assertAlmostEqual(one['net_return']-two['net_return'],1.1875/14.46+.05)

    def test_match_threshold_matches_actual_returns(self):
        for common_exit in [0,3,8,12,20]:
            cn=short_return(11.88,common_exit,1,0,.03)['net_return']
            pp=required_preferred_exit(14.46,1.1875,1,.05,cn)
            if pp is not None:
                self.assertAlmostEqual(short_return(14.46,pp,1,1.1875,.05)['net_return'],cn)
            else:
                self.assertLess(short_return(14.46,0,1,1.1875,.05)['net_return'],cn)

    def test_yield_price_is_not_call_price(self):
        self.assertAlmostEqual(yield_price(1.1875,.12),9.8958333333)
        self.assertGreater(yield_price(1.1875,.04),25)

    def test_seniority_common_has_zero_when_preferred_impaired(self):
        for pool in [0,100,300,424.9]:
            result=liquidation_pool(pool,17)
            self.assertEqual(result['common_residual_m'],0)
            self.assertLess(result['preferred_recovery_per_share'],25)

    def test_parity_and_arrears_allocate_proportionately(self):
        r=liquidation_pool(260,17,25,1,78)
        self.assertAlmostEqual(r['preferred_recovery_per_share'],13)
        self.assertEqual(r['common_residual_m'],0)

    def test_announcement_does_not_reduce_debt(self):
        self.assertEqual(tender_effect(200,197.125,1,'announced')['observed_net_debt_change_m'],0)

    def test_cash_and_revolver_net_debt_effect_agree(self):
        cash=tender_effect(200,197.125,0,'settled')
        debt=tender_effect(200,197.125,1,'settled')
        self.assertAlmostEqual(cash['observed_net_debt_change_m'],-2.875)
        self.assertEqual(cash['observed_net_debt_change_m'],debt['observed_net_debt_change_m'])
        self.assertNotEqual(cash['observed_gross_debt_change_m'],debt['observed_gross_debt_change_m'])

    def test_bad_inputs_fail(self):
        for values in [(0,10,1),(10,-1,1),(10,1,-1),(10,float('nan'),1)]:
            with self.assertRaises(ValueError):short_return(*values)
        with self.assertRaises(ValueError):yield_price(1,0)

    def test_cutoff_and_unsettled_tender_gates(self):
        cfg=json.loads((ROOT/'config/hpp_security_inputs.json').read_text(encoding='utf-8'))
        future=copy.deepcopy(cfg);future['price_date']='2026-10-10'
        with self.assertRaises(ValueError):validate_config(future)
        wrong=copy.deepcopy(cfg);wrong['known_event_bridge']['observed_completed_principal_reduction']=200
        with self.assertRaises(ValueError):validate_config(wrong)

    def test_saved_scenarios_remain_scenarios(self):
        cfg=json.loads((ROOT/'config/hpp_security_inputs.json').read_text(encoding='utf-8'))
        r=calculate(cfg)
        self.assertEqual(len(r['short_scenarios']),456)
        self.assertTrue(all(row['status']=='scenario' for row in r['short_scenarios']))
        self.assertAlmostEqual(r['headline']['preferred_current_yield'],1.1875/14.46)
        cfg['scenario_assumptions']['central_common_exit']=0
        impossible=calculate(cfg)
        self.assertIsNone(impossible['headline']['preferred_exit_to_match_common'])
        self.assertIsNone(impossible['headline']['preferred_yield_to_match_common'])

if __name__=='__main__':unittest.main()
