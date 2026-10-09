# Project handoff

Updated: 2026-10-09 (America/Los_Angeles)

## Latest execution: HPP cash/covenant evidence audit (2026-10-09)

User reprioritized: freeze the existing 456 security-return scenarios. First close
cash/debt/lease/NOI and contractual constraints; then use one 2027-2030 economic
state for common value and preferred cash dividends/arrears/recovery plus reverse
NAV; third obtain actual broker execution evidence. Missing locate quotes do not
block the first two public-source workstreams. No executable returns are claimed.

Start with `outputs/v2/hpp_liquidity_audit/hpp_liquidity_audit.html` and
`cash_covenant_audit_zh.md`. This is a Priority 1 evidence slice, not a closed
October balance sheet, complete funding-gap model or calibrated joint NAV.

- Cutoff: October 9, 12:10:59 PDT / 15:10:59 EDT, before scheduled tender expiry.
  Tender accepted amounts, settlement and cash/revolver split remain unknown;
  verified completed reduction is zero, not a forecast of zero final acceptance.
- Located Sep 10, 2025 Fifth Modification Exhibit A; read contract definitions and
  visually checked redline pages/images 165-166, and Q2 supplemental page 15.
  FCC is trailing 12 months, contract Adjusted EBITDA/Fixed Charges, with the Q2
  pro-forma denominator window tied to 2025 Projections. Filled compliance
  certificate and those projections were not obtained. The 1.6x display is rounded.
  6.25% numerator sensitivity at fixed denominator is NOT a NOI default threshold.
- Liquidity >=125m applies when revolving COMMITMENTS >600m. Issuer press-release
  borrowings wording conflicts with signed contract/8-K; use contract. June cash
  80.760m plus unused 795.250m gives 876.010m from precise components; not current
  spendable cash. No-default/pro-forma conditions restrict draws. Commitments fall
  by 333.250m on Dec 21, 2026; 2027 remaining 462m. Extended base maturity Dec 2028;
  Dec 2029 requires two conditional six-month options. Unencumbered NOI coverage
  minimum steps from 1.75x back to 2.0x after 2026.
- Financial covenants fall under 11.1(b)(i); do not import (b)(ii)'s general 30-day
  cure. No automatic equity cure verified. Any EOD restricts upstream distributions
  under 10.1(i); lender remedies/waiver are conditional, not observed default.
- Gross Q3 sales 90.5m, but net proceeds, actual repayment and disposed NOI remain
  unreconciled. ABR removed for Glu 5.637567m is not NOI. Hollywood JV reserve 20m
  and excess-cash sweep matter for upstream liquidity; actual HPP cash contribution
  unknown. Known-event 2027 HPP-share maturity 1033.962m is not a matched funding gap.
- Found pre-funded warrants: 10.223269m in Q2 EPS footnote. Listed common alone is
  insufficient; Q2 weighted-average common/OP units 65.684497m is not current fully
  diluted units. Reconcile OP/awards/JV/parent claims before per-share reverse NAV.
- Added a stdlib-only audit with unknown-cash and basis-match gates, 10 financial
  tests (86 total passed), source references, cutoff, input/code hashes, and standalone HTML/Canvas. HTML controls/console/layout and Canvas types checked.
  Direct source-download 403 attempts are recorded; web reads have no invented raw
  hash. Existing PDF hashes retained. Previous 456 scenarios and old outputs unchanged.

Reproduce: `python scripts/hpp_liquidity_audit.py`; `python -m unittest discover -s tests`.
Next: tender results/actual Oct 14 settlement, public lease/property debt/TI-LC and
unit/claim mapping, then Q3 results scheduled Nov 5. Do not wait for broker data to
continue those. Do not add subjective price/yield targets or probabilities.
No automation or broker transaction was created.

## Previous execution: HPP common versus callable Series C (2026-10-09)

Start with `outputs/v2/hpp_security_comparison/hpp_security_comparison.html`.
This advances the HPP priority within V2.1; it does not replace the earlier
credit/property execution or claim a completed property NAV/capital-structure model.

- Verified the issuer's Series C cumulative, perpetual terms: $25 liquidation
  preference, $1.1875 annual dividend, optional ordinary call from November 16,
  2026. First call date is not mandatory redemption or maturity.
- Same-date October 8 closes: HPP $11.88, Series C $14.46. Preferred close/8100
  volume confirmed in two downloaded vendors. Intraday October 9 quotes and stale
  search-cache prices are excluded. Borrow inventory, fee and bid/ask remain unknown.
- Executed 456 short-cost scenarios, yield repricing and conditional liquidation
  allocations. No probabilities, expected return, absolute NAV or joint terminal
  economic-state mapping were estimated. D/y applies only to uninterrupted
  no-call perpetuities. Suspended-dividend terminal quotes are exogenous; arrears
  are recorded, not erased. Returns use equal initial notional, not margin capital.
- One-year illustration: common $8 exit/3% fee gives 29.7% net. Preferred 12%
  required yield/5% fee/full dividends gives 18.4%; 16% gives 35.5%. Matching the
  common scenario requires preferred below $8.26 (~14.38% uninterrupted yield).
  These are conditional examples, not evidence the preferred is mispriced.
- Re-downloaded Q2 supplemental and tender PDFs: hashes match the prior archive;
  visually reviewed pages 8/12/13/15. Kept consolidated versus ownership-share
  debt/NOI/cash distinct. Absolute per-share NAV remains gated on current common,
  OP unit/award dilution and the parent-level claims/property map.
- Reproduced the old core path from tracked panels in an isolated local clone;
  all 63 prior tests passed. New 13 financial/gating tests also passed, total 76.
  HTML desktop/mobile and controls were verified; Canvas source type-check passed.
- Tender is still unverified/unsettled for this research snapshot: observed debt
  reduction remains zero. $98/$99.125 are issuer tender offers, NOT observed bond
  trading prices. Cash/revolver funding of full targets reduces net debt only by
  the $2.875m purchase discount before accrued interest/fees, not $200m.

Reproduce this slice: `python scripts/hpp_security_comparison.py` followed by
`python -m unittest discover -s tests`. Config and source references are in
`config/hpp_security_inputs.json`; source byte metadata and all analytical results
are under `outputs/v2/hpp_security_comparison/`. A fresh portable replay of the older
core pass remains `python scripts/core_path.py --from-panels` (on Windows use Python
UTF-8 mode, e.g. `python -X utf8 ...`). Older tracked observations/reports were not
overwritten by this slice.

Next: obtain tender acceptance/settlement and cash/revolver changes, rebuild the
post-disposition lease/NOI/cash bridge, and constrain 2027-2030 TI/LC, refinance,
dilution and liquidation scenarios jointly. Broker locate/fees are needed only
for an executable short comparison; public-source research can continue now.

## Remote continuation package (2026-10-09)

This delivery includes the comparison script, locked input configuration, 13 new
unit tests, full scenario outputs, source retrieval/validation manifests, and
standalone HTML/Canvas reports. The run manifest records the execution base
`5a92ea869d04adef86b76e340649a38cb049597c`; it is provenance for the analysis,
not the eventual delivery commit. Prior tracked research snapshots are preserved.

Raw downloaded documents remain ignored under `data/raw/` and are not included
in the remote delivery. Source URLs, retrieval metadata and document hashes are
included so a fresh checkout can retrieve and verify them. The comparison itself
runs from the tracked configuration without those raw caches. Historical pricing
and findings are an October 8/9 snapshot; refresh evidence before trading use.

Continue first with tender settlement evidence and the post-disposition cash/NOI
bridge described above. No additional user input is required for public-source
research. Actual broker locate availability and fees are required before calling
any modeled short scenario executable.

## Previous execution: four research priorities (2026-10-07)

Start with `outputs/v2/core_path_report_zh.md`. The framework remains V2.1;
the execution order changed to targeted history + property liquidity/price +
COLB refinance scenarios + HPP known-event bridge. Do not make complete document
backfill or matched controls a prerequisite. Do not start LODES/HMDA/bulk CMBS yet.

Actually run in this pass:

- 40 original-quarter documents, 538 bank observations, 2024Q1–2026Q2.
  `core_history.py` extracts current columns only; `core_filing_history.py`
  sums COLB rating rows with whole-portfolio reconciliations and verified filing
  dates. COLB 2025Q3 filed November 6 (signature November 5 is not publication).
- Six counties × 32 months of Redfin series, FHFA metro repeat-sales and NWMLS
  September King tables. Separate LiquidityStress and CollateralStress vectors,
  no weighted city score. Santa Clara, San Jose and Pierce explicitly covered.
- 576 COLB hypothetical refinance cases. Every output is scenario, not loss.
  Average all-office LTV 57%, nonowner DSCR 1.76 and 2027 maturity9% do not describe
  an observed joint cohort; do not multiply the latter by the $3.559bn filing book.
- HPP ownership-share June debt + executed Hollywood extension: 2027 $1,033.962m
  versus $503.195m at June. Gross JV loan remains $1.1bn. Announced tender reduces
  observed debt by zero; gross sales are not assumed to repay debt. Identified
  Glu/875 Howard sale adjusts June2027 current ABR $66.100m to $60.462m, but the
  complete current rent roll and post-June net debt still need reconciliation.
- KRE-only / KRE+rates / legacy KRE+SPY+rates regressions, 126/252 pre-event days.
  Matched ex-target basket deliberately missing until matched controls exist.
- Five rendered/inspected PNG figures and 63 passing tests.

Main inference: observed residential exit stress and conditional 2027 refinance
fragility are real research findings; an unpriced bank-loss thesis is unproven.
HPP rollover first, COLB cohort next, WAFD funding/merger as a separate question;
KRC remains comparative evidence. Preserve SF residential strength and CBRE
positive office absorption as counterevidence.

### Reproduce this pass on another computer

```powershell
python -m pip install -r requirements.txt
python scripts/core_path.py --from-panels
python -m unittest discover -s tests
```

This uses tracked extracted panels for scenarios, events, figures and the report.
It does NOT re-download or re-extract the ignored original source archive. The
original observations keep their historical execution versions. For a raw-cache
rebuild, run `python scripts/core_path_sources.py`, restore the property downloads
identified in `outputs/v2/*_source.json`, and run `python scripts/core_path.py`.
The pipeline checks raw hashes against the pinned metadata. Bank mirror PDFs
were fetched through official IR. The older baseline HPP source metadata and
market panels are tracked and remain available to the new pass.

Redfin download route: https://www.redfin.com/news/data-center/downloads/;
Housing Market Tracker -> All Metrics (14), Monthly, Counties, All Counties,
Jan2024–Aug2026; separately Price Drops with the same date/geography filters.
Original filenames are `redfin_housing_market_monthly_all_counties_2024_Jan_to_2026_Aug.csv`
and `redfin_price_drops_monthly_all_counties_2024_Jan_to_2026_Aug.csv`. Copy matching
bytes to the content-addressed `raw_path` in each metadata file. Later downloads
may be revised: preserve a new vintage, do not silently replace the old hash.
FHFA and NWMLS URLs are in their metadata files. Property observations use
retrieval time as availability; no September historical-as-of claim is allowed.
Unlabelled Redfin columns retain an explicit seasonal-adjustment uncertainty;
headlines use same-month YoY and the vendor's raw levels, not an inferred MoM signal.

Unfinished target data: WAFD first six quarters' classified (only substandard in
the original releases; SEC direct requests still403), complete bank funding/floor
fields, COLB 2027 loan-cohort joint features, HPP actual tender settlement/funding,
remaining sold leases and current cash/debt reconciliation. Original-quarter
core series do not make all V2 batches complete. Next obtain these decisive cells,
then match low-tech controls; no new framework is needed.

## Archived earlier execution: V2 first slice

Start with `outputs/v2/research_report_zh.md`. The first V2 pipeline has actually
run: 22 source documents; three consecutive WAFD/COLB quarters; six daily market
series; pre-event 252/126-session factor regressions; four dated four-layer
comparisons; HPP/KRC owner leasing/debt baselines; and CBRE Puget/San Francisco
office market pilots. HPP North San Jose and Santa Clara are separate rows.

Verified price returns: WAFD September -16.30%, September 4–30 -17.55%; COLB
September -3.51%. WAFD's September 8 daily factor residual is about -4.52pp
(252-session fit), a descriptive residual rather than causal attribution.
Historical September 1 snapshots exclude the September 7 merger announcement.
HPP September extension/sales and October tender are separate dated events;
the June debt/lease schedules are explicitly historical, not a current net wall.

Rebuild V2 after installing requirements (includes pypdf and Windows tzdata):

```powershell
python scripts/research_sources.py
python scripts/market_replay.py --end 2026-10-06
python scripts/research_v2.py
python -m unittest discover -s tests
```

`reviewed_v2_facts.py` stores human-reviewed source cells. `v2_review_locks.json`
pins bytes and document identities. A replaced/missing locked source fails closed;
do not automatically update locks to make a test pass. The raw cache is ignored,
while all reports, tables, source manifests and code/configuration are tracked.
Old SEC cache retrieval timestamps are unknown, explicitly null. SEC direct
downloads currently return 403; issuer IR supplied the key releases/decks. Another
computer can read outputs immediately; a full source rebuild still depends on
access to the locked SEC documents. Do not claim an unavailable raw archive was
transferred by Git. `run_manifest.json` and `code_manifest.json` identify the
executed source tree, market input hashes, package versions and observation IDs.

**Acceptance still pending:** full 2024-onward filing backfill; matched control
feature/tech-exposure verification; all funding/loan-floor fields; property
transaction/DOM/employment histories; complete owner/tenant/loan mapping; refi,
collateral and capital bridge. The control registry is a retrospective screening
queue, not valid matched controls. Property LiquidityStress remains null; credit
is a separate observed vector without a composite score. Old manual city weights
remain sensitivity assumptions and are not used as validated AI exposure.

The first slice's work order has been superseded by the latest execution above.
Keep supportive and contrary evidence together. Remaining acceptance requirements
are in `IMPLEMENTATION_PLAN.md`; do not mark batches 1–2 complete yet.

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

Stage 4 checks `config/sec_review_sources.csv` against the reviewed manifest and fails if the accession, report date, URL or SHA-256 changes. Legacy stage 4 does not index exact source-table locations for every metric; V2 adds PDF pages/table identifiers. The test command now collects 56 tests, including the new V2 contract, scope and date/market leakage tests.

The geography coverage outputs under `outputs/` report selected mortgages excluded for invalid or unmatched census tracts by year, region and lender. The core-place weights are assumptions about residential originations only. `core_share_of_regional` uses a selected-county denominator, not the bank's whole balance sheet.

The 2023–2025 cached HMDA audit found 22 invalid-tract records among 334,851 qualifying selected-county mortgages, no valid but unmatched tracts, and no invalid/unmatched records for the observed candidate LEIs. This does not validate the city weights. In `outputs/residential_geography_sensitivity.csv`, FSBW leads WAFD in Puget Sound core origination dollars under the 0.7 baseline ($275.1m versus $157.8m), but WAFD leads under the 0.9 narrow threshold ($57.6m versus $19.4m) and when Seattle city is excluded ($81.2m versus $45.4m). These are origination rankings, not current retained exposure or expected losses.

On 2026-10-05, San Jose and Santa Clara city were added to `config/tech_core_places.json` at provisional score 0.7 and the first two residential stages were rerun from the six cached HMDA downloads plus fresh Census TIGERweb geography. Of 2,757 selected-county tracts, 203 now map to San Jose and 25 to Santa Clara; they previously mapped to "Outside named places." Across all lenders, the two cities add 21,573 qualifying loans and $22.212bn to the Bay Area core-origination denominator for 2023–2025. Candidate originations in the two cities total $60.45m (EWBC $52.55m, WAFD $4.00m, COLB $2.90m, HMST $1.00m). EWBC's Bay Area core-originated amount rises from $91.855m in the legacy-city scenario to $144.405m with both cities included, while its core market share falls from 0.326% to 0.287% because the regional denominator grows more. Its modeled 2025 base cohort balance/TCE rises from 1.62% to 2.22%. `outputs/candidate_originations_by_place_2023_2025.csv` shows city/year/lender detail, and `residential_geography_sensitivity.csv` retains a `legacy_exclude_new_cities` comparison. The 0.7 city scores and threshold are still manual hypotheses, not empirically fitted income or employment weights.

## Open questions and next work

The execution order, data contracts and acceptance criteria are in [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). The first working slice and reproduced WAFD windows are summarized above; full batch acceptance and the later refi/capital/AI models remain pending.

V2.1 (`2026-10-07-r2`) requires funding/rates alongside credit. Initial panels, the four-layer report and the exact-scope gate are implemented. Dual states are separate outputs, not statistical independence: property liquidity still lacks the data needed for a state estimate. Sublease market data and owner effective rents are ingested, while market concessions and valid matched controls remain missing. BXP/FSBW are business references, not automatically AI controls.

- Establish quarterly credit and funding/earnings panels, distinguishing acquisition effects from organic changes and keeping improvement and deterioration evidence together. WAFD's July 16 earnings release reports criticized/net loans rising from 4.24% to 4.93% between March and June 2026 despite classified/net loans moving from 2.60% to 2.59%.
- Seek more precise collateral geography or loan-level evidence for FSBW; its public disclosure identifies a primary market but does not quantify tech-core loans.
- Keep HMDA origination share separate from retained, current balance-sheet exposure. Current retained-loan figures are sensitivity proxies.
- Recheck property-type mix, maturities, collateral values, nonaccruals, reserves, and capital with the latest filings before extending the short thesis.
- Add effective-dated LEI/FDIC certificate/parent and acquisition mappings before presenting a pro forma current-group ranking; current screens are historical entity observations.
- Build a separate office-property branch with property ownership shares, lease expirations, tenant mix, debt, lender, and scenario valuation. Marginal CRE-by-region and office-by-property totals do not identify their intersection.
- `outputs/office_intersection_bounds.csv` gives mathematical bounds using only the currently ingested margins. The 2026-10-07 source review identified COLB's Q2 earnings presentation, slide 26, reporting office geography (Puget Sound 15%, Bay Area 4%). The previous claim that the intersection is wholly unavailable was too broad. Reconcile the deck's office portfolio basis with the 10-Q before publishing a derived regional dollar amount; the existing $0–3.559bn bound and $0.743bn independence scenario are incomplete-source results, not the best available disclosure. See the V2 plan for the original document and the reconciliation gate.
- Add a credit-loss-to-capital bridge that treats allowances, ongoing earnings, tax and regulatory capital consistently; the existing standardized CRE haircuts are comparative scenarios, not AI-loss forecasts.

See `README.md` for methodology, limitations, and official source links.
