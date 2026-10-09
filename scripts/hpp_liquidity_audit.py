"""Cash and contract audit. Unknown flows never become a current cash estimate."""
import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} must be a finite number')
    if positive and value <= 0:
        raise ValueError(f'{name} must be positive')
    return float(value)


def coverage_headroom(ratio, minimum, fixed_charge_change=0.0):
    """Fractional numerator fall to equality; negative means growth is required."""
    r = number(ratio, 'ratio', positive=True)
    m = number(minimum, 'minimum', positive=True)
    change = number(fixed_charge_change, 'fixed charge change')
    if change <= -1:
        raise ValueError('fixed charges must remain positive')
    return 1.0 - m * (1.0 + change) / r


def cash_spend_capacity(cash, unused, commitments, minimum=125.0, trigger=600.0):
    """Only this liquidity constraint; does not certify borrowing availability."""
    c = number(cash, 'cash')
    u = number(unused, 'unused')
    k = number(commitments, 'commitments')
    m = number(minimum, 'minimum')
    t = number(trigger, 'trigger')
    if min(c, u, k, m, t) < 0 or u > k:
        raise ValueError('invalid liquidity balances')
    floor = m if k > t else 0.0
    return dict(liquidity=c+u, applicable_floor=floor,
                maximum_net_cash_spend_under_this_constraint=max(0.0, c+u-floor),
                shortfall_to_floor=max(0.0, floor-c-u),
                certified_drawable_capacity=None)


def reconcile_cash(anchor_cash, signed_flows):
    c = number(anchor_cash, 'anchor cash')
    missing = sorted(k for k, value in signed_flows.items() if value is None)
    if missing:
        return dict(current_cash=None, missing=missing, status='unreconciled')
    return dict(current_cash=c+sum(number(v, k) for k, v in signed_flows.items()),
                missing=[], status='reconciled_input_arithmetic')


def same_basis_funding_gap(maturity, resources, maturity_basis, resource_basis):
    if maturity_basis != resource_basis:
        raise ValueError('Funding gap requires matched legal/economic basis')
    if maturity is None or resources is None:
        return None
    return max(0.0, number(maturity, 'maturity')-number(resources, 'resources'))


def audit(config):
    a = config['anchor']
    c = config['contract']
    cutoff = datetime.fromisoformat(config['research_cutoff'])
    events = {e['id']: e for e in config['events']}
    tender = events['tender']
    if cutoff >= datetime.fromisoformat(tender['expiration']):
        raise ValueError('Refresh tender status for a cutoff at/after scheduled expiration')
    capacity = cash_spend_capacity(a['consolidated_unrestricted_cash'], a['reported_undrawn_capacity'],
                                  a['revolving_commitments'], c['liquidity_minimum'],
                                  c['liquidity_trigger_commitments'])
    r = a['fixed_charge_ratio_displayed']
    m = a['fixed_charge_minimum']
    lease = config['lease_bridge']
    maturity = config['maturity_bridge']
    return {
        'research_cutoff': config['research_cutoff'],
        'assumption_set_id': config['assumption_set_id'],
        'scope': config['scope'],
        'coverage': {
            'displayed_ratio': r, 'minimum': m,
            'numerator_drop_to_equality_if_denominator_unchanged': coverage_headroom(r, m),
            'denominator_rise_to_equality_if_numerator_unchanged': r/m-1.0,
            'numerator_drop_to_equality_if_denominator_rises_5pct': coverage_headroom(r, m, .05),
            'nearest_0_1_rounding_illustration': {
                'assumption_verified': False, 'ratio_interval': '[1.55, 1.65)',
                'numerator_drop_interval': [coverage_headroom(1.55, m), coverage_headroom(1.65, m)],
                'upper_endpoint_excluded': True},
            'actual_unrounded_headroom': None,
            'noi_drop_threshold': None,
            'status': 'arithmetic_sensitivity_not_covenant_certificate',
            'definition': c,
        },
        'june_liquidity_constraint_only': capacity,
        '2027_facility_rolloff': {
            'committed_reduction': a['original_commitments'],
            'remaining_commitments': a['extended_commitments'],
            'extended_base_maturity': a['extended_base_maturity'],
            'extended_optional_maturity': a['extended_optional_maturity'],
            'extended_maturity_is_conditional': True,
            'june_cash_plus_2027_commitments_static': a['consolidated_unrestricted_cash']+a['extended_commitments'],
            'static_capacity_status': 'not_current_cash_not_2027_forecast'},
        'sale_bridge': {
            'completed_gross_sales': events['gateway']['gross_sales']+events['howard']['gross_sales'],
            'current_cash': None, 'net_sale_proceeds': None, 'debt_repayment': None,
            'disposed_noi': None, 'status': 'gross_sale_evidence_only',
            'identified_2027_current_abr_removed': lease['identified_glu_sold_abr'],
            'june_2027_abr_less_identified_sold_lease': lease['2027_anchor']-lease['identified_glu_sold_abr'],
            'complete_current_lease_roll': False, 'abr_is_noi': False},
        'current_cash_reconciliation': reconcile_cash(a['consolidated_unrestricted_cash'], config['current_post_june_flows']),
        'hollywood': events['hollywood'],
        'tender': {
            **tender, 'verified_completed_principal_reduction': 0.0,
            'observed_net_debt_change': None,
            'conditional_full_targets_net_debt_change_before_interest_fees': tender['cash_before_interest_fees_full_targets']-tender['target_2027']-tender['target_2028'],
            'cash_plus_unused_consumption_if_full_targets': tender['cash_before_interest_fees_full_targets'],
            'conditional_status': 'only_if_full_targets_settle_no_reallocation'},
        'maturity_2027_known_event_hpp_share': maturity['2027_anchor']+maturity['executed_hollywood_shift'],
        'actual_2027_funding_gap': same_basis_funding_gap(None, None, 'HPP_share', 'HPP_share'),
        'equity_denominator_evidence': config['equity_denominator_evidence'],
        'joint_nav_calibrated': False, 'executable_return_verified': False,
        'next_public_disclosure': config['next_public_disclosure'],
        'sources': config['sources'],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT/'config/hpp_liquidity_inputs.json')
    parser.add_argument('--output', type=Path, default=ROOT/'outputs/v2/hpp_liquidity_audit')
    args = parser.parse_args()
    raw = args.config.read_bytes()
    config = json.loads(raw)
    result = audit(config)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output/'liquidity_audit.json').write_text(json.dumps(result, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    manifest = dict(executed_at=datetime.now(timezone.utc).isoformat(),
                    research_cutoff=config['research_cutoff'],
                    config_sha256=hashlib.sha256(raw).hexdigest(),
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    assumption_set_id=config['assumption_set_id'],
                    expanded_security_return_grid=False)
    (args.output/'run_manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'observed_current_cash': None, 'fixed_denominator_sensitivity': result['coverage']['numerator_drop_to_equality_if_denominator_unchanged'], 'actual_2027_funding_gap': None}))


if __name__ == '__main__':
    main()
