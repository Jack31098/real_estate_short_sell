"""Chinese evidence report. All quantitative comparison cells use reviewed inputs."""
import json
import pandas as pd
from research_sources import ROOT, OUT, write_json
from research_contract import as_of, instant


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                     ['| '+' | '.join(str(x).replace('|','/') for x in row)+' |' for row in rows])+'\n'


def write_report(rows,cutoffs,version,run_id):
    def get(entity,metric,period='2026-06-30',geo='all'):
        match=[r for r in rows if r['entity_id']==entity and r['metric']==metric and r['period_end']==period and r['geography']==geo]
        if len(match)!=1: raise ValueError(f'Ambiguous/missing report input {entity,metric,period,geo}')
        return match[0]['value']
    market=pd.read_csv(OUT/'market_daily.csv')
    windows=pd.read_csv(OUT/'market_window_returns.csv')
    factors=json.loads((OUT/'event_factor_results.json').read_text())
    sources={s['key']:s for s in json.loads((OUT/'source_manifest.json').read_text())}
    events=json.loads((ROOT/'config/v2_events.json').read_text())
    for e in events:
        s=sources[e['source_key']]
        e.update(source_id=s['source_id'],source_sha256=s['sha256'],retrieved_at=s['retrieved_at'],
                 metric_definition_version='event_record.v1',transform_code_version=version)
    write_json(OUT/'events.json',events)
    registry=json.loads((ROOT/'config/v2_control_registry.json').read_text())
    write_json(OUT/'control_registry.json',registry)
    def link(key,label,page=None):
        s=sources[key];return f'[{label}]({s["url"]}'+(f'#page={page}' if page else '')+')'
    def win(ticker,label):
        return windows.loc[(windows.ticker==ticker)&(windows.window==label)].iloc[0]
    w=win('WAFD','september_month'); c=win('COLB','september_month')
    lines=['# V2 首轮执行报告：银行资金、信用与市场定价',
        '', '研究日期：2026-10-07。完整行情截止 2026-10-06；基本面为 2025-12 / 2026-03 / 2026-06 三个季度，事件另按实际披露日期更新。',
        '', '**本轮已运行下载、校验、季度面板、行情/事件回归和历史截点报告。第一、二批形成可用初版，尚未通过完整批次验收；没有完成 AI 因果检验或交易模型。**',
        '', '## 1. 本轮结论', '',
        f'1. WAFD 的跌幅已复现：9 月月度价格/总回报均为 **{w.price_return_pct:.2f}%**；9 月 4 日公告前收盘至 9 月 30 日为 **{win("WAFD","announcement_to_month_end").price_return_pct:.2f}%**。COLB 9 月为 **{c.price_return_pct:.2f}%**。这两个 WAFD 区间不能互换。',
        '2. WAFD 应提高资金结构与公司事件的研究优先级：存款流失和借款增加已在公告前可见，criticized 也上升；同时 NIM/PPNR 改善、classified 未恶化，不能把它概括为单一路径信用崩塌。9 月 7 日合并公告提供了新的估值解释，但事件残差仍不是因果证据。',
        '3. COLB 的信用风险比较可见，但不自动成为更好的空头：总非应计贷款环比下降，90 天以上仍计息贷款上升，办公楼 classified 又上升。必须按分项读，且股价相对银行 ETF 的表现明显强于 WAFD。',
        '4. Office 是业主收租/续租/债务再融资研究。HPP 的 North San Jose 明显弱于其 Santa Clara；HPP/KRC 的租约到期表和银行贷款到期表分开保存。市场净吸纳的改善也构成对“AI 必然摧毁办公需求”的反证。',
        '5. 目前支持的是“WAFD 资金/交易重估、COLB 信用迁移、HPP 租约与净债务”三个不同研究方向；尚不能得出谁是当前最佳空头，也不能把当前价格折价解释为某个风险已被完全计入。',
        '', '## 2. 市场复算与事件残差', '',
        table(['对象','9月价格回报','9月含分红回报','相对 KRE 总回报差（百分点）'],
            [[t,f'{win(t,"september_month").price_return_pct:.2f}%',f'{win(t,"september_month").total_return_pct:.2f}%',
              f'{win(t,"september_month").excess_vs_KRE_pp:.2f}' if t in ['WAFD','COLB'] else '不以银行ETF作业主对照'] for t in ['WAFD','COLB','HPP','KRC']]),
        '月度端点为 8 月 31 日至 9 月 30 日。Yahoo 日线覆盖 2024 年起六个代码；WAFD/COLB 五个关键端点已与 StockAnalysis / S&P Global 收盘价逐一对照到美分。复权历史是本次重建，并非当时下载的价格档案。见 [端点审计](market_endpoint_checks.json)、[公司行动](corporate_actions.json)。',
        '',table(['对象','训练日数','事件窗','累计日残差（百分点）','iid 95%半宽'],
            [[f['ticker'],f['training_sessions'],f["event_start"]+' → '+f["event_end"],f'{f["sum_daily_residual_pct"]:.2f}',f'±{f["iid_95_half_width_pct"]:.2f}'] for f in factors if f['event_end'] in ['2026-09-08','2026-09-30']]),
        '回归因子为 KRE/SPY 总回报与美国财政部 2Y/10Y 收益率日变化；训练严格截止 9 月 4 日。残差是日异常收益求和，与复合持有回报不同。区间假设 iid，未处理事件异方差、自相关及共因子内生性；17 日长窗还混入其他新闻。只能作描述性异常回报，不能说“合并导致了全部下跌”。收益率节假日沿用此前值，具体日期见 market_validation.json。',
        '', '## 3. 四个历史截点的四层表', '',
        '这些表是按披露日期重建的信息集。日期不详的日内发布时间统一延后至次日 12:00 UTC；不是严格的逐分钟可交易回测。三季基础指标多数来自 7 月文件中的比较列，不能据此宣称该数值版本在 1 月已知。新消息不会反向进入 9 月 1 日截点。']
    snapshot_meta=[]
    for cutoff in cutoffs:
        known=as_of(rows,cutoff)
        ev=[e for e in events if instant(e['available_at'])<=instant(cutoff)]
        merger=any(e['entity_id']=='WAFD' for e in ev)
        cells={}
        for entity in ['WAFD','COLB']:
            f=market.loc[(market.ticker==entity)&(market.date<=cutoff[:10])].iloc[-1]
            tbv=get(entity,'tbv_per_share')
            price=f'截至 {f.date} 收盘 ${f.close:.2f}；相对 6 月 TBV {f.close/tbv:.2f}x（滞后账面值）'
            if cutoff[:10]>='2026-09-30':
                a=win(entity,'september_month');price+=f'；9月总回报 {a.total_return_pct:.2f}%，相对KRE {a.excess_vs_KRE_pp:+.2f}pp'
            elif cutoff[:10]=='2026-09-08':
                a=win(entity,'merger_first_session');price+=f'；9/4→9/8 {a.total_return_pct:.2f}%'
            cells[entity]=price
        lines+=['',f'### 截至 {cutoff[:10]}','',table(['层','WAFD','COLB'],[
            ['当前已发生','6月存款 $20.932bn、借款含次级债 $3.316bn；NIM 2.81%；非应计 $127.569m。'+('合并已公告，尚未完成。' if merger else '该截点没有合并公告信息。'),
             '6月存款 $52.056bn、借款不含次级债 $4.250bn；税等价 NIM 3.93%；非应计 $180m，NPL $268m。'],
            ['领先恶化指标','criticized/net loans 4.24%→4.93%；classified 2.60%→2.59%；借款利息支出环比上升。',
             '办公楼 classified $78.3m→$85.3m；31–89天逾期 $168m→$125m 改善；指标不可相加。'],
            ['尚未发生但暴露存在',('管理层预计2027 EPS增厚/TBV摊薄；审批、执行与公允价值调整仍待发生。' if merger else '固定/浮动资产、资金重定价可能影响盈利；缺少纯2027合同到期额。')+' 尚未证明未来信用损失。',
             '办公贷款披露2027到期占9%，当年重定价占5%；区域百分比与10-Q余额尚未核齐。未来损失/RefiGap未知。'],
            ['市场已经反映：可观测价格证据',cells['WAFD'],cells['COLB']]])]
        snapshot_meta.append({'as_of':cutoff,'observation_ids':[r['observation_id'] for r in known],
                              'event_ids':[e['event_id'] for e in ev], 'market_prices':cells})
    write_json(OUT/'four_layer_asof_inputs.json',snapshot_meta)
    lines+=['','## 4. 信用与资金三季变化','','单位为 USD million，比例为百分数；按自然季度对齐，WAFD 的三列实际为 FY2026 Q1/Q2/Q3。']
    metrics={'WAFD':[('deposits','存款'),('borrowings_including_junior','借款含次级债'),('nib_deposits','不付息存款'),
        ('uninsured_and_uncollateralized_deposits','无保险且无抵押存款'),('afs_fair_value','AFS公允价值'),('htm_amortized_cost','HTM摊余成本'),
        ('nim_gaap','NIM（GAAP）'),('ppnr_gaap_basis','PPNR（税前利润+拨备）'),('provision_total','拨备'),
        ('nonaccrual_loans','非应计贷款'),('criticized_to_net_loans','criticized/net loans'),('classified_to_net_loans','classified/net loans')],
        'COLB':[('deposits','存款'),('borrowings_excluding_junior','借款不含次级债'),('nib_deposits','不付息存款'),
        ('uninsured_deposits','无保险存款（取整披露）'),('brokered_deposits','经纪存款'),('aoci','AOCI'),
        ('afs_duration','AFS有效久期（年）'),('nim_tax_equivalent','NIM（税等价）'),('cost_ib_deposits','付息存款成本'),
        ('ppnr_gaap_basis','PPNR（税前利润+拨备）'),('nonaccrual_loans','非应计贷款'),('past_due_90plus_accruing','90+天仍计息'),
        ('nonperforming_loans','NPL'),('office_classified','办公楼classified'),('office_nonaccrual','办公楼非应计')]}
    for entity,items in metrics.items():
        lines+=['',f'### {entity}','',table(['指标','2025-12','2026-03','2026-06'],
            [[label]+[f'{get(entity,m,p):,.3f}'.rstrip('0').rstrip('.') for p in ['2025-12-31','2026-03-31','2026-06-30']] for m,label in items])]
    lines+=['',
        'WAFD 存款半年约减少 $485m，借款含次级债增加约 $827m，借款利息季度流量从 $15.171m 升至 $27.708m；PPNR 同期从 $85.801m 增至 $95.349m。不能因批发融资增加就忽略盈利改善。',
        'COLB 经纪存款从 $2.355bn 降至 $0.978bn，借款增加但付息存款成本下降。全部三季均已包含 2025-08-31 完成的 Pacific Premier 收购；跨收购季度的增长不能直接称为有机增长。WAFD 与 COLB 的 uninsured、贷款净额、NIM 口径不同，面板保留原口径。',
        'WAFD 报告的 -100bp NII 敏感性为 +5.4%，不是我们预测的收益；模型期限尚待核对。Deposit beta/loan beta、完整批发融资口径和贷款 floors 尚缺，不用贷款收益率变化冒充 beta。',
        '', '来源：'+link('wafd_2026q2_release','WAFD 三季表',2)+'；'+link('colb_2026q2_release','COLB 三季表',8)+'；'+link('colb_2026q2_deck','COLB 资金/office',26)+'。每个数据格的文档哈希、PDF页码、单位和时间见 [reviewed_observations.json](reviewed_observations.json)。',
        '', '## 5. 双状态与计算边界', '',
        '- `LiquidityStress = unknown`：住宅 pending/closed、库存、DOM 尚未入库。银行存款流动性不等于地产成交流动性；办公楼空置率也不能替代住宅成交指标。',
        '- `CreditStress` 已输出分项向量，含三季 criticized/classified/past-due/nonaccrual/chargeoff 的已核指标，没有合成总分。分类重叠，不相加，也不假设贷款必经每个状态。',
        '- 目前没有估计 LSI 对信用的领先相关，也没有计算 RefiWall × CollateralStress。样本和地域映射不足时不输出漂亮但不可识别的系数。',
        '- COLB 办公地理占比：Puget Sound 15%、Bay 4% 可直接保存。与 10-Q $3.559bn 相乘被 `approximate` 门禁拒绝；不能输出 $676m 并标成精确敞口。见 [scope_reconciliation.json](scope_reconciliation.json)。',
        '', '## 6. 写字楼业主与市场试点', '',
        'HPP/KRC 是收租的业主，同时是借款人。入住率、租约重置、净有效租金决定收入；债务到期和估值决定融资压力。两条表分别记录，租约到期金额不是银行贷款本金。',
        '',table(['HPP 子市场（6月组合）','入住率','出租率','HPP份额年化基础租金 $m'],[
            [g,f'{get("HPP","office_occupied_pct",geo=g):.1f}%',f'{get("HPP","office_leased_pct",geo=g):.1f}%',f'{get("HPP","office_owner_share_abr",geo=g):.2f}'] for g in ['North San Jose','Santa Clara','San Francisco','Seattle']]),
        'North San Jose 和 Santa Clara 已独立入表；这些是 HPP 的物业组合，不代表整座城市。6月组合尚含随后出售物业，不能称为10月现存组合。'+link('hpp_2026q2_supplement','HPP地理披露',17),
        '', 'HPP 当季同空间现金租金变化 -11.4%，而 GAAP 租金变化为正；新租约净有效租金 $44.35/sf/年，续约 $65.41，TI/LC 分别为 $113.95/sf 和 $4.06/sf。净有效租金已扣年化 TI/LC，不再重复扣除。2027 到期表披露 HPP 份额 ABR $66.10m、13.9%，与第17页在营组合 ABR 口径不同。'+link('hpp_2026q2_supplement','租赁及到期表',21),
        '', 'KRC 当季二代空间全部签约现金租金变化 +6.1%；仅空置不超过12个月的子集为 +15.6%，不能挑后一项代表全部租赁。2027到期 ABR $38.087m（5.0%），其中湾区 $1.668m、Seattle $5.684m；包含合并合伙物业100%，不直接与 HPP 权益份额比较。'+link('krc_2026q2_supplement','KRC租赁及分区到期表',24),
        '', 'KRC 6月入住率77.0%、出租率81.5%，仍有明显闲置；排除KOP 2后入住率80.8%，不能把组合变动当成同店退租。HPP六月图中2027有抵押债务份额 $103.195m、无抵押 $400m；KRC六月2027债务到期含摊还 $249.125m。两者范围不同，且HPP后续展期/要约、KRC七月已偿还的 $200m 2026票据必须另行桥接，不能机械沿用旧墙。'+link('hpp_2026q2_supplement','HPP债务图',14)+'；'+link('krc_2026q2_supplement','KRC债务图及期后偿债注释',39),
        '',table(['CBRE Q2市场','总空置率','直接可租率','转租可租率','净吸纳 sqft','直接挂牌租金 $/sf/年'],
            [[g,f'{get("OFFICE_MARKET","total_vacancy",geo=g):.1f}%',f'{get("OFFICE_MARKET","direct_availability",geo=g):.1f}%',
              f'{get("OFFICE_MARKET","sublease_availability",geo=g):.1f}%',f'{get("OFFICE_MARKET","net_absorption",geo=g):,.0f}',
              f'{get("OFFICE_MARKET","direct_asking_rent",geo=g):.2f}'] for g in ['Puget Sound','San Francisco']]),
        'CBRE 的两个市场当季净吸纳都为正，旧的线性需求崩塌叙事需要修正。直接可租率不是直接空置率；挂牌租金不是扣优惠后的有效租金。免费期、市场 TI、有效租金缺失已列入 coverage_gaps；San Francisco 市場不是整个湾区，Silicon Valley 市场报告仍待补。'+link('cbre_puget_2026q2','Puget Sound',5)+'；'+link('cbre_sf_2026q2','San Francisco',5),
        '', '### 不能沿用六月到期表的后续事件', '',
        '- HPP 9月披露 Hollywood Media Portfolio 总额 $1.1bn CMBS 延至 2027-11-09，并有储备金/现金流归集要求。$1.1bn 是JV毛额，不能直接作为 HPP 净债务份额。'+link('hpp_hollywood_extension','展期公告'),
        '- 9月出售 875/899 Howard；加上 North San Jose 的 2001 Gateway，Q3出售总额 $90.5m。6月租约到期表需要按出售物业桥接，当前未计算更新后净到期额。'+link('hpp_howard_sale','出售公告'),
        '- 10月5日发起最高 $200m 的2027/2028债券现金要约，尚不视为已偿债。'+link('hpp_tender','要约公告'),
        '', '## 7. 上一版遗漏了什么', '',
        table(['类别','本轮发现','可得性/处理'],[
            ['当时已有但漏读','WAFD资金/利率、COLB EX99 office地理及到期披露','7月发布，9/1截点可见；本轮纳入'],
            ['当时尚未知','9/7 WAFD交易公告；HPP9月展期/出售与10月要约','按各自available_at加入，禁止回填9/1'],
            ['虽有数据但未纳入判断','股价已反映多少、PPNR与资金结构、业主租赁改善','补入市场层与反向证据；无法仅凭股价判断风险完全计价'],
            ['目前仍无法解释','September长窗所有异常回报、AI特定贡献、精确地区净损失','残差不归因；对照、资产映射、资本桥仍待建立']]),
        '', '## 8. 下一窗口与未完成项', '',
        '下一轮首先补 WAFD/COLB 新季度披露：借款/存款迁移、NIM/PPNR、criticized→classified 的分项变化，以及合并审批和正式交易材料。同步复核 HPP 债券要约结果和出售物业后的2027租约/净债务到期桥。未经资料确认，不把预计EPS增厚、偿债或信用迁移记为事实。',
        '', '对照登记已保存 4 家银行与 4 个 metro 的候选队列和禁止按事后收益筛选的规则；**基础特征和低科技暴露尚未核实，没有有效匹配对照**。该设计于10月7日登记，不能包装成9月之前预注册的实验。现有手工城市0.7权重仅留在旧住宅情景，不进入新的AI因果结论。',
        '', '仍需：2024起10-K/Q与8-K附件完整回填（本环境SEC直连403，已用发行人IR补关键文件）；贷款floors/完整FHLB与批发融资定义；住宅成交与就业序列；对照特征及前趋势；物业/租户/贷款映射；抵押品、RefiGap、税后资本桥与交易成本。第一、二批的全部验收条件尚未满足。',
        '', '## 9. 复现与审计', '',
        f'- 执行ID：`{run_id}`；代码版本：`{version}`。',
        '- `python scripts/research_sources.py` 下载文档；`python scripts/market_replay.py --end 2026-10-06` 重建行情；`python scripts/research_v2.py` 校验并生成本报告。',
        '- 数值录入仍需人工读表；脚本验证哈希、页码、数字存在、单位/版本、截点与计算边界，不声称已全自动理解SEC。图中地理/到期数值经视觉核对。',
        '- 首轮文件、字节哈希和原始URL见 source_manifest；旧SEC缓存的原下载时间未知，明确为null。每项 derived 指标有输入ID；源文件变更必须重新核查锁，不能刷新下载后沿用旧解读。',
        '- raw文件不入Git；另一台电脑可直接读已跟踪输出，重算需下载相同哈希。源站替换旧文件会导致失败，而不是悄悄使用新版本。']
    (OUT/'research_report_zh.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
