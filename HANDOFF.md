# Project handoff

Updated: 2026-10-05 (America/Los_Angeles)

## Purpose and current state

This is a research screen for the hypothesis that a decline in high-wage tech employment could pressure Seattle/Puget Sound and Bay Area housing and commercial real estate, then affect regional banks. It is **not** a current loan-level exposure database or a trading recommendation.

Four stages were completed on 2026-09-01 using 2023–2025 HMDA and FDIC data and bank filings through 2026 Q2:

1. `scripts/pipeline.py`: HMDA originations in named tech-core places, lender rankings, and geographic concentration.
2. `scripts/retained_exposure.py`: an originated-cohort balance proxy under purchaser, amortization and prepayment assumptions, compared with tangible common equity. Balance/TCE is not loss/TCE.
3. `scripts/cre_capital_screen.py`: bank-wide CRE composition, capital and stress screens.
4. `scripts/sec_filing_screen.py` and `scripts/sec_disclosure_analysis.py`: seven issuers' SEC filing index and manually reviewed geographic, portfolio, and credit metrics.

Read `outputs/fourth_stage_sec_findings_zh.md` for the pinned 2026 Q2 filing review and `outputs/first_stage_findings.md` / `outputs/second_stage_findings.md` for the recalculated 2023–2025 residential results. `outputs/quantitative_findings_zh.md` is an archived 2026-09-01 interpretation with superseded residential numbers. The source conversation excerpts imported on 2026-09-01 are in the two `chatgpt_shared_chat_*.txt` files. They contain only what was visible on the shared pages, not necessarily complete conversations.

The 2026 Q2 conclusion was to follow FSBW and COLB most closely, then CVBF, while preserving the geographic and disclosure limitations described in the report. This is a historical research conclusion; recheck filings and market data before using it for a current decision.

## What is in Git

Code, tests, configuration, stage reports, CSV/JSON analytical outputs, the tract score mapping, and the data manifest are versioned. `data/raw/` (about 130 MB on the original computer) and extracted SEC text under `data/derived/sec_text/` are intentionally ignored because they can be downloaded or derived again. The manifest records HMDA source URLs, row counts, and SHA-256 hashes. The SEC filing manifest in `outputs/sec_filings_manifest.csv` records filing URLs and hashes. Outputs preserve the last completed snapshot even before source downloads are rebuilt.

## Resume on another computer

```powershell
git clone https://github.com/Jack31098/real_estate_short_sell.git
cd real_estate_short_sell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m unittest discover -s tests
```

The tracked reports and tables can be read immediately after cloning. To rebuild from official sources, run these in order with internet access:

```powershell
python scripts/pipeline.py
python scripts/geography_sensitivity.py
python scripts/retained_exposure.py
python scripts/cre_capital_screen.py
python scripts/sec_filing_screen.py
python scripts/sec_disclosure_analysis.py
python scripts/office_intersection_bounds.py
```

The downloads may take time and official endpoints can change or rate-limit. `pipeline.py` downloads the six HMDA county/year files. The SEC screen downloads current latest filings to separate `sec_latest_*` discovery files, leaving the reviewed 2026 Q2 snapshot unchanged. `sec_disclosure_analysis.py` contains hand-reviewed figures tied to the 2025 10-K/2026 Q2 10-Q snapshot; **do not treat its output as refreshed merely because the SEC screen downloaded newer filings**. Re-review the filing tables and update that script, the reviewed manifest, and the source lock before regenerating the stage-4 conclusions for a new quarter.

Stage 4 checks `config/sec_review_sources.csv` against the reviewed manifest and fails if the accession, report date, URL or SHA-256 changes. It does not yet index exact source-table locations for every metric. The test command above collects all 37 tests as of this handoff update.

The geography coverage outputs under `outputs/` report selected mortgages excluded for invalid or unmatched census tracts by year, region and lender. The core-place weights are assumptions about residential originations only. `core_share_of_regional` uses a selected-county denominator, not the bank's whole balance sheet.

The 2023–2025 cached HMDA audit found 22 invalid-tract records among 334,851 qualifying selected-county mortgages, no valid but unmatched tracts, and no invalid/unmatched records for the observed candidate LEIs. This does not validate the city weights. In `outputs/residential_geography_sensitivity.csv`, FSBW leads WAFD in Puget Sound core origination dollars under the 0.7 baseline ($275.1m versus $157.8m), but WAFD leads under the 0.9 narrow threshold ($57.6m versus $19.4m) and when Seattle city is excluded ($81.2m versus $45.4m). These are origination rankings, not current retained exposure or expected losses.

On 2026-10-05, San Jose and Santa Clara city were added to `config/tech_core_places.json` at provisional score 0.7 and the first two residential stages were rerun from the six cached HMDA downloads plus fresh Census TIGERweb geography. Of 2,757 selected-county tracts, 203 now map to San Jose and 25 to Santa Clara; they previously mapped to "Outside named places." Across all lenders, the two cities add 21,573 qualifying loans and $22.212bn to the Bay Area core-origination denominator for 2023–2025. Candidate originations in the two cities total $60.45m (EWBC $52.55m, WAFD $4.00m, COLB $2.90m, HMST $1.00m). EWBC's Bay Area core-originated amount rises from $91.855m in the legacy-city scenario to $144.405m with both cities included, while its core market share falls from 0.326% to 0.287% because the regional denominator grows more. Its modeled 2025 base cohort balance/TCE rises from 1.62% to 2.22%. `outputs/candidate_originations_by_place_2023_2025.csv` shows city/year/lender detail, and `residential_geography_sensitivity.csv` retains a `legacy_exclude_new_cities` comparison. The 0.7 city scores and threshold are still manual hypotheses, not empirically fitted income or employment weights.

## Open questions and next work

- Establish quarterly monitoring for FSBW, COLB, and CVBF, distinguishing acquisition effects from organic credit deterioration.
- Seek more precise collateral geography or loan-level evidence for FSBW; its public disclosure identifies a primary market but does not quantify tech-core loans.
- Keep HMDA origination share separate from retained, current balance-sheet exposure. Current retained-loan figures are sensitivity proxies.
- Recheck property-type mix, maturities, collateral values, nonaccruals, reserves, and capital with the latest filings before extending the short thesis.
- Add effective-dated LEI/FDIC certificate/parent and acquisition mappings before presenting a pro forma current-group ranking; current screens are historical entity observations.
- Build a separate office-property branch with property ownership shares, lease expirations, tenant mix, debt, lender, and scenario valuation. Marginal CRE-by-region and office-by-property totals do not identify their intersection.
- `outputs/office_intersection_bounds.csv` now gives mathematical bounds and an independence-assumption scenario for COLB, CVBF, and EWBC. COLB's regional office balance is still unobserved: its Puget + Bay Area CRE is $5.635bn, bank-wide office CRE is $3.559bn, and bank-wide CRE is $27.009bn; the intersection can range from $0 to $3.559bn. The $0.743bn independence scenario is not an observation.
- Add a credit-loss-to-capital bridge that treats allowances, ongoing earnings, tax and regulatory capital consistently; the existing standardized CRE haircuts are comparative scenarios, not AI-loss forecasts.

See `README.md` for methodology, limitations, and official source links.
