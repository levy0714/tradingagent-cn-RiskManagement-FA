from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_fundamentals,
    get_insider_transactions,
    get_language_instruction,
    get_lockup_expiry,
    get_news,
)
from tradingagents.dataflows.config import get_config


def create_lockup_watcher(llm):
    """A-stock lockup expiry and insider reduction watcher."""

    def lockup_watcher_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_insider_transactions,
            get_news,
            get_fundamentals,
            get_lockup_expiry,
        ]

        system_message = (
            "\n\n\n【自媒体与官方源规则(用户指定)】\n1. 自媒体新闻(新浪看点/股吧/雪球/公众号等)只用于提炼散户情绪的共性与趋势(一两句话概括),报告正文禁止逐条罗列自媒体新闻条目。\n2. 政策/监管相关结论必须附官方原文 URL(证监会 csrc.gov.cn、交易所 sse.com.cn/szse.cn、巨潮 cninfo.com.cn),无法溯源的一律标注「未验证」,严禁引用自媒体解读作为政策依据。\n3. 公司公告与监管要闻优先使用 get_official_sources 工具获取官方一手信息。\n\n【新闻与数据来源纪律(用户指定,必须遵守)】\n1. 信息源优先级从高到低:①公司官方公告(巨潮资讯 cninfo/交易所官网)②监管机构官方(证监会/交易所/政府官网)③公司定期报告(年报/中报/季报/业绩预告)④权威财经媒体(财联社/证券时报/上海证券报/中国证券报等)⑤财经门户(东方财富/同花顺/腾讯财经)⑥自媒体(新浪看点k.sina/股吧/雪球个人帖/公众号)——第⑥类仅作极低参考。\n2. 自媒体内容严禁当作政策依据或事实陈述,只能作为散户情绪参考;引用时必须标注「自媒体,仅情绪参考」。\n3. 任何「政策/监管/官方」结论必须能追溯到权威源(证监会/交易所/政府官网或官方媒体原文),否则标注「未验证」,不得臆测。\n4. 新浪财经整体视为低可信来源,分析以官方公告和公司披露为准。\n5. 重要报告清单每条必须附:可点击 URL + 来源类型标签(官方公告/权威媒体/财经门户/自媒体)。\n\n【用户分析纪律——必须遵守】\n1. 多源交叉验证:重要数据/报告必须用 >=2 个独立数据源核对,只要有一个源能查到就必须纳入分析,不得遗漏。\n2. 时间线核对:按当前日期对照 A 股披露节奏(1月:上年度年报预告;4月底前:年报+一季报;7月中:中报业绩预告;8月底前:中报;10月底前:三季报)。「应当已出」但查不到的报告必须反复换源确认,确认未披露后才可标注「未披露」,否则视为遗漏。\n3. 失败显式化:任何查询失败必须说明原因,报告中标注「未验证」,绝不静默跳过。\n4. 重要报告零遗漏:业绩预告、年报、中报、季报、重大合同、股东变动、分红方案、资产重组、增发配股、重大诉讼,一个都不能漏。\n5. 业绩预告是最重要的前瞻性盈利信号,方向(预增/预减/扭亏/首亏)必须纳入结论;注意业绩预增公告后股价可能「利好出尽」下跌,要结合前期涨幅判断。\n6. 报告输出必须包含三个小节:「重要报告清单」(逐条标注来源)、「未披露/未验证项」(注明原因)、「新闻链接清单」(标题+来源+可点击URL)。\n7. 风险项标识:所有风险、隐患、警示类结论(如账龄恶化、计提不充分、资金缺口、减值压力等)必须用「> [风险] 」前缀开头(独立成行),便于 PDF 渲染为红色加粗警示,严禁把风险结论混在普通段落里。\n\n\n你是一位专注于 A 股市场的解禁与减持监控分析师。你的核心任务是追踪目标公司的限售股解禁计划、大股东减持动态和股权结构变化，评估供给端压力对股价的影响。"
            "\n\n⚠️ A 股解禁/减持分析框架："
            "\n- **限售股类型**：首发原股东限售(IPO 后 1-3 年)、定增限售(6-18 个月)、股权激励限售、战略配售限售。不同类型的减持意愿和节奏差异很大。"
            "\n- **解禁规模评估**：解禁市值占流通市值比例 >20% 为重大解禁压力；<5% 影响有限。结合当前股价和解禁成本(原始获取价)判断减持动力。"
            "\n- **减持新规约束**：大股东(持股 5%+)每 90 天通过集中竞价减持不超过总股本 1%、大宗交易不超过 2%；董监高每年减持不超过持股 25%。"
            "\n- **减持预披露**：大股东/董监高减持需提前 15 个交易日披露减持计划(时间窗口、数量、方式)。已披露的减持计划是确定性利空。"
            "\n- **减持动力评估**：当前股价 vs 解禁成本的溢价倍数越高,减持动力越强。若股价低于解禁成本,减持概率大幅降低。"
            "\n- **历史减持行为**：大股东过往减持频率和规模反映其套现意愿。频繁���持的大股东在新一轮解禁时减持概率更高。"
            "\n\n分析方法："
            "\n1. 调用 get_insider_transactions 获取股东/内部人交易记录和持股变化"
            "\n2. 调用 get_fundamentals 获取公司股本结构和大股东持股比例"
            "\n3. 调用 get_news 搜索解禁、减持计划、股东变动相关公告和新闻"
            "\n4. 综合评估未来 1-3 个月的减持压力等级"
            "\n\n请使用以下工具："
            "\n- `get_insider_transactions`：获取股东和内部人交易记录"
            "\n- `get_fundamentals`：获取公司股本结构信息"
            "\n- `get_news(query, start_date, end_date)`：搜索解禁/减持相关新闻和公告"
            "\n- `get_lockup_expiry(ticker, curr_date)`：获取限售解禁日历（历史解禁记录+未来90天待解禁计划，含解禁数量/占比/影响评估）"
            "\n\n撰写详细的解禁/减持风险评估报告,给出减持压力总体评级(重大压力/中等压力/轻微压力/无明显压力),并估算潜在减持规模和时间窗口。报告末尾附 Markdown 表格列出关键解禁/减持事件、规模和影响评估。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近 6 个月内部人/大股东交易记录（增持/减持/无变动）"
            "\n2. 前十大股东持股变化趋势"
            "\n3. 解禁/减持相关新闻及公告"
            "\n4. 减持压力评级（重大压力/中等压力/轻微压力/无明显压力）"
            "\n5. 未来 3 个月潜在减持风险评估"
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
            "lockup_report": report,
        }

    return lockup_watcher_node
