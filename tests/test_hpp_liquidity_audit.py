import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from hpp_liquidity_audit import audit, cash_spend_capacity, coverage_headroom, reconcile_cash, same_basis_funding_gap


class LiquidityAuditTests(unittest.TestCase):
    def test_fractional_numerator_headroom(self):
        self.assertAlmostEqual(coverage_headroom(1.6, 1.5), .0625)
        self.assertAlmostEqual(coverage_headroom(1.6, 1.5, .05), .015625)

    def test_threshold_equality_and_growth_requirement(self):
        self.assertAlmostEqual(coverage_headroom(1.5, 1.5), 0)
        self.assertLess(coverage_headroom(1.4, 1.5), 0)

    def test_invalid_coverage(self):
        for values in [(0, 1.5, 0), (1.6, 1.5, -1), (float('nan'), 1.5, 0)]:
            with self.assertRaises(ValueError):
                coverage_headroom(*values)

    def test_commitments_trigger_even_when_no_borrowings(self):
        r = cash_spend_capacity(80.760, 795.250, 795.250)
        self.assertEqual(r['applicable_floor'], 125)
        self.assertAlmostEqual(r['maximum_net_cash_spend_under_this_constraint'], 751.010)
        self.assertIsNone(r['certified_drawable_capacity'])

    def test_trigger_is_strictly_above_600(self):
        self.assertEqual(cash_spend_capacity(80, 600, 600)['applicable_floor'], 0)
        self.assertEqual(cash_spend_capacity(80, 462, 462)['applicable_floor'], 0)

    def test_draw_does_not_create_total_liquidity(self):
        before = cash_spend_capacity(80, 795.25, 795.25)['liquidity']
        after_draw = cash_spend_capacity(180, 695.25, 795.25)['liquidity']
        self.assertEqual(before, after_draw)

    def test_cash_or_revolver_tender_spend_same_liquidity(self):
        cash_funded = cash_spend_capacity(300-197.125, 795.25, 795.25)['liquidity']
        draw_funded = cash_spend_capacity(300, 795.25-197.125, 795.25)['liquidity']
        self.assertEqual(cash_funded, draw_funded)

    def test_unknown_flows_do_not_become_zero(self):
        self.assertIsNone(reconcile_cash(80.760, {'sales': 90.5, 'operating_cash': None})['current_cash'])
        self.assertAlmostEqual(reconcile_cash(80.760, {'net_sales': 85.0, 'capex': -20.0})['current_cash'], 145.760)

    def test_basis_mismatch_blocks_funding_gap(self):
        with self.assertRaises(ValueError):
            same_basis_funding_gap(1033.962, 542.760, 'HPP_share', 'consolidated')
        self.assertIsNone(same_basis_funding_gap(1033.962, None, 'HPP_share', 'HPP_share'))

    def test_snapshot_preserves_gates_and_tender_chronology(self):
        cfg = json.loads((ROOT/'config/hpp_liquidity_inputs.json').read_text(encoding='utf-8'))
        r = audit(cfg)
        self.assertIsNone(r['current_cash_reconciliation']['current_cash'])
        self.assertIsNone(r['actual_2027_funding_gap'])
        self.assertIsNone(r['coverage']['noi_drop_threshold'])
        self.assertEqual(r['tender']['verified_completed_principal_reduction'], 0)
        self.assertAlmostEqual(r['tender']['conditional_full_targets_net_debt_change_before_interest_fees'], -2.875)
        self.assertAlmostEqual(r['maturity_2027_known_event_hpp_share'], 1033.962)
        self.assertFalse(r['joint_nav_calibrated'])
        cfg['research_cutoff'] = '2026-10-09T21:01:00+00:00'
        with self.assertRaises(ValueError):
            audit(cfg)


if __name__ == '__main__':
    unittest.main()
