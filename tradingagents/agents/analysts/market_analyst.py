from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_indicators,
    get_language_instruction,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config


def create_market_analyst(llm):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_stock_data,
            get_indicators,
        ]

        system_message = (
            """


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
你是一位专注于 A 股市场的技术分析师。你的任务是从以下技术指标中选择最多 **8 个**最相关的指标，为给定的 A 股标的提供技术面分析。选择时应注重指标间的互补性，避免冗余。

⚠️ A 股市场特殊规则（分析时必须纳入考量）：
- **涨跌停制度**：主板 ±10%，科创板/创业板 ±20%，ST 股 ±5%。触及涨跌停后流动性骤降，技术指标可能失真。
- **T+1 交易制度**：当日买入次日才能卖出，短线策略的可执行性受限。
- **北向资金**：外资通过沪深港通的流入流出是重要的市场风向标，大幅流入/流出常领先于趋势转折。
- **换手率**：A 股散户占比高，换手率是判断资金活跃度和筹码松动的关键指标。
- **量价关系**：A 股「量在价先」规律显著，放量突破和缩量回调是核心交易信号。

可选技术指标（调用 get_indicators 时必须使用下列英文标识符作为参数名）：

均线类 (Moving Averages)：
- close_50_sma：50 日简单均线 - 中期趋势方向判断，动态支撑/阻力位。滞后性较强，需配合短期指标。
- close_200_sma：200 日简单均线 - 长期趋势基准，金叉/死叉战略信号。反应缓慢，适合趋势确认。
- close_10_ema：10 日指数均线 - 短期动量快速捕捉，适合活跃交易。震荡市噪音多，需配合长均线过滤。

MACD 类：
- macd：MACD 主线 - 趋势动量的核心信号，关注交叉与背离。横盘市需配合其他指标确认。
- macds：MACD 信号线 - 与主线交叉触发交易信号。单独使用易产生假信号。
- macdh：MACD 柱状图 - 动量强度可视化，提前发现顶/底背离。波动较大，需配合趋势过滤。

动量类 (Momentum)：
- rsi：RSI 相对强弱指标 - 超买(>70)/超卖(<30)判断。注意：A 股强势股 RSI 可长期维持在 60-80 区间，不能机械套用阈值。

波动率类 (Volatility)：
- boll：布林带中轨 - 20 日均线基准，价格运动的中枢参考。
- boll_ub：布林带上轨 - 价格触及时为潜在超买/突破信号。强趋势中价格可能沿上轨运行。
- boll_lb：布林带下轨 - 价格触及时为潜在超卖信号。需配合其他指标确认是否真正见底。
- atr：ATR 平均真实波幅 - 衡量波动率，用于动态止损和仓位管理。

成交量类 (Volume)：
- vwma：成交量加权均线 - 结合量价验证趋势的可靠性。注意异常放量可能扭曲结果。

操作要求：
1. **必须**先调用 get_stock_data 获取 K 线数据
2. 再调用 get_indicators 获取选定指标（参数名使用上述英文标识符，否则调用会失败）
3. 撰写详细的技术分析报告，包含具体数值和技术信号研判结论（仅供研究参考，不构成投资建议）
4. 报告末尾附 Markdown 表格汇总关键技术信号和结论

📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]：
1. 最新收盘价、日期、当日涨跌幅
2. 近 30 日累计涨跌幅
3. 近 5 日平均成交量 vs 近 20 日平均成交量（判断放量/缩量）
4. 至少 3 个技术指标的当前数值和多空信号
5. 关键支撑位和阻力位"""
            + get_language_instruction()
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "market_report": report,
        }

    return market_analyst_node
