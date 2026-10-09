# HPP 现金、债务与契约核验切片

信息截止：2026-10-09 12:10:59 PDT / 15:10:59 EDT。金额均为百万美元，除非另注。

本轮停止扩充证券收益网格，完成第一优先级的公开证据核验。当前现金、实际可借额度、完整出售后 NOI 与 2027 融资缺口仍未被公开资料闭合；不能把六月数据加几个已知事件后称为十月资产负债表。第二优先级的联合估值尚未校准，第三优先级的执行收益尚未验证。

## 契约：6.25% 是敏感性，不是 NOI 违约线

Q2 原表和 10-Q 均报告 adjusted EBITDA / fixed charges 为 1.6x，门槛 1.5x，并称六月底合规。[Q2 10-Q，债务契约表](https://www.sec.gov/Archives/edgar/data/1482512/000148251226000069/hpp-20260630.htm)。Q2 补充文件第 15 页已再次视觉核对。

以 1.6 当作精确比率，分母不变时分子降幅至等于门槛为 `1 − 1.5 / 1.6 = 6.25%`；分子不变时分母可增加 `1.6 / 1.5 − 1 = 6.667%`。如果分母先增加 5%，分子只再下降 1.5625% 就到等号。等于最低值本身不等于低于最低值。1.6 只披露一位小数；若假设按最近 0.1 四舍五入，实际比率 `[1.55, 1.65)` 对应余量 `[3.226%, 9.091%)`。该舍入规则未核实，这只是精度示例，不是对真实余量的置信区间。

已读取并视觉核对第五次修订的红线原件；适用新文字，不能照搬文字提取中混在一起的旧阈值。[签署合同 Exhibit A](https://www.sec.gov/Archives/edgar/data/1482512/000148251225000139/hpp-fifthamendmenttocred.htm)：

- Section 10.1(c) 在季度末测试过去连续 12 个月；合同 EBITDA 扣除 Capital Reserves，分母含规定的利息、非到期大额本金及合资格已付／应计优先分配。
- Section 1.2 纳入合并实体全部财务属性及未合并实体的合同 Ownership Share，口径不同于补充报告 HPP share；季度 annualized cash adjusted EBITDAre 也不是契约分子。
- Q2 所处窗口的分母有与提交银行的 2025 Projections 一致的备考要求。未取得这些预测和填好的合规证书，无法重建精确余量。
- Article X 违约在 11.1(b)(i)，不能套用 (b)(ii) 的 30 天一般补救期；未确认自动 equity cure。豁免和补救需依合同；任何 EOD 下的上游分配受 10.1(i) 约束。

这些条款不证明现在违约，也不支持把 NOI 降幅直接等同分子降幅。停派累计优先股息不能机械地从契约分母扣除。合同资本准备与实际 TI/LC 现金支出也要分别建账。

## 可用额度受承诺期限和契约双重约束

六月底可核对的是合并 unrestricted cash 80.760，restricted cash 24.659，revolver 未用额度 795.250；后者不等于无条件可提款现金。按精确组件相加为 876.010；发行人标题采用四舍五入组件称约 876.1，不能给标题数额额外精度。[Q2 补充文件，第 3、8、13 页](https://s22.q4cdn.com/675150095/files/doc_financials/2026/q2/HPP-Q2-2026-Supplemental-compressed.pdf)。受限现金不进入 unrestricted cash。

最低 liquidity 125 在 revolving commitments 超过 600 时适用。[8-K Item 1.01](https://www.sec.gov/Archives/edgar/data/1482512/000148251225000139/hpp-20250910.htm) 与签署合同一致；[新闻稿](https://investors.hudsonpacificproperties.com/investor-resources/press-releases/press-release-details/2025/Hudson-Pacific-Completes-Credit-Facility-Amendment-and-Extension/default.aspx) 的 borrowings 措辞不同。因此六月无借款也不能据此说该限制不适用。仅这一约束下的算术净现金支出余量为 751.010；其他契约、资金归属与提款条件会继续限制，不能把它称为当前可用资金。

333.250 承诺在 2026-12-21 到期，之后剩 462.0。基础到期是 2028-12-31，两次六个月展期附条件才到 2029-12-31；补充文件列的是含选项到期。2027 不能沿用 795.250 额度。按不变六月现金加 462.0 的 542.760 只是静态演示，不能拿它减 HPP share 到期债务计算真实融资缺口。无抵押 NOI / 无抵押利息门槛在 2027 从 1.75 回到 2.0，需和 fixed-charge covenant 一起预测。

## 事件桥：什么已经移除，什么尚未结算

2001 Gateway 于 7 月 1 日成交，毛价 25.0；875/899 Howard 于 9 月 25 日成交，毛价 65.5。Q3 合计毛价 90.5，净收入用途为 general corporate purposes，未披露本切片可用的净入账现金及逐笔还债证明。[Gateway，10-Q Note 22](https://www.sec.gov/Archives/edgar/data/1482512/000148251226000069/hpp-20260630.htm)，[Howard 出售公告](https://investors.hudsonpacificproperties.com/investor-resources/press-releases/press-release-details/2026/Hudson-Pacific-Sells-875-and-899-Howard-in-San-Francisco/default.aspx)。不能在未扣还债现金支出的情况下，同时把全额毛价记作现金增加、又把同额债务扣掉；已卖物业也不能继续保留终值和 NOI。

Howard 出售移除了该物业未来资本支出与剩余主要租约到期风险，也带走租金。已准确映射的 Glu Mobile current ABR 为 5.637567，六月 2027 ABR 66.099838 扣除后是 60.462271。ABR 不等于 NOI；其他已卖租约、新签、提前退租、免费租金与费用还未全部对齐，不能称完整当前 rent roll。[Q2 补充文件，第 19、22、24 页](https://s22.q4cdn.com/675150095/files/doc_financials/2026/q2/HPP-Q2-2026-Supplemental-compressed.pdf)。

Hollywood 11 亿美元 JV 借款已展期至 2027-11-09，同时有 JV 层面 20.0 租赁／资本准备及未来 excess cash sweep。2026 到期压力被推后，债务没有消失；JV 现金不能全当作可分配母公司现金。未披露 HPP unrestricted cash 为准备实际支出多少，不能直接扣 10.2。[9 月 11 日 8-K Item 8.01](https://www.sec.gov/Archives/edgar/data/1482512/000148251226000073/hpp-20260909.htm)。六月 HPP share 到期表加已执行展期后，2027 为 1,033.962，仍不是闭合当前余额。

截至本研究截点 tender 尚未到 10 月 9 日 17:00 EDT 截止，预计 10 月 14 日结算；实际接受额、结算、现金／revolver 分配仍未知。已验证完成的本金减额为零，这不代表最终接受额为零。若恰按各 100.0 目标结算，197.125 是不含应计利息／费用的支付；净债务仅减少 2.875，cash + unused revolver 同时消耗 197.125，资金来自 cash 或 revolver 不改变这个合计。[tender 公告，第 1 页](https://s22.q4cdn.com/675150095/files/doc_news/2026/10/HPP-Tender-PR-FINAL.pdf)。额度提款只是现金和未用额度互换，不会创造总流动性。

## 第二优先级已消除一个分母盲点

六月普通股 54.267530m 本身不能作为完整经济股权分母：10-Q EPS 注脚另有 10.223269m 可按名义对价随时行权的 pre-funded warrants；季度 common/OP units 加权平均为 65.684497m。加权平均仍不能充当十月或 2030 点时完全摊薄数。[10-Q Note 15](https://www.sec.gov/Archives/edgar/data/1482512/000148251226000069/hpp-20260630.htm)。

下一项联合估值须用同一 2027–2030 经营状态：租约保留面积、租金、免费期与 downtime → NOI → TI/LC/capex 与母公司现金 → 契约和融资／出售／增发 → JV 与母公司逐层回收 → Series C 派息、累计欠息／回收与普通股残值。AI 面积压缩通过面积假设进入，保留 AI 新增需求／复苏的抵消分支，不预设因果结论。

reverse NAV 求解的是达到给定普通股市价所需的最低租金／入住率／融资条件；不得再输入独立普通股退出价和优先股收益率决定结果。必须映射 OP preferred units、外部 Series A、JV partner debt／权益、受限现金和 parent claims，防止双扣 Series C 对应的内部 OP 优先单位，避免将被租金费用吸收的 ground lease 义务再无调整扣一遍。合同 capitalization rates 是抵押／契约价值定义，不是市场估值证据。

完整当前现金和融资缺口需要下一批公开披露，Q3 业绩已安排 11 月 5 日发布。[发行人时间公告](https://investors.hudsonpacificproperties.com/investor-resources/press-releases/press-release-details/2026/Hudson-Pacific-Properties-Announces-Date-for-Third-Quarter-Earnings-Release-and-Conference-Call/default.aspx)。在此之前继续核对公开租约、物业债务、warrants/OP/awards 和 TI/LC，不因券商报价缺失停工。未创建定时监控。

复现：`python scripts/hpp_liquidity_audit.py`；`python -m unittest discover -s tests`。来源清单和门禁在 `config/hpp_liquidity_inputs.json`，机器结果与执行哈希在同目录 JSON。原始下载 403 已记录，web 阅读不虚构字节哈希；既有 PDF 的哈希保留。原先 456 个收益情景保持历史快照，未扩充。
