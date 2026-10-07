"""Human-reviewed cells, not estimated exposures or automated document understanding.

Values are latest-to-oldest unless periods are explicit. Source hashes are locked
in config/v2_review_locks.json. Page numbers are PDF pages (not printed labels).
Adding a metric requires reading its table, units, denominator and footnotes.
"""
PERIODS = ['2026-06-30','2026-03-31','2025-12-31']


def facts():
    rows=[]
    def add(key,page,metric,values,unit='USD_million',scale=1,periods=None,
            portfolio='all',basis='reported',denominator='not_applicable',
            measurement='stock',ownership='consolidated',geography='all',notes=''):
        for period,value in zip(periods or PERIODS,values):
            rows.append(dict(source_key=key,page=page,metric=metric,value=value*scale,
                raw_value=value,scale=scale,unit=unit,period_end=period,portfolio=portfolio,
                basis=basis,denominator=denominator,measurement=measurement,ownership=ownership,
                geography=geography,notes=notes))
    w='wafd_2026q2_release'; c='colb_2026q2_release'
    for metric,values in {
        'cash':[676467,669799,734915], 'loans_net':[20017876,19966983,19848156],
        'acl_including_unfunded':[233831,224450,221039],
        'afs_fair_value':[4190263,4352258,4142285], 'htm_amortized_cost':[858261,745727,764794],
        'assets':[27596970,27568785,27285744], 'deposits':[20932075,21124151,21416970],
        'borrowings_including_junior':[3315697,3114548,2488411]}.items():
        add(w,2,metric,values,scale=.001)
    for metric,values in {'nim_gaap':[2.81,2.81,2.70],
        'nonaccrual_to_net_loans':[.64,.62,.96], 'delinquencies_to_net_loans':[.75,.78,1.07],
        'criticized_to_net_loans':[4.93,4.24,4.60], 'classified_to_net_loans':[2.59,2.60,2.94]}.items():
        add(w,2,metric,values,'percent',denominator='average earning assets' if metric=='nim_gaap' else 'net loans',
            measurement='quarter_annualized' if metric=='nim_gaap' else 'stock_ratio',
            notes='Criticized and classified overlap; never add. Delinquency definition differs from COLB buckets.')
    add(w,2,'tbv_per_share',[30.82,30.27,29.91],'USD_per_share',denominator='common shares')
    for metric,values in {'nii':[181338,177570,171111], 'provision_total':[11000,4000,3500],
        'noninterest_income':[24178,19813,20255], 'noninterest_expense':[110334,109857,105721],
        'pretax_income':[84349,83806,82301], 'deposit_interest_expense':[123079,125999,136214],
        'borrowing_interest_expense':[27708,21165,15171]}.items():
        add(w,7,metric,values,scale=.001,measurement='quarter_flow')
    add(w,19,'nib_deposits',[2646615,2577976,2692680],scale=.001)
    add(w,19,'uninsured_and_uncollateralized_deposits',[5326972,5333317,5607476],scale=.001,
        notes='Intersection: uninsured AND non-collateralized; not comparable to COLB uninsured total.')
    add(w,19,'uninsured_and_uncollateralized_pct',[25.4,25.2,26.2],'percent',denominator='total deposits')
    add(w,19,'borrowings_effective_maturity_within_3m',[1645000,1425000,800000],scale=.001,
        notes='Effective maturity; includes junior subordinated debentures.')
    add(w,17,'nonaccrual_loans',[127569,123859,191348],scale=.001)
    add(w,17,'net_chargeoffs',[1619,589,3681],scale=.001,measurement='quarter_flow')
    add(w,15,'acl_loans',[214831,201950,199539],scale=.001)
    add(w,16,'loans_amortized_cost',[20232707,20168933,20047695],scale=.001)
    add(w,20,'nii_shock_plus_100bp',[.9,-.1,-.2],'percent',basis='management sensitivity',
        denominator='modeled base NII',notes='Reported model output, not realized return. No balance sheet management action; horizon not verified.')
    add(w,20,'nii_shock_minus_100bp',[5.4,6.2,4.8],'percent',basis='management sensitivity',
        denominator='modeled base NII',notes='Reported model output; scenario assumptions belong to issuer. Horizon not verified.')
    add(w,5,'aoci',[48087],scale=.001)
    add('wafd_2026q2_deck',17,'securities_duration',[3.1],'years',notes='Issuer disclosed securities portfolio duration; not loan duration.')
    for metric,values in {
        'cash_due_from_banks':[648,577,511], 'interest_bearing_cash':[1121,1522,1869],
        'afs_fair_value':[11131,10915,11112], 'htm_amortized_cost':[17,18,18],
        'loans_gross_net_fees':[47166,47697,47776], 'loans_net':[46708,47238,47310],
        'assets':[65380,66027,66832], 'nib_deposits':[17218,17635,17419],
        'deposits':[52056,53489,54211], 'borrowings_excluding_junior':[4250,3400,3200],
        'repo_funding':[189,162,207], 'junior_fair_value':[339,333,338],
        'junior_other_amortized_cost':[97,97,97], 'aoci':[-310,-291,-233]}.items():
        add(c,8,metric,values,notes='Pacific Premier consolidated since 2025-08-31; all three quarters include acquisition.')
    add(c,9,'tbv_per_share',[19.22,19.03,19.11],'USD_per_share',denominator='common shares')
    for metric,values,denom in [('nim_tax_equivalent',[3.93,3.96,4.06],'average earning assets; 21% tax equivalent'),
        ('cost_ib_deposits',[1.96,2.04,2.08],'average interest bearing deposits'),
        ('cost_total_deposits',[1.32,1.39,1.40],'average total deposits'),
        ('loan_yield',[5.77,5.78,5.92],'average loans and leases')]:
        add(c,9,metric,values,'percent',denominator=denom,measurement='quarter_annualized')
    for metric,values in {'nii':[589,594,627], 'provision_total':[27,28,23],
        'noninterest_income':[88,83,90], 'noninterest_expense':[375,394,412],
        'pretax_income':[275,255,282], 'merger_expense':[9,24,39]}.items():
        add(c,6,metric,values,measurement='quarter_flow')
    for metric,values in {'nonaccrual_loans':[180,187,116], 'past_due_90plus_accruing':[88,74,82],
        'nonperforming_loans':[268,261,198], 'past_due_31_89':[125,168,94]}.items():
        add(c,13,metric,values,notes='NPL includes government guarantees; repurchase-eligible unrepurchased mortgages excluded.')
    for metric,values in {'nonperforming_to_gross_loans':[.57,.55,.41],
        'nonaccrual_to_gross_loans':[.38,.39,.24]}.items():
        add(c,13,metric,values,'percent',denominator='loans and leases net of fees before ACL')
    for metric,values in {'acl_loans':[458,459,466], 'acl_including_unfunded':[475,478,485]}.items():
        add(c,14,metric,values)
    add(c,14,'net_chargeoffs',[30,35,30],measurement='quarter_flow',notes='Positive denotes loss; PDF bridge displays subtraction.')
    for key,period,pagefund,pageoffice,pageduration,brokered,uninsured,duration,office_na,office_class in [
        ('colb_2026q2_deck','2026-06-30',27,26,28,978,20600,5.0,29.9,85.3),
        ('colb_2026q1_deck','2026-03-31',26,25,27,1595,20900,5.1,30.2,78.3),
        ('colb_2025q4_deck','2025-12-31',25,15,11,2355,19800,5.2,15.1,90.8)]:
        add(key,pagefund,'brokered_deposits',[brokered],periods=[period])
        # Disclosed in billions: preserve both original token and scale.
        add(key,pagefund,'uninsured_deposits',[uninsured/1000],scale=1000,periods=[period],notes='Rounded to 0.1 billion; not directly comparable to WAFD intersection.')
        add(key,pageduration,'afs_duration',[duration],'years',periods=[period])
        add(key,pageoffice,'office_nonaccrual',[office_na],portfolio='office deck',periods=[period])
        add(key,pageoffice,'office_classified',[office_class],portfolio='office deck',periods=[period])
    add('colb_2026q2_deck',26,'office_geography_pct',[15],'percent',portfolio='office deck',geography='Puget Sound',denominator='deck office portfolio',basis='excludes purchase accounting adjustments/deferred fees; reconciliation pending')
    add('colb_2026q2_deck',26,'office_geography_pct',[4],'percent',portfolio='office deck',geography='Bay Area',denominator='deck office portfolio',basis='excludes purchase accounting adjustments/deferred fees; reconciliation pending')
    add('colb_2026q2_deck',26,'office_contractual_maturity_2027_pct',[9],'percent',portfolio='office deck',denominator='deck office portfolio')
    add('colb_2026q2_deck',26,'office_repricing_2027_pct',[5],'percent',portfolio='office deck',denominator='deck office portfolio')
    add('colb_2026q2_deck',27,'fhlb_line_utilized',[4429],notes='Facility utilization, not a verified FHLB borrowing balance.')
    add('colb_2026q2_deck',27,'potential_liquidity',[25648],notes='Includes unused facilities and collateral; not cash.')

    h='hpp_2026q2_supplement'; k='krc_2026q2_supplement'
    for geo,occupied,leased,sqft,abr in [('North San Jose',59.9,59.9,2506253,68785163),
        ('Santa Clara',92.9,92.9,285764,11877579),('San Francisco',92.2,92.4,2139651,105228072),
        ('Seattle',74.7,74.7,2186798,51787080)]:
        add(h,17,'office_occupied_pct',[occupied],'percent',portfolio='in-service office',geography=geo,denominator='reported square feet')
        add(h,17,'office_leased_pct',[leased],'percent',portfolio='in-service office',geography=geo,denominator='reported square feet')
        add(h,17,'office_square_feet',[sqft],'sqft',portfolio='in-service office',geography=geo)
        add(h,17,'office_owner_share_abr',[abr],scale=.000001,portfolio='in-service office',geography=geo,ownership='HPP economic share',measurement='annualized_contract_rent',notes='Annualized base rent is not NOI or effective cash rent; excludes off-line repositioning space.')
    for metric,value,unit in [('new_cash_rent',44.47,'USD_sqft_year'),('renewal_cash_rent',61.65,'USD_sqft_year'),
        ('new_net_effective_rent',44.35,'USD_sqft_year'),('renewal_net_effective_rent',65.41,'USD_sqft_year'),
        ('new_ti_lc',113.95,'USD_sqft'),('renewal_ti_lc',4.06,'USD_sqft'),
        ('new_lease_term',208.5,'months'),('renewal_lease_term',45.6,'months'),
        ('same_space_cash_rent_change',-11.4,'percent')]:
        add(h,21,metric,[value],unit,portfolio='office leases executed in quarter',measurement='quarter_cohort',notes='Net effective rent nets annualized TI/LC; do not deduct them twice.')
    add(h,22,'lease_expiration_2027_abr',[66099838],scale=.000001,portfolio='expiring office lease schedule',ownership='HPP economic share',measurement='annualized_contract_rent',notes='June snapshot; subsequent Howard/Gateway sales require bridge. Not comparable denominator to page 17 in-service ABR.')
    add(h,22,'lease_expiration_2027_abr_pct',[13.9],'percent',portfolio='expiring office lease schedule',denominator='HPP share ABR in expiration schedule')
    add(h,14,'owner_share_debt',[2831042],scale=.001,ownership='HPP economic share',notes='Net share principal; includes extensions in maturity profile; not gross consolidated JV debt.')
    add(h,14,'debt_weighted_maturity',[2.1],'years',ownership='HPP economic share',notes='Includes extension options; stale after September modification.')
    for metric,value in [('secured_maturity_2026',535767),('secured_maturity_2027',103195),('unsecured_maturity_2027',400000)]:
        add(h,14,metric,[value],scale=.001,ownership='HPP economic share',
            notes='June maturity chart visually reviewed; principal including extensions. Historical baseline only; September Hollywood extension not yet applied.')
    add(k,9,'office_occupied_pct',[77.0,77.6,81.6],'percent',portfolio='stabilized office',denominator='reported square feet',
        notes='Composition changes with KOP 2; excluding KOP 2 June occupancy is 80.8%, not a same-store inference.')
    add(k,9,'office_leased_pct',[81.5,82.3,83.8],'percent',portfolio='stabilized office',denominator='reported square feet')
    add(k,9,'noi_reported',[180293,178403,176426],scale=.001,measurement='quarter_flow',notes='Issuer NOI, not same-store growth.')
    add(k,39,'debt_maturity_2026',[348102],scale=.001,notes='June baseline; footnote reports $200m October 2026 notes repaid in July.')
    add(k,39,'debt_maturity_2027',[249125],scale=.001,notes='June chart; includes scheduled amortization; not owner-share adjusted.')
    add(k,24,'new_lease_square_feet',[200978],'sqft',portfolio='executed non-short-term office leases',measurement='quarter_flow')
    add(k,24,'renewal_lease_square_feet',[134530],'sqft',portfolio='executed non-short-term office leases',measurement='quarter_flow')
    add(k,24,'second_gen_ti_lc',[67.00],'USD_sqft',portfolio='second generation',measurement='quarter_cohort')
    add(k,24,'second_gen_lease_term',[66],'months',portfolio='second generation',measurement='quarter_cohort')
    add(k,24,'cash_rent_change_all_signed',[6.1],'percent',portfolio='all second generation',measurement='quarter_cohort',denominator='expiring same-space cash rent')
    add(k,24,'cash_rent_change_vacant_le_12m',[15.6],'percent',portfolio='second generation vacant <=12 months',measurement='quarter_cohort',denominator='expiring same-space cash rent')
    add(k,27,'lease_expiration_2027_abr',[38087],scale=.001,portfolio='stabilized office',ownership='100% consolidated partnerships',measurement='annualized_contract_rent')
    add(k,27,'lease_expiration_2027_abr',[1668],scale=.001,portfolio='stabilized office',geography='Bay Area',ownership='100% consolidated partnerships',measurement='annualized_contract_rent')
    add(k,27,'lease_expiration_2027_abr',[5684],scale=.001,portfolio='stabilized office',geography='Seattle',ownership='100% consolidated partnerships',measurement='annualized_contract_rent')
    add(k,27,'lease_expiration_2027_abr_pct',[5.0],'percent',portfolio='stabilized office',denominator='stabilized in-place ABR',ownership='100% consolidated partnerships')
    for key,geo,vacancy,availability,direct,sublease,asking,absorption in [
        ('cbre_puget_2026q2','Puget Sound',28.2,28.1,24.3,3.8,46.78,64000),
        ('cbre_sf_2026q2','San Francisco',29.2,31.9,27.6,4.3,72.96,963980)]:
        for metric,value in [('total_vacancy',vacancy),('total_availability',availability),
                             ('direct_availability',direct),('sublease_availability',sublease)]:
            add(key,5,metric,[value],'percent',portfolio='CBRE surveyed office market',geography=geo,
                ownership='market inventory',denominator='survey net rentable area',notes='Availability differs from vacancy; direct availability is not direct vacancy.')
        add(key,5,'direct_asking_rent',[asking],'USD_sqft_year',portfolio='CBRE surveyed office market',geography=geo,
            ownership='market inventory',basis='full service gross annual asking; not effective rent')
        add(key,5,'net_absorption',[absorption],'sqft',portfolio='CBRE surveyed office market',geography=geo,
            ownership='market inventory',measurement='quarter_flow')
    return rows
