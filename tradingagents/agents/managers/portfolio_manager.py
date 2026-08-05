"""Portfolio Manager: synthesises the risk-analyst debate into the final decision.

Uses LangChain's ``with_structured_output`` so the LLM produces a typed
``PortfolioDecision`` directly, in a single call.  The result is rendered
back to markdown for storage in ``final_trade_decision`` so memory log,
CLI display, and saved reports continue to consume the same shape they do
today.  When a provider does not expose structured output, the agent falls
back gracefully to free-text generation.
"""

from __future__ import annotations

from tradingagents.agents.schemas import PortfolioDecision, render_pm_decision
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_portfolio_manager(llm):
    structured_llm = bind_structured(llm, PortfolioDecision, "Portfolio Manager")

    def portfolio_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])

        trader_plan = state["trader_investment_plan"]

        # Collect analyst reports (risk debate & research manager removed)
        report_map = {
            "Market Analysis Report": state.get("market_report", ""),
            "Sentiment Analysis Report": state.get("sentiment_report", ""),
            "News Analysis Report": state.get("news_report", ""),
            "Fundamentals Analysis Report": state.get("fundamentals_report", ""),
            "Policy Analysis Report": state.get("policy_report", ""),
            "Hot Money / Capital Flow Report": state.get("hot_money_report", ""),
        }
        analyst_reports = "\n\n".join(f"{k}:\n{v}" for k, v in report_map.items() if v)
        risk_debate_state = state.get("risk_debate_state") or {}

        past_context = state.get("past_context", "")
        lessons_line = (
            f"- Lessons from prior decisions and outcomes:\n{past_context}\n"
            if past_context
            else ""
        )

        prompt = f"""


【自媒体与官方源规则(用户指定)】
1. 自媒体新闻(新浪看点/股吧/雪球/公众号等)只用于提炼散户情绪的共性与趋势(一两句话概括),报告正文禁止逐条罗列自媒体新闻条目。
2. 政策/监管相关结论必须附官方原文 URL(证监会 csrc.gov.cn、交易所 sse.com.cn/szse.cn、巨潮 cninfo.com.cn),无法溯源的一律标注「未验证」,严禁引用自媒体解读作为政策依据。
3. 公司公告与监管要闻优先使用 get_official_sources 工具获取官方一手信息。

【新闻与数据来源纪律(用户指定,必须遵守)】
1. 信息源优先级从高到低:①公司官方公告(巨潮资讯 cninfo/交易所官网)②监管机构官方(证监会/交易所/政府官网)③公司定期报告(年报/中报/季报/业绩预告)④权威财经媒体(财联社/证券时报/上海证券报/中国证券报等)⑤财经门户(东方财富/同花顺/腾讯财经)⑥自媒体(新浪看点k.sina/股吧/雪球个人帖/公众号)——第⑥类仅作极低参考。
2. 自媒体内容严禁当作政策依据或事实陈述,只能作为散户情绪参考;引用时必须标注「自媒体,仅情绪参考」。
3. 任何「政策/监管/官方」结论必须能追溯到权威源(证监会/交易所/政府官网或官方媒体原文),否则标注「未验证」,不得臆测。
4. 新浪财经整体视为低可信来源,分析以官方公告和公司披露为准。
5. 重要报告清单每条必须附:可点击 URL + 来源类型标签(官方公告/权威媒体/财经门户/自媒体)。

【用户分析纪律——必须遵守】
1. 多源交叉验证:重要数据/报告必须用 >=2 个独立数据源核对,只要有一个源能查到就必须纳入分析,不得遗漏。
2. 时间线核对:按当前日期对照 A 股披露节奏(1月:上年度年报预告;4月底前:年报+一季报;7月中:中报业绩预告;8月底前:中报;10月底前:三季报)。"应当已出"但查不到的报告必须反复换源确认,确认未披露后才可标注"未披露",否则视为遗漏。
3. 失败显式化:任何查询失败必须说明原因,报告中标注"未验证",绝不静默跳过。
4. 重要报告零遗漏:业绩预告、年报、中报、季报、重大合同、股东变动、分红方案、资产重组、增发配股、重大诉讼,一个都不能漏。
5. 业绩预告是最重要的前瞻性盈利信号,方向(预增/预减/扭亏/首亏)必须纳入结论;注意业绩预增公告后股价可能"利好出尽"下跌,要结合前期涨幅判断。
6. 报告输出必须包含三个小节:「重要报告清单」(逐条标注来源)、「未披露/未验证项」(注明原因)、「新闻链接清单」(标题+来源+可点击URL)。\n7. 风险项标识:所有风险、隐患、警示类结论(如账龄恶化、计提不充分、资金缺口、减值压力等)必须用「> [风险] 」前缀开头(独立成行),便于 PDF 渲染为红色加粗警示,严禁把风险结论混在普通段落里。
As the Portfolio Manager, synthesize the analysts' reports and the trader's proposal, then deliver the final trading decision.

{instrument_context}

---

**A-Stock Trading Constraints** (must factor into your decision):
- T+1 settlement: shares bought today cannot be sold until the next trading day
- Daily price limits: main board ±10%, STAR/ChiNext ±20%, ST stocks ±5%
- Minimum lot size: 100 shares (1 手) for main board; 200 shares for STAR/ChiNext
- Trading hours: 09:30-11:30, 13:00-15:00 (Beijing time)
- ST/delisting risk: ST or *ST status signals regulatory warning; factor into position sizing
- Margin eligibility: not all A-shares are margin-eligible; assume cash-only unless stated

---

**Rating Scale** (use exactly one):
- **Buy**: Strong conviction to enter or add to position
- **Overweight**: Favorable outlook, gradually increase exposure
- **Hold**: Maintain current position, no action needed
- **Underweight**: Reduce exposure, take partial profits
- **Sell**: Exit position or avoid entry

**Context:**
- Analyst reports: **{analyst_reports}**
- Trader's transaction proposal: **{trader_plan}**
{lessons_line}

---

Be decisive and ground every conclusion in specific evidence from the analysts.{get_language_instruction()}"""

        final_trade_decision = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_pm_decision,
            "Portfolio Manager",
        )

        new_risk_debate_state = {
            "judge_decision": final_trade_decision,
            "history": risk_debate_state.get("history", ""),
            "aggressive_history": risk_debate_state.get("aggressive_history", ""),
            "conservative_history": risk_debate_state.get("conservative_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Judge",
            "current_aggressive_response": risk_debate_state.get("current_aggressive_response", ""),
            "current_conservative_response": risk_debate_state.get("current_conservative_response", ""),
            "current_neutral_response": risk_debate_state.get("current_neutral_response", ""),
            "count": risk_debate_state.get("count", 0),
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": final_trade_decision,
        }

    return portfolio_manager_node
