#!/usr/bin/env python3
"""Turn reviewed SEC 10-K/10-Q disclosures into comparable screening metrics.

The input values below are curated from issuer tables in the cached filings.
They remain separate from machine-extracted keyword hits so that every ratio has
an explicit numerator, denominator, disclosure date, and geographic precision.
Dollar values are millions unless stated otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
MANIFEST = OUTPUT_DIR / "sec_filings_manifest.csv"
REVIEW_SOURCES = PROJECT_ROOT / "config" / "sec_review_sources.csv"
SOURCE_KEYS = ["ticker", "form"]
LOCKED_FIELDS = ["report_date", "accession", "document_url", "sha256"]


def pct(numerator: float, denominator: float) -> float:
    return 100.0 * numerator / denominator


def validated_manifest(
    manifest_path: Path = MANIFEST,
    review_path: Path = REVIEW_SOURCES,
    manifest_override: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Refuse to attach reviewed figures to a different SEC filing snapshot."""
    manifest = (
        manifest_override.astype("string")
        if manifest_override is not None
        else pd.read_csv(manifest_path, dtype="string")
    )
    reviewed = pd.read_csv(review_path, dtype="string")
    required = set(SOURCE_KEYS + LOCKED_FIELDS)
    if not required.issubset(manifest.columns) or not required.issubset(reviewed.columns):
        raise ValueError(f"SEC source lock requires columns: {sorted(required)}")
    for label, frame in (("manifest", manifest), ("review lock", reviewed)):
        if frame[SOURCE_KEYS].isna().any().any() or frame.duplicated(SOURCE_KEYS).any():
            raise ValueError(f"SEC {label} has missing or duplicate ticker/form keys")
        if frame[LOCKED_FIELDS].isna().any().any():
            raise ValueError(f"SEC {label} has missing source metadata")
    actual = manifest.set_index(SOURCE_KEYS)[LOCKED_FIELDS].sort_index()
    expected = reviewed.set_index(SOURCE_KEYS)[LOCKED_FIELDS].sort_index()
    if not actual.equals(expected):
        raise ValueError(
            "SEC filing manifest differs from reviewed accessions, dates, URLs or hashes; "
            "review the new filing tables and update curated metrics and source lock together"
        )
    return manifest


def filing_urls() -> dict[tuple[str, str], str]:
    manifest = validated_manifest()
    return {
        (row.ticker, row.form): row.document_url
        for row in manifest.itertuples(index=False)
    }


def geo_rows(urls: dict[tuple[str, str], str]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    def add(
        ticker: str,
        form: str,
        report_date: str,
        geography: str,
        precision: str,
        numerator: float | None,
        denominator: float | None,
        denominator_name: str,
        interpretation: str,
    ) -> None:
        rows.append(
            {
                "ticker": ticker,
                "form": form,
                "report_date": report_date,
                "geography": geography,
                "precision": precision,
                "exposure_usd_m": numerator,
                "denominator_usd_m": denominator,
                "denominator_name": denominator_name,
                "exposure_pct": (
                    pct(numerator, denominator)
                    if numerator is not None and denominator is not None
                    else None
                ),
                "interpretation": interpretation,
                "document_url": urls[(ticker, form)],
            }
        )

    add(
        "FSBW", "10-K", "2025-12-31", "Seattle-Tacoma-Bellevue primary market",
        "market-footprint only", None, None, "not disclosed",
        "High qualitative Puget Sound purity, but the filing does not allocate loan balances by county or metro.",
    )

    wafd_total = 21633.392
    add(
        "WAFD", "10-Q", "2026-06-30", "Washington",
        "state upper bound", wafd_total * 0.274, wafd_total, "total gross loans",
        "Washington is material, but a state total is not a Seattle-tech-core measure.",
    )

    bmrc_cre = 1676.470
    add(
        "BMRC", "10-K", "2025-12-31", "San Francisco + San Mateo + Santa Clara counties",
        "county", 188.372 + 40.511 + 37.682, bmrc_cre, "commercial real estate loans",
        "Strict three-county proxy; true city/tract tech-core exposure is smaller.",
    )
    add(
        "BMRC", "10-K", "2025-12-31", "Strict three counties + Alameda",
        "county broad", 188.372 + 40.511 + 37.682 + 201.558, bmrc_cre,
        "commercial real estate loans",
        "Broad Bay-relevant proxy; Marin and Sonoma remain the two largest disclosed CRE counties.",
    )

    bcml_total = 2074.704
    bcml_re = 169.719 + 345.008 + 478.478 + 901.277 + 10.143
    add(
        "BCML", "10-Q", "2026-06-30", "San Francisco Bay Area",
        "issuer-defined region", 392.416, bcml_total, "total loans",
        "Direct regional disclosure; roughly four-fifths of loans are outside the Bay Area.",
    )
    add(
        "BCML", "10-Q", "2026-06-30", "San Francisco Bay Area real estate",
        "issuer-defined region", 365.915, bcml_re, "real-estate loan categories",
        "Sum of disclosed Bay Area residential, multifamily, owner-occupied and non-owner CRE balances.",
    )

    cvbf_total = 12017.055
    cvbf_cre = 8983.934
    add(
        "CVBF", "10-Q", "2026-06-30", "Santa Clara + San Mateo",
        "county", 1080.754 + 580.453, cvbf_total, "total loans",
        "Strict Silicon Valley county proxy after the Heritage Commerce acquisition.",
    )
    add(
        "CVBF", "10-Q", "2026-06-30", "Santa Clara + San Mateo CRE",
        "county", 634.499 + 309.788, cvbf_cre, "commercial real estate loans",
        "Strict county CRE proxy; Los Angeles and Central Valley/Sacramento are much larger.",
    )

    colb_cre = 27009.0
    add(
        "COLB", "10-Q", "2026-06-30", "Puget Sound",
        "issuer-defined region", 3895.0, colb_cre, "commercial real estate loans",
        "Direct regional CRE disclosure; Southern California is more than twice as large.",
    )
    add(
        "COLB", "10-Q", "2026-06-30", "Bay Area",
        "issuer-defined region", 1740.0, colb_cre, "commercial real estate loans",
        "Direct regional CRE disclosure.",
    )
    add(
        "COLB", "10-Q", "2026-06-30", "Puget Sound + Bay Area",
        "two broad regions", 3895.0 + 1740.0, colb_cre, "commercial real estate loans",
        "Combined upper-bound proxy; neither region is restricted to named tech-core cities.",
    )

    ewbc_cre = 21668.988
    ewbc_resi = 17375.594
    add(
        "EWBC", "10-Q", "2026-06-30", "Northern California + Washington CRE",
        "broad-region upper bound", 3826.107 + 706.606, ewbc_cre,
        "commercial real estate loans",
        "Only broad regional disclosure; includes substantial non-tech-core geography.",
    )
    add(
        "EWBC", "10-Q", "2026-06-30", "Northern California + Washington residential",
        "broad-region upper bound", 2519.218 + 994.605, ewbc_resi,
        "residential mortgage loans",
        "Only broad regional disclosure; not a city- or county-level measure.",
    )
    return rows


def portfolio_rows(urls: dict[tuple[str, str], str]) -> list[dict[str, object]]:
    raw = [
        ("FSBW", "10-Q", "2026-06-30", "CRE incl. multifamily/construction", 1004.990, 2660.157, "total gross loans"),
        ("FSBW", "10-Q", "2026-06-30", "Residential real estate", 793.497, 2660.157, "total gross loans"),
        ("FSBW", "10-Q", "2026-06-30", "Construction & development", 370.459, 2660.157, "total gross loans"),
        ("WAFD", "10-Q", "2026-06-30", "CRE + multifamily + construction + land A&D", 4721.719 + 3642.259 + 2144.343 + 219.267, 21633.392, "total gross loans"),
        ("WAFD", "10-Q", "2026-06-30", "Single-family residential", 7389.117, 21633.392, "total gross loans"),
        ("BMRC", "10-Q", "2026-06-30", "CRE incl. construction", 288.744 + 1373.990 + 16.317, 2100.976, "total loans"),
        ("BCML", "10-Q", "2026-06-30", "CRE incl. multifamily/construction", 345.008 + 478.478 + 901.277 + 10.143, 2074.704, "total loans"),
        ("CVBF", "10-Q", "2026-06-30", "Commercial real estate", 8983.934, 12017.055, "total loans"),
        ("CVBF", "10-Q", "2026-06-30", "Office", 1457.979, 8983.934, "commercial real estate loans"),
        ("COLB", "10-Q", "2026-06-30", "Office", 3559.0, 27009.0, "commercial real estate loans"),
        ("EWBC", "10-Q", "2026-06-30", "Office", 2296.0, 21668.988, "commercial real estate loans"),
    ]
    return [
        {
            "ticker": ticker,
            "form": form,
            "report_date": report_date,
            "metric": metric,
            "balance_usd_m": balance,
            "denominator_usd_m": denominator,
            "denominator_name": denominator_name,
            "portfolio_pct": pct(balance, denominator),
            "document_url": urls[(ticker, form)],
        }
        for ticker, form, report_date, metric, balance, denominator, denominator_name in raw
    ]


def credit_rows(urls: dict[tuple[str, str], str]) -> list[dict[str, object]]:
    raw = [
        ("FSBW", "10-Q", "2026-06-30", "CRE nonaccrual", 7.778, 1004.990, None, None, "Concentrated in construction loans."),
        ("FSBW", "10-Q", "2026-06-30", "Construction nonaccrual", 7.164, 370.459, None, None, "Main current weakness in the disclosed CRE buckets."),
        ("BMRC", "10-Q", "2026-06-30", "Total nonaccrual loans", 8.453, 2100.976, 26.902, 1.27, "Improved materially from 2025 year-end."),
        ("BCML", "10-Q", "2026-06-30", "Nonperforming loans", 9.104, 2074.704, 13.443, 0.65, "Improved from 2025 year-end."),
        ("CVBF", "10-Q", "2026-06-30", "Total nonaccrual loans", 16.642, 12017.055, 4.685, None, "Post-acquisition balance is not directly comparable with year-end."),
        ("COLB", "10-Q", "2026-06-30", "CRE nonaccrual", 96.0, 27009.0, 50.0, pct(50.0, 27870.0), "Deteriorated from year-end, although the absolute rate remains below 0.4%."),
        ("COLB", "10-Q", "2026-06-30", "Office nonaccrual", 30.0, 3559.0, None, None, "0.84% of office loans; issuer table also shows 0.11% when divided by total CRE."),
        ("EWBC", "10-Q", "2026-06-30", "CRE nonaccrual", 89.122, 21668.988, 66.648, 0.313, "Rose from 2025 year-end."),
    ]
    rows = []
    for ticker, form, report_date, metric, amount, denominator, prior_amount, prior_pct, note in raw:
        rows.append(
            {
                "ticker": ticker,
                "form": form,
                "report_date": report_date,
                "metric": metric,
                "current_usd_m": amount,
                "current_denominator_usd_m": denominator,
                "current_pct": pct(amount, denominator),
                "prior_usd_m": prior_amount,
                "prior_pct": prior_pct,
                "note": note,
                "document_url": urls[(ticker, form)],
            }
        )
    return rows


def write_report(geo: pd.DataFrame, portfolio: pd.DataFrame, credit: pd.DataFrame) -> None:
    def f(value: float) -> str:
        return "—" if pd.isna(value) else f"{value:.1f}%"

    strict = {
        "BMRC": geo.query("ticker == 'BMRC' and precision == 'county'").iloc[0].exposure_pct,
        "BCML": geo.query("ticker == 'BCML' and denominator_name == 'total loans'").iloc[0].exposure_pct,
        "CVBF": geo.query("ticker == 'CVBF' and denominator_name == 'total loans'").iloc[0].exposure_pct,
        "COLB": geo.query("ticker == 'COLB' and geography == 'Puget Sound + Bay Area'").iloc[0].exposure_pct,
        "EWBC": geo.query("ticker == 'EWBC' and geography.str.contains('CRE')", engine="python").iloc[0].exposure_pct,
        "WAFD": geo.query("ticker == 'WAFD'").iloc[0].exposure_pct,
    }
    def portfolio_pct(ticker: str, metric: str) -> float:
        return float(portfolio.loc[(portfolio.ticker == ticker) & (portfolio.metric == metric), "portfolio_pct"].iloc[0])

    def credit_row(ticker: str, metric: str) -> pd.Series:
        return credit.loc[(credit.ticker == ticker) & (credit.metric == metric)].iloc[0]

    bcml_npl = credit_row("BCML", "Nonperforming loans")
    cvbf_cre_pct = float(
        geo.loc[
            geo.ticker.eq("CVBF")
            & geo.denominator_name.eq("commercial real estate loans"),
            "exposure_pct",
        ].iloc[0]
    )
    urls = filing_urls()
    lines = [
        "# 第四阶段：10-K / 10-Q 地理与资产质量复核",
        "",
        "本次复核固定为 2026 年二季度 10-Q（WAFD 的 10-K 财年截至 2025-09-30；其余 10-K 截至 2025-12-31）。金额均为百万美元；更新下载后必须重新人工复核，不能自动延用这些数字。",
        "",
        "## 结论先行",
        "",
        "1. **FSBW 是最纯的定性 Puget Sound 暴露，但无法定量到科技核心。** 申报文件把 Seattle–Tacoma–Bellevue MSA 列为主要市场，然而没有按县或都会区披露贷款余额。",
        f"2. **BMRC 并不是 Silicon Valley 纯标的。** SF、San Mateo、Santa Clara 三县仅占年末 CRE 的 {strict['BMRC']:.1f}%；Marin 与 Sonoma 才是最大的两个 CRE 县。",
        f"3. **BCML 的地域稀释很明确。** 2026Q2 Bay Area 仅占总贷款 {strict['BCML']:.1f}%。",
        f"4. **CVBF 收购 Heritage 后获得了可见的 Silicon Valley 暴露，但仍由南加州和 Central Valley 主导。** Santa Clara + San Mateo 占总贷款 {strict['CVBF']:.1f}%、占 CRE {cvbf_cre_pct:.1f}%；跨期可比性因收购下降。",
        f"5. **COLB 的地理披露最好，且信用信号边际变差。** Puget + Bay Area 合计占 CRE {strict['COLB']:.1f}%；CRE nonaccrual 从年末 ${credit_row('COLB', 'CRE nonaccrual').prior_usd_m:.0f}m 升至 ${credit_row('COLB', 'CRE nonaccrual').current_usd_m:.0f}m，office nonaccrual 约为 office 余额的 {credit_row('COLB', 'Office nonaccrual').current_pct:.2f}%。",
        f"6. **EWBC 与 WAFD 只能给出宽口径上限。** EWBC 的 Northern California + Washington 占 CRE {strict['EWBC']:.1f}%；WAFD 的 Washington 占总贷款 {strict['WAFD']:.1f}%，两者都不能视为科技核心暴露。",
        "",
        "## 候选股更新",
        "",
        "- **优先继续跟踪：FSBW、COLB。** FSBW 地域叙事最纯但需补充贷款级地理证据；COLB 的地域表清楚、CRE nonaccrual 正在上升，最适合建立季度监测序列。",
        "- **第二梯队：CVBF。** 收购带来 Santa Clara/San Mateo 暴露和更大的 CRE/office 账面，但需要把 Heritage 收购影响与有机恶化拆开。",
        "- **降低短期信用恶化权重：BMRC、BCML。** 二者 2026Q2 不良指标均较年末改善；仍可作为高 CRE 集中度观察样本，但当前 10-Q 不支持“马上爆雷”的说法。",
        "- **地理纯度偏低：WAFD、EWBC。** 资产规模大、产品类型披露较好，但州/大区口径包含大量非科技核心地区。",
        "",
        "## 关键比例（口径不可直接横向排名）",
        "",
        "| 公司 | 申报地理口径 | 比例 | 分母 | 粒度 |",
        "|---|---|---:|---|---|",
    ]
    for _, row in geo.iterrows():
        lines.append(
            f"| {row.ticker} | {row.geography} | {f(row.exposure_pct)} | {row.denominator_name} | {row.precision} |"
        )
    lines += [
        "",
        "这些比例是筛选工具，不是最终风险敞口：州级/大区级数字是上限，县级数字仍包含非科技核心城市，FSBW 则只有经营足迹而没有贷款余额。",
        "",
        "## 信用与组合观察",
        "",
        f"- FSBW：CRE 约占总贷款 {portfolio_pct('FSBW', 'CRE incl. multifamily/construction'):.1f}%，construction & development 占 {portfolio_pct('FSBW', 'Construction & development'):.1f}%；CRE nonaccrual {credit_row('FSBW', 'CRE nonaccrual').current_pct:.2f}%，其中 construction 约 {credit_row('FSBW', 'Construction nonaccrual').current_pct:.2f}%。",
        f"- BMRC：CRE（含 construction）约占总贷款 {portfolio_pct('BMRC', 'CRE incl. construction'):.1f}%；总 nonaccrual 从年末 ${credit_row('BMRC', 'Total nonaccrual loans').prior_usd_m:.1f}m / {credit_row('BMRC', 'Total nonaccrual loans').prior_pct:.2f}% 降至 ${credit_row('BMRC', 'Total nonaccrual loans').current_usd_m:.2f}m / {credit_row('BMRC', 'Total nonaccrual loans').current_pct:.2f}%。",
        f"- BCML：CRE（含 multifamily/construction）约占总贷款 {portfolio_pct('BCML', 'CRE incl. multifamily/construction'):.1f}%；NPL 比率从 {bcml_npl.prior_pct:.2f}% 降至 {bcml_npl.current_pct:.2f}%。",
        f"- CVBF：CRE 占总贷款 {portfolio_pct('CVBF', 'Commercial real estate'):.1f}%，office 占 CRE {portfolio_pct('CVBF', 'Office'):.1f}%；2026Q2 完成 Heritage Commerce 收购，年末/二季度数字不可直接作同口径趋势。",
        f"- COLB：office 占 CRE {portfolio_pct('COLB', 'Office'):.1f}%；CRE nonaccrual {credit_row('COLB', 'CRE nonaccrual').current_pct:.2f}%，较年末 {credit_row('COLB', 'CRE nonaccrual').prior_pct:.2f}% 上升。",
        f"- EWBC：office 占 CRE {portfolio_pct('EWBC', 'Office'):.1f}%；CRE nonaccrual {credit_row('EWBC', 'CRE nonaccrual').current_pct:.2f}%，高于年末约 {credit_row('EWBC', 'CRE nonaccrual').prior_pct:.2f}%。",
        "上述非应计/不良余额变化只描述两个报表时点，不推断借款人恢复偿付；出售、核销及分类变动需另行核对。",
        "",
        "## 官方申报文件",
        "",
    ]
    for ticker in ["FSBW", "WAFD", "BMRC", "BCML", "CVBF", "COLB", "EWBC"]:
        lines.append(
            f"- {ticker}: [10-K]({urls[(ticker, '10-K')]}) · [10-Q]({urls[(ticker, '10-Q')]})"
        )
    lines += [
        "",
        "## 可复核输出",
        "",
        "- `sec_geographic_exposure_summary.csv`：地理敞口、分母和披露粒度。",
        "- `sec_portfolio_metrics.csv`：组合结构比例。",
        "- `sec_credit_metrics.csv`：不良/非应计余额及可比性备注。",
        "- `sec_filings_manifest.csv`：14 份原始文件 URL、缓存路径和 SHA-256。",
        "",
        "免责声明：这是公开申报文件的定量筛选，不构成投资建议。不同公司的地理定义和贷款分类不同，必须结合逐笔抵押物位置、租户/借款人行业、到期结构和估值更新进一步验证。",
    ]
    (OUTPUT_DIR / "fourth_stage_sec_findings_zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run() -> None:
    manifest = validated_manifest()
    urls = {(row.ticker, row.form): row.document_url for row in manifest.itertuples(index=False)}
    geo = pd.DataFrame(geo_rows(urls))
    portfolio = pd.DataFrame(portfolio_rows(urls))
    credit = pd.DataFrame(credit_rows(urls))

    assert set(geo.ticker) == {"FSBW", "WAFD", "BMRC", "BCML", "CVBF", "COLB", "EWBC"}
    assert geo.exposure_pct.dropna().between(0, 100).all()
    assert portfolio.portfolio_pct.between(0, 100).all()
    assert credit.current_pct.between(0, 100).all()

    source_ids = manifest[SOURCE_KEYS + ["report_date", "accession", "sha256"]]
    for frame in (geo, portfolio, credit):
        linked = frame.merge(source_ids, on=SOURCE_KEYS + ["report_date"], how="left", validate="many_to_one")
        if linked["accession"].isna().any():
            raise ValueError("Curated SEC metric has no matching reviewed filing accession")
        frame["accession"] = linked["accession"].to_numpy()
        frame["source_sha256"] = linked["sha256"].to_numpy()
        frame["amount_unit"] = "USD millions"
    geo.to_csv(OUTPUT_DIR / "sec_geographic_exposure_summary.csv", index=False)
    portfolio.to_csv(OUTPUT_DIR / "sec_portfolio_metrics.csv", index=False)
    credit.to_csv(OUTPUT_DIR / "sec_credit_metrics.csv", index=False)
    write_report(geo, portfolio, credit)
    print(f"wrote {len(geo)} geographic, {len(portfolio)} portfolio, and {len(credit)} credit metrics")


if __name__ == "__main__":
    run()
