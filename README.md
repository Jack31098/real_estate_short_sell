# Tech-core mortgage exposure screen

This project tests the hypothesis that AI-driven compression of high-wage tech
employment could reduce the location premium embedded in Seattle and Bay Area
housing. It starts from geography and asks which HMDA lenders originated the
most principal-residence mortgages in named tech-core places.

For the current project state and instructions for continuing on another computer,
see [HANDOFF.md](HANDOFF.md).

## First-stage scope

- Years: 2023–2025 HMDA snapshot data.
- Geography: selected Puget Sound and Bay Area counties.
- Loans: originated, first-lien, non-commercial, non-reverse, principal-
  residence, 1–4 unit home-purchase/refinance/cash-out refinance loans.
- Tract assignment: the Census tract interior point must fall inside the named
  incorporated-place polygon.
- Output: lender market share and geographic concentration, including a focused
  view of banks named in the imported conversation.

## Important limitation

HMDA mainly describes applications and originations. It does **not** say whether
the originating lender retained the loan, sold it, or still holds it today.
The first-stage ranking is therefore an origination-footprint screen, not a
balance-sheet credit-exposure estimate. CRE also requires a separate data path.

## Second-stage retained-balance proxy

`scripts/retained_exposure.py` narrows the first-stage tech-core originations to
two HMDA purchaser-type proxies: purchaser type 0 (not reported sold during the
reporting year) and a broader version that also includes purchaser type 8
(affiliate purchaser). It rolls those loans to 2025 year-end with scheduled
amortization and 4%/8%/15% CPR scenarios, then compares the result with a
bank-level tangible common equity proxy from FDIC BankFind data.

This is still a sensitivity model rather than a current-loan tape. Subsequent
sales, refinancings, participations, repurchases, and commercial real estate are
not observed in this stage.

## Run

Use the bundled Python environment supplied by Codex, or any Python environment
with pandas installed:

```powershell
python scripts/pipeline.py
python scripts/retained_exposure.py
python scripts/cre_capital_screen.py
python scripts/sec_filing_screen.py
python scripts/sec_disclosure_analysis.py
```

Raw downloads are cached under `data/raw/`. Derived tract mappings are written
under `data/derived/`. Reviewable analytical tables and `summary.json` are
written under `outputs/`.

The main stage-2 interpretation is in `outputs/second_stage_findings.md`.

`scripts/cre_capital_screen.py` adds a bank-wide Call Report screen for
construction, multifamily, owner-occupied nonresidential, and other
nonresidential loans. It reports CRE/TCE, observed asset-quality ratios, and
two standardized stress sensitivities. Because Call Reports do not identify
property locations, this stage measures capital sensitivity but not tech-core
geographic purity. Its interpretation is in
`outputs/third_stage_cre_findings.md`.

`scripts/sec_filing_screen.py` downloads and hashes the latest 10-K and 10-Q
for the seven public-bank candidates, and indexes geographic/property keywords.
`scripts/sec_disclosure_analysis.py` converts reviewed filing tables into
explicit geographic, portfolio, and credit metrics. Geographic disclosure
precision is preserved (county, issuer-defined region, state, or qualitative
footprint) rather than forcing unlike measures into a single ranking. The
Chinese interpretation is in `outputs/fourth_stage_sec_findings_zh.md`.

## Official sources

- HMDA Data Browser API: https://ffiec.cfpb.gov/documentation/api/data-browser/
- HMDA Data Browser: https://ffiec.cfpb.gov/data-browser/data/
- Census TIGERweb tracts: https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Tracts_Blocks/MapServer/0
- Census TIGERweb incorporated places: https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Places_CouSub_ConCity_SubMCD/MapServer/4
- FDIC BankFind Suite API: https://api.fdic.gov/banks/docs/
- SEC EDGAR submissions and filing archive: https://www.sec.gov/edgar/search-and-access
