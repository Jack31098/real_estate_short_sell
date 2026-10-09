import { Stack, H1, H2, Text, Table, Row, Stat, TextInput, useState, useHostTheme, Divider, Link } from "cursor/canvas";

const CONTRACT = "https://www.sec.gov/Archives/edgar/data/1482512/000148251225000139/hpp-fifthamendmenttocred.htm";
const Q2 = "https://www.sec.gov/Archives/edgar/data/1482512/000148251226000069/hpp-20260630.htm";
const evidence = [
  ["6 月底现金 / 未用 revolver", "$80.760m / $795.250m", "已披露；restricted cash $24.659m 不可加入 unrestricted cash"],
  ["2026 年末承诺到期", "$333.250m", "2027 仅剩 $462.0m；基础到期 2028 年末，2029 含附条件展期"],
  ["已出售物业毛价", "$90.5m", "Gateway $25.0m + Howard $65.5m；净入账现金、还债和出售 NOI 未闭合"],
  ["Hollywood 展期", "至 2027-11-09", "$1.1bn JV 债务没有消失；$20m JV 准备 + excess cash sweep"],
  ["2027 HPP share 到期桥", "$1,033.962m", "六月基线加已执行展期；不与合并现金直接相减"],
  ["tender 截点状态", "尚未到截止时间", "截止 10 月 9 日 17:00 EDT，预期 10 月 14 日结算；实际接受额与资金来源未知"],
  ["2027 已卖 Glu 租金移除", "$5.637567m ABR", "$66.099838m → $60.462271m；不是 NOI，也不是完整当前租约表"],
];

export default function HPPLiquidityAudit(){
  const theme=useHostTheme();
  const [ratio,setRatio]=useState("1.6"),[charges,setCharges]=useState("0");
  const r=Number(ratio),d=Number(charges)/100;
  const valid=ratio.trim()!=="" && charges.trim()!=="" && Number.isFinite(r) && r>0 && Number.isFinite(d) && d>-1;
  const headroom=valid ? 100*(1-1.5*(1+d)/r) : NaN;
  return <Stack style={{maxWidth:1080,margin:"0 auto",padding:24,gap:22,color:theme.text.primary}}>
    <H1>HPP：先约束现金与契约，再求联合估值</H1>
    <Text>公开证据核验 · 截至 2026-10-09 12:10:59 PDT。金额为百万美元。旧的 456 个证券收益情景保持快照。</Text>
    <Row style={{flexWrap:"wrap",gap:24}}>
      <Stat label="当前可动用现金" value="尚未闭合"/>
      <Stat label="Q2 fixed-charge coverage" value="1.6x / 1.5x"/>
      <Stat label="当前 2027 融资缺口" value="尚未闭合"/>
    </Row>
    <H2>6.25% 的正确读法</H2>
    <Text>过去连续 12 个月的契约 Adjusted EBITDA / Fixed Charges。分母含规定的利息、非到期大额本金及合资格已付或应计优先分配；口径不同于季度 NOI 或现金 adjusted EBITDAre。</Text>
    <Row style={{alignItems:"flex-end",flexWrap:"wrap",gap:20}}>
      <Stack><Text>起始比率（倍，披露 1.6）</Text><TextInput type="number" value={ratio} onChange={setRatio}/></Stack>
      <Stack><Text>分母变化（%，假设）</Text><TextInput type="number" value={charges} onChange={setCharges}/></Stack>
      <Stat label="分子下降至等于 1.5x（%）" value={valid ? headroom.toFixed(4)+"%" : "输入有效数字"}/>
    </Row>
    <Text>1 − 1.5 × (1 + 分母变动) / 起始比率。分母 +5% 时，分子余量为 1.5625%；负值表示分子需要增长。到等号不等于低于最低值。这不是 NOI 违约线。</Text>
    <Text>1.6 只披露一位小数；如果按最近 0.1 四舍五入，余量可在 3.226% 至小于 9.091%（舍入规则未核实）。Q2 窗口另有与 2025 Projections 一致的备考分母要求，未取得填好的合规计算底稿。</Text>
    <Divider/>
    <H2>资金桥：可核对的事实与剩余约束</H2>
    <Table headers={["事项","已披露 / 派生值","经济约束"]} rows={evidence}/>
    <Text>签署合同的 $125m 最低 liquidity 以 commitments 超过 $600m 触发。新闻稿的 borrowings 措辞不同，以合同为准。借 revolver 是现金与未用额度互换，不会增加总 liquidity；受限现金与 JV sweep 资金不能自动用于母公司。</Text>
    <Text>Article X 违约不能自动套用一般条款的 30 天补救期；未确认自动 equity cure。任何 EOD 下的上游分配有契约限制，不能假设优先股一定继续付现金。这里没有认定当前违约。</Text>
    <H2>联合估值的下一步</H2>
    <Text>同一 2027–2030 租金、面积、入住率、免费期 → NOI → TI/LC/capex → 融资、出售、契约 → JV 与母公司分层回收 → 优先股现金派息 / 累计欠息 / 回收，以及普通股残值。</Text>
    <Text>reverse NAV 反求当前价格所需的经营复苏。10-Q 已找到 10.223269m pre-funded warrants，不能只用 54.267530m 六月普通股；65.684497m 季度 common/OP units 加权平均也不是十月完全摊薄分母。还需核对 OP 单位、奖励、外部优先单位及 JV / 母公司 claims。</Text>
    <Text>第三项借券数量、费用、价差与召回风险尚待券商证据。前两项公开研究继续；未验证执行收益。Q3 业绩计划 11 月 5 日发布；未创建自动监控。</Text>
    <Divider/>
    <Row style={{gap:16,flexWrap:"wrap"}}><Link href={CONTRACT}>签署契约与红线原件</Link><Link href={Q2}>Q2 10-Q</Link><Link href="https://investors.hudsonpacificproperties.com/investor-resources/press-releases/default.aspx">发行人事件披露</Link></Row>
  </Stack>;
}
