# Project handoff

Updated: 2026-10-05 (America/Los_Angeles)

## Purpose and current state

This is a research screen for the hypothesis that a decline in high-wage tech employment could pressure Seattle/Puget Sound and Bay Area housing and commercial real estate, then affect regional banks. It is **not** a current loan-level exposure database or a trading recommendation.

Four stages were completed on 2026-09-01 using 2023–2025 HMDA and FDIC data and bank filings through 2026 Q2:

1. `scripts/pipeline.py`: HMDA originations in named tech-core places, lender rankings, and geographic concentration.
2. `scripts/retained_exposure.py`: retention and amortization proxies compared with tangible common equity.
3. `scripts/cre_capital_screen.py`: bank-wide CRE composition, capital and stress screens.
4. `scripts/sec_filing_screen.py` and `scripts/sec_disclosure_analysis.py`: seven issuers' SEC filing index and manually reviewed geographic, portfolio, and credit metrics.

Read `outputs/fourth_stage_sec_findings_zh.md` first for the latest synthesis. Earlier stage reports are `outputs/first_stage_findings.md`, `outputs/second_stage_findings.md`, `outputs/third_stage_cre_findings.md`, and `outputs/quantitative_findings_zh.md`. The source conversation excerpts imported on 2026-09-01 are in the two `chatgpt_shared_chat_*.txt` files. They contain only what was visible on the shared pages, not necessarily complete conversations.

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
python scripts/retained_exposure.py
python scripts/cre_capital_screen.py
python scripts/sec_filing_screen.py
python scripts/sec_disclosure_analysis.py
```

The downloads may take time and official endpoints can change or rate-limit. `pipeline.py` downloads the six HMDA county/year files; the SEC screen downloads current latest filings and will therefore change its manifest over time. `sec_disclosure_analysis.py` contains hand-reviewed figures tied to the 2025 10-K/2026 Q2 10-Q snapshot; **do not treat its output as refreshed merely because the SEC screen downloaded newer filings**. Re-review the filing tables and update that script before regenerating the stage-4 conclusions for a new quarter.

## Open questions and next work

- Establish quarterly monitoring for FSBW, COLB, and CVBF, distinguishing acquisition effects from organic credit deterioration.
- Seek more precise collateral geography or loan-level evidence for FSBW; its public disclosure identifies a primary market but does not quantify tech-core loans.
- Keep HMDA origination share separate from retained, current balance-sheet exposure. Current retained-loan figures are sensitivity proxies.
- Recheck property-type mix, maturities, collateral values, nonaccruals, reserves, and capital with the latest filings before extending the short thesis.

See `README.md` for methodology, limitations, and official source links.
