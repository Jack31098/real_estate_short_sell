# Second-stage residential origination-cohort balance proxy

## Headline result

The purchaser-type screen materially reduces the first-stage origination footprint. The table below compares modeled 2025-12-31 balances in named tech-core places with bank-level tangible common equity (TCE) proxies.

| Ticker | Core originations | Strict base balance | Expanded base balance | Expanded / TCE | Capital date |
|---|---:|---:|---:|---:|---:|
| FSBW | $275.1M | $81.4M | $81.4M | 24.92% | 20251231 |
| HMST | $197.0M | $68.9M | $68.9M | 13.06% | 20250630 |
| WAFD | $161.8M | $133.5M | $133.5M | 5.11% | 20251231 |
| EWBC | $195.6M | $170.6M | $170.6M | 2.22% | 20251231 |
| COLB | $184.2M | $104.7M | $104.7M | 1.79% | 20251231 |
| BCML | $0 | $0 | $0 | 0.00% | 20251231 |
| BMRC | $0 | $0 | $0 | 0.00% | 20251231 |
| CVBF | $0 | $0 | $0 | 0.00% | 20251231 |

Strict means HMDA purchaser type 0: an originated loan was not reported as sold during that reporting calendar year. Expanded adds purchaser type 8, sale to an affiliate. Type 8 does not establish that the bank subsidiary in the TCE denominator holds the loan. Neither field proves that the loan remained on a consolidated balance sheet at 2025 year-end. The observed candidate sample contains 0 type 8 loans.

## Model assumptions

- Scope is unchanged from stage 1: principal-residence, first-lien, 1–4 unit, non-commercial purchase/refinance loans whose Census tract point falls in a place with a tech score of at least 0.7.
- Each loan is assumed to originate at the midpoint of its HMDA year. Scheduled amortization uses reported rate and term; missing/invalid values use 6.5% and 360 months.
- CPR scenarios are 4%, 8% (base), and 15%. This is a sensitivity analysis, not a loan-level servicing model.
- Bank TCE proxy = FDIC total equity capital minus perpetual preferred stock minus intangible assets. FDIC amounts are converted from thousands of dollars.
- HomeStreet's last 2025 FDIC financial report is 2025-06-30 and its current FDIC status is inactive. Its ratio is historical/entity-specific and not directly comparable with the surviving year-end banks.

## What this does and does not establish

This is a sharper residential screening metric than raw originations, but it is still not current loan holdings. HMDA lacks stable loan identifiers across years; refinancings, subsequent sales, repurchases, participations, charge-offs, and exact origination dates are unobserved. Most importantly, CRE and construction lending are outside this residential model and require Call Report/SEC portfolio data.

The proxy can overstate exposure through later sales and repeat refinancing originations, or understate it by excluding pre-2023 cohorts, purchased loans and acquired portfolios. It is not a conservative bound. Balance / TCE is not loss / TCE: losses also depend on defaults, collateral recoveries, reserves, earnings and taxes.

## Reproducible outputs

- `candidate_retained_exposure_total.csv`: bank ranking across both observed regions.
- `candidate_retained_exposure_by_region.csv`: same model split by region.
- `candidate_purchaser_mix_2023_2025.csv`: purchaser-type audit trail.
- `fdic_capital_2025.csv`: latest 2025 bank capital record used for each FDIC certificate.

## Official sources

- HMDA data and filing guides: https://ffiec.cfpb.gov/data-publication/
- HMDA Data Browser API: https://ffiec.cfpb.gov/documentation/api/data-browser/
- FDIC BankFind Suite API documentation: https://api.fdic.gov/banks/docs/
