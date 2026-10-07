# V2 实施计划：房地产变化、信用传导与市场定价

日期：2026-10-07（America/Los_Angeles）。状态：已完成专家反馈阅读、现有代码检查及关键公开来源抽查；以下为待实施计划，不代表新模型或回测已经运行。当前计算基线为提交 `e15ea64`。

## 目标与方法调整

研究目标改为：识别哪些上市银行或写字楼业主的现金流、融资和资本会在未来 4–12 个季度受压，哪些变化已被价格反映，哪些在当时可获得的信息中已经可以识别。

现有城市/HMDA/CRE 筛选提供静态位置与规模信息。V2 增加就业、交易流动性、物业价格、租约、信用状况、融资到期、盈利资本及市场价格的时间维度。城市分数不再作为是否进入观察名单的门槛。

研究对象先覆盖 WAFD、COLB，FSBW 为住宅/本地信贷参照；写字楼业主先覆盖 HPP、KRC，BXP 为对照。其余现有银行继续保留在观察范围内。候选池依据经济业务和披露覆盖建立，退出必须记录理由，不能因为缺少精细地理数据就判为低风险。所有排序区分银行与业主、风险大小与价格是否有吸引力。

传导路径有多条：

- 就业/收入变化 → 住宅成交与抵押物价格 → 借款人现金流及贷款表现。
- 企业办公需求 → 续租、空置、租赁支出与 NOI → 业主估值、再融资及股权价值。
- 存款成本、资产重定价、并购、监管和资本行动 → 银行盈利/资本/估值。
- 利率与风险偏好可以同时影响以上路径。股价可以提前反映预期，不能强制排在 NPL 或资本损失之后。

AI 替代是待验证的冲击解释之一。裁员、地产下跌和股价下跌本身均不足以识别 AI 因果效应。

## 本轮核实与仍待核实的事项

1. **数据源遗漏得到确认。** `sec_filing_screen.py` 目前每家公司只取最新 10-K/10-Q；`sec_disclosure_analysis.py` 用 ticker/form 锁定人工摘录，无法表达多个季度和同一 8-K 的多个附件。应扩展为逐文档、逐指标的证据链。
2. **COLB 已有 office × region 披露。** 2026 Q2 演示第 26 页给出 Puget Sound 15%、Bay Area 4%，以及 LTV、非自用 DSCR、信用状况、到期/重定价。旧“交叉敞口完全未披露”的说法需要修正。但 `3.559bn × 19% ≈ 676m` 在核对演示与 10-Q 的余额、范围及四舍五入前，只能列为暂算。演示的 $29.9m/0.83% 与仓库的 $3.559bn 并非直接对得上；应查清差异后再发布美元数。[COLB 原始演示](https://www.sec.gov/Archives/edgar/data/887343/000088734326000165/colb2026q2earningspresen.htm)
3. **WAFD 是混合信用信号。** 2026-03-31 至 2026-06-30，adversely classified/net loans 为 2.60% → 2.59%，而 total criticized/net loans 为 4.24% → 4.93%。不能只保留其中一个方向。WAFD 财年 Q3 对应日历 Q2；演示中 LTV 还有一季度滞后，应逐字段保存日期。[官方业绩报告第 2 页](https://www.wafdbank.com/documents/financial-news/2026/wafd-bank-press-release-20260716.pdf)；[投资者演示第 9、14 页](https://www.sec.gov/Archives/edgar/data/936528/000093652826000058/wafdinvestorpresentation.htm)
4. **WAFD 存在重大事件路径。** 2026-09-07 官方宣布 EverBank 合并交易。复盘应区分公告前后，并识别换股、股权稀释、盈利预期与资本影响。该公告不能用于声称 9 月 1 日已经知道这项交易。[官方公告](https://www.everbank.com/about/news/09-07-26/everbank-wafd-announce-strategic-merger)
5. **约 17% 跌幅尚未在本轮复算。** 首先核对起止日期、价格回报/含分红回报、月度回报/高点回撤。默认“上个月”为 2026 年 9 月，月度计算使用 8 月末至 9 月末收盘，并另列近期高点回撤；不能挑选最接近 17% 的区间来证明原假设。

## 实施顺序与交付标准

### 第一批：证据补全、WAFD 复盘、当时信息重建

目的：先回答我们漏了哪些已公开信息，以及它们能否在下跌前改变研究判断。

工作：

- 扩展 SEC 抓取到历史 submissions、10-K/10-Q、8-K、EX-99 财报和演示；同时发现公司 IR 的 supplemental、业绩演示与并购材料。先回填 WAFD/COLB 从 2024 Q1 至最新已发布季度，优先人工复核 2025 Q4、2026 Q1/Q2。保留 WAFD 的财年标签及实际期末日。
- HTML、PDF 和图片幻灯片按文档类型提取；保存页码、表名、原文片段、原始值、单位、分母、组合范围。低置信提取进入复核队列，先用人工核实的种子数据跑通，不以实现全自动 OCR 为前提。
- 为 COLB 第 26 页与 WAFD 业绩/演示完成可追溯摘录；美元总额和地区占比只有在同一组合口径时才相乘。优先使用直接披露的地区 office 数据，边际上下界作为未披露组合的后备方法。
- 引入日行情、分红拆股、KRE、广泛市场、2Y/10Y 利率与事件时间。价格优先使用发行人/交易所可得历史数据；受限时用有明确复权定义、可导出原始文件的行情供应商，并用独立来源核对区间端点。来源及许可限制登记，禁止手抄截图作为完整序列。
- 建立 WAFD/COLB 事件表：业绩、指引、并购、资本行动、监管/评级事件；补充 NIM、存款成本、存款流失、PPNR 和资产重定价路径，避免把所有残差解释成地产信用。
- 复盘时冻结“截至 2026-09-01 已公开的信息”；分别分析 9 月 7 日公告后首个交易时点、月末及截至 10 月 7 日的可得信息。若重建不到当时的数据版本，标为事后重建，不能标成无前视偏差回测。

交付：`source_manifest`、`reviewed_observations`、`market_daily`、`events` 和 WAFD/COLB 对照复盘。复盘明确列出“当时已有但漏读”“当时尚未知”“虽观察到但未纳入判断”“无法解释”四类。

验收：复算指定窗口的价格/总回报；对齐公告可交易时点；关键数据可回到原页；回报因子拟合只使用事件前历史（预设 252 日，126 日敏感性）；事件窗口超额回报和模型残差报告不确定性，不声称精确因果分摊。9 月事件窗口不能反过来用于挑选模型参数或候选股。

### 第二批：季度银行面板与写字楼业主试点

目的：形成最小可用研究版本；银行信用与业主收租两条线都必须有具体结果。

银行工作：

- 把贷款风险评级、逾期、非应计、核销、回收、ACL、拨备、组合规模、LTV、DSCR、担保和到期/重定价建成季度面板。全行、CRE、office、owner/non-owner occupied 分开。
- FFIEC Call Report/UBPR 提供银行子公司监管口径，FR Y-9C/SEC 提供上市母公司口径；FDIC 用于交叉核对。小型母公司若无 Y-9C，使用其实际适用报表/SEC，不能补造一行母公司数字。
- 建立带生效日期的 CIK、RSSD、LEI、FDIC certificate、上市母公司与并购关系。WAFD 合并的公告、预计完成与实际完成分别记录；COLB/CVBF 的收购前后数据保留范围变更。
- 每个余额同时给分母和金额，避免组合增长、缩表、收购或核销使比例变化被误读。可取得的新增、恢复、出售、转出、核销做滚动核对；无法取得时输出净变化及未解释部分。

业主工作：

- 从 HPP/KRC 开始，BXP 对照，抓 10-K/10-Q、EX-99 和 supplemental；先做 Seattle/Eastside/SF Bay Area 所披露的物业及 2027–2029 租约。
- 建立 `property → ownership/JV → tenant → lease → NOI → debt` 关系。面积、租金、入住率和已出租率分开；权益份额作用于适用金额，不能把比例反复相乘。
- 记录租户行业、租金到期、续租租金、免租期、停租空档、TI/LC、物业 NOI、债务到期和追索范围。担保/母公司融资单列；贷款最终持有人只有查证时才连接。
- 租户与到期表只有边际合计时，对“科技租户 × 2027 到期租金”给覆盖率/边界/情景，不能把两个比例相乘写成观察值。租约未到期的裁员不自动使合同租金消失，估值变化可先行。

交付：`bank_credit_quarterly`、`bank_funding_earnings_quarterly`、`loan_maturity_repricing`、`office_properties`、`office_leases`、`office_debt`，及每个对象的证据卡：支持压力的证据、相反证据、下一催化日期、尚缺信息。

验收：试点银行至少三个已核实连续季度；两家业主完成当前组合基线、到期表及披露覆盖率；每条记录可定位来源。未披露字段保持缺失。只有公司/地区层数据时，不声称完成逐物业贷款表。

### 第三批：就业、住宅流动性与价格发现

目的：辨认先出现的是就业/收入变化、成交减少、价格重估，还是独立的金融市场冲击。

工作：

- WA WARN 保存 received/published/effective 三种日期，处理同一事件的追加、撤回、重复与多地址。科技行业用版本化分类规则；WARN 不覆盖全部裁员，也不自动说明裁员由 AI 导致。湾区阶段接入 CA 对应来源。
- QCEW 使用 county × NAICS 的就业和工资总额，处理保密抑制、行业版本和季节性。使用实际发布日；截至 2026-10-07，官方日程中 2026 Q2 尚待 12 月 2 日发布，不能把它当作实时已知数据。
- Redfin 保存各产品的地区、频率、滚动窗口、季调状态和下载版本；指标覆盖按产品核查。先做 Puget Sound 与湾区 metro/county，再按覆盖扩到 city/ZIP。NWMLS 公开月报做核对，会员字段不作为首版依赖。
- 流动性分别展示 pending、closed、inventory、DOM、months supply、cancel、price cuts；价格发现分别展示 HPI、$/sf、sale/list；强迫出售候选分别显示有证据的 trustee/foreclosure、重复交易折价和短持有转售。
- County sales 做合格交易与重复交易样本，排除明显非市场交易、组合出售、重大改建及重复申报。低于 assessed value 只能是筛选条件，不能直接认定强迫出售。

交付：`employment_shock_panel`、`housing_liquidity_panel`、`collateral_prices` 和一份地区时间轴。先展示可解释原始指标，随后才评估标准化指数；缺指标不记零，训练窗口不含未来，避免滚动窗口和相关指标重复计权。

验收：每个指标都有数据覆盖、发布时间、修订与季调标志；2026 年 Redfin 方法变更可追溯；识别“成交弱、价格暂稳”的组合，不要求所有指标同时恶化。

### 第四批：再融资、现金损失与资本桥梁

目的：估计需要补充多少资金、谁承担压力、在什么已披露时间窗口发生，并量化对盈利资本的情景影响。

工作：

- 对口径兼容的贷款组计算：`RefiCapacity = min(NOI / (DSCR_min × debt_service_factor), property_value × max_LTV)`，`RefiGap = max(0, maturity_balance − RefiCapacity)`。摊还型、只付息、气球偿付和利率重定价分别处理。
- 以 NOI、资本化率、利率、最低 DSCR、最高 LTV 和到期余额构建确定性情景网格。只知道组合均值时，输出“代表性组合情景”及假设敏感性，不声称逐笔违约概率或实际缺口分布；先不用任意 Monte Carlo 包装精度。
- 到期表只有年份时，结果只做到年份。到期、重定价、swap 到期和租约到期是不同事件。地区×到期×物业类型未交叉披露时，不独立相乘成精确金额。
- 业主补资、出售、展期、担保执行和违约分别建情景。融资缺口不是贷款损失；从未解决缺口到 PD/LGD 必须有明确额外假设或可校准样本。
- 贷款损失经核销/回收、ACL 与拨备、PPNR、税、分红/回购及其他权益变动进入母公司 TCE/CET1；资本指标和风险加权资产变化分开。以 `ACL_end = ACL_start + provision − net_chargeoffs + other_changes` 核对，不再次从已受拨备影响的权益扣同一份 ACL。
- 业主输出现金 NOI、TI/LC 后现金流、利息/资本支出与权益估值，按 JV 权益和债务追索范围归属。

交付：`refinance_scenarios`、`owner_cashflow_scenarios`、`loss_capital_bridge`。每个结果列基准、压力、改善情景及关键反证条件。

验收：金额和单位一致；利率/NOI/LTV 约束极端值和单调性正确；资本滚动可对账；结果区分已披露值、按同口径计算值和假设值。输出的时间粒度不超过源数据。

### 第五批：LODES/HMDA 与 CMBS 的增量验证

目的：只有能改善前四批结论的空间和贷款信息，才进入更细模型。

- LODES 8.4 的 RAC/WAC/OD 及官方 crosswalk 覆盖居住与工作联系；用 primary jobs 减少多重就业重复，并保留就业岗位单位。优先计算可直接识别的居住地行业暴露；工作地冲击沿 OD 传播时标注推断及误差。
- LODES 最高收入档只是月收入 >$3,333；OD 只有粗行业边际，没有任意“详细科技行业×高收入×居住/工作地点”联合明细，也没有个人职业或雇主身份。因此不能直接得出 25 万美元工程师占比、家庭购买力或 HMDA 借款人的失业概率。行业/职业/工资补充源分别说明可识别范围。
- HMDA 补充 income、property value、CLTV、DTI、rate、term、purpose 等字段，保留区间、取整、豁免与缺失。住房价值指数使用实际可取得的地理层级；没有 tract HPI 时明确标为上级地区代理。余额、留存、次级抵押权、后续再融资和贷款购入仍存在未观察项。
- 在没有违约标签前，输出压力分层/情景损失，不声称拟合出贷款级 PD。若引入外部违约样本，先验证样本定义、经济周期和贷款覆盖可迁移性，再做外样本校准。
- CMBS 从目标地区的少量公开 deal 验证 ABS-EE/EX-102 与补充材料，建立 loan/property 稳定标识及余额、到期、DSCR、入住率、服务/逾期状态。先核实各字段是否实际公开；缺少 watchlist/special servicing 字段不补造。处理一贷多物业、共贷及证券化份额，防止重复加总。
- CMBS 作为同地区同类物业的外部证据，不能据此推断某家银行持有这些贷款；公开证券化样本的选择偏差需报告。

交付：可审计的住宅暴露替代指标、HMDA 脆弱度分层、CMBS 地区面板，以及“加入该模块是否改变结论”的比较。若没有新增解释力，保持为辅助信息。

### 第六批：情景定价与前瞻评估

市场数据与事件监测已在第一批开始；本批完成跨模块判断。

- 银行以母公司层盈利/资本情景及估值区间，业主以 NOI/现金流/NAV 情景，与市场价格比较；报告时间、反证、借券费、股息补偿及流动性。实时借券可得性若无来源则标未知，不用股票成交量代替。
- `TBV − Price/m` 仅作为估值折价的假设情景。全公司比较用 `TCE − MarketCap/m`，每股比较保持全部单位为每股；m 由同日同口径可比公司/盈利与资本成本情景确定。折价也可反映盈利能力、增长、并购和风险溢价，不能称为已识别的市场信用损失。
- 以滚动历史截点、跨银行/业主样本、事先指定的事件窗口和参数评估；包括未下跌的对照。记录提前量、误报、漏报、周转与成本后表现，避免只用 WAFD 这一个已知结果调参。
- 分开输出“业务风险”“未来催化”“市场已反映程度”“交易可行性”和证据覆盖，不先压成一个主观总分。允许结论为证据相反或机会已被反映。

验收：任何历史判断都能按信息可得日期重现；复权、发布滞后、并购范围和样本存续偏差有检查；新数据能够推翻原先的压力判断。

## 数据契约与代码落点

每条观测最少包含：`entity_id`、`entity_scope`、`period_end`、`fiscal_label`、`published_at`、`available_at`、`retrieved_at`、`source_id`、`page_or_table`、`metric`、`value`、`unit`、`denominator`、`portfolio_scope`、`geography`、`status`、`missing_reason`。`status` 区分 observed / derived / scenario；原始发布日期未知的行不能参与声称可交易的历史回测。修订与被替代值都保留。

来源标识应基于 CIK + accession + document/exhibit + hash；IR 无 accession 的文件以官方 URL + 文档日期 + hash 标识，再关联 SEC 同源附件。指标锁还包括页表/单位/范围，取代只按 ticker/form 寻址的假设。

先沿用 Python、现有 scripts/tests 与缓存清单，不为 V2 先重写整套工程。具体落点：

- `scripts/sec_filing_screen.py`：历史文档发现、8-K 附件与 IR 文件关联。
- `scripts/sec_disclosure_analysis.py`：从有来源的长格式观测生成时间序列；旧 Q2 快照保留历史标签。
- `scripts/office_intersection_bounds.py`：直接交叉披露优先，未披露时才计算边界；范围不一致时停止合并。
- 新增市场事件、季度信用、地方就业/住宅、业主租约、再融资/资本模块；逐批落地，模块输出使用统一证据与日期契约。
- `tests/` 优先覆盖真实风险：来源替换、重复附件、空值、季度错位、组合范围、评级重叠、未来信息泄漏、公司行动复权、权益份额重复及资本重复扣减。

每批保存下载清单与 hash、已复核小样本、可复算结果、限制和下一步至 HANDOFF，并同步 Git。脚本刷新频率可以按日/周/季设计；自动定时运行需另行配置，目前未创建。

## 必须修正的模型理解

- 风险评级、逾期天数、非应计和核销是不同维度，不能当作每笔贷款依次经过的互斥状态。Criticized 往往包含 classified；LateStress 中 past due 是否包含 nonaccrual 要核原定义。存量变化不等于迁移概率。
- COLB 的非自用 DSCR 不能直接套在整本 office；演示还包含自用、医疗牙科和建设贷款，不能把 office 整体理解成科技公司承租的写字楼。
- 没有联合分布时，平均 LTV/DSCR 不足以识别违约尾部；模拟只能表达新增假设，不能创造数据。
- 参考市场收益和利率回归提供统计基准，残差仍可能来自漏掉的共同因子。单个事件 dummy 不能证明该事件造成多少跌幅。
- 研究改进应以信息覆盖、可复现性、提前量和外样本表现验收；不能以“新模型必能抓住全部 17%”验收。

## 首次执行的明确边界

先完成第一批和第二批的最小版本：WAFD/COLB 的原始材料、季度指标和事件复盘，以及 HPP/KRC 的收租/到期基线。第一份结果必须直接回答：此前遗漏什么、当时何时能知道、哪些风险支持/反对判断、下一观察窗口是什么。随后根据数据缺口推进第三至第六批。

本计划不把“等待所有数据齐全”作为输出第一份结论的条件；同时，每个结论要显示其覆盖范围及能够推翻它的证据。

## 已核查的实施入口

- [WAFD 官方财务材料目录](https://www.wafdbank.com/about-us/investor-relations/financial-news)
- [FFIEC Call Report/UBPR 批量下载](https://cdr.ffiec.gov/public/pws/downloadbulkdata.aspx)
- [NIC 母公司财务数据说明](https://www.ffiec.gov/npw/Home/About)
- [WA WARN](https://esd.wa.gov/employer-requirements/layoffs-and-employee-notifications/worker-adjustment-and-retraining-notification-warn-layoff-and-closure-database)
- [QCEW 下载](https://www.bls.gov/cew/downloadable-data-files.htm)与[发布日历](https://www.bls.gov/cew/release-calendar.htm)
- [Redfin 下载](https://www.redfin.com/news/data-center/downloads/)与[指标/时间窗口方法](https://www.redfin.com/news/data-center/methodology/)
- [King County eSales](https://info.kingcounty.gov/assessor/esales/Residential.aspx?openSearchForm=1)与[最近三年成交图层](https://www5.kingcounty.gov/SDC?Layer=parcel_sales3yr_area)
- [LODES 8.4 技术文档](https://lehd.ces.census.gov/doc/help/onthemap/LODESTechDoc.pdf)
- [CMBS ABS-EE/EX-102 公开文件样例](https://www.sec.gov/Archives/edgar/data/1547361/000153949726002177/0001539497-26-002177-index.htm)
