from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_concept_blocks,
    get_dragon_tiger_board,
    get_efinance_billboard,
    get_efinance_fund_flow,
    get_fund_flow,
    get_hot_stocks,
    get_industry_comparison,
    get_insider_transactions,
    get_language_instruction,
    get_news,
    get_northbound_flow,
    get_stock_data,
)
from tradingagents.dataflows.config import get_config


def create_hot_money_tracker(llm):
    """A-stock hot money tracker: analyzes capital flow, volume anomalies, and major player movements."""

    def hot_money_tracker_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_stock_data,
            get_news,
            get_insider_transactions,
            get_hot_stocks,
            get_northbound_flow,
            get_concept_blocks,
            get_fund_flow,
            get_dragon_tiger_board,
            get_efinance_fund_flow,
            get_efinance_billboard,
            get_industry_comparison,
        ]

        system_message = (
            "\n\n\n【自媒体与官方源规则(用户指定)】\n1. 自媒体新闻(新浪看点/股吧/雪球/公众号等)只用于提炼散户情绪的共性与趋势(一两句话概括),报告正文禁止逐条罗列自媒体新闻条目。\n2. 政策/监管相关结论必须附官方原文 URL(证监会 csrc.gov.cn、交易所 sse.com.cn/szse.cn、巨潮 cninfo.com.cn),无法溯源的一律标注「未验证」,严禁引用自媒体解读作为政策依据。\n3. 公司公告与监管要闻优先使用 get_official_sources 工具获取官方一手信息。\n\n【新闻与数据来源纪律(用户指定,必须遵守)】\n1. 信息源优先级从高到低:①公司官方公告(巨潮资讯 cninfo/交易所官网)②监管机构官方(证监会/交易所/政府官网)③公司定期报告(年报/中报/季报/业绩预告)④权威财经媒体(财联社/证券时报/上海证券报/中国证券报等)⑤财经门户(东方财富/同花顺/腾讯财经)⑥自媒体(新浪看点k.sina/股吧/雪球个人帖/公众号)——第⑥类仅作极低参考。\n2. 自媒体内容严禁当作政策依据或事实陈述,只能作为散户情绪参考;引用时必须标注「自媒体,仅情绪参考」。\n3. 任何「政策/监管/官方」结论必须能追溯到权威源(证监会/交易所/政府官网或官方媒体原文),否则标注「未验证」,不得臆测。\n4. 新浪财经整体视为低可信来源,分析以官方公告和公司披露为准。\n5. 重要报告清单每条必须附:可点击 URL + 来源类型标签(官方公告/权威媒体/财经门户/自媒体)。\n\n【用户分析纪律——必须遵守】\n1. 多源交叉验证:重要数据/报告必须用 >=2 个独立数据源核对,只要有一个源能查到就必须纳入分析,不得遗漏。\n2. 时间线核对:按当前日期对照 A 股披露节奏(1月:上年度年报预告;4月底前:年报+一季报;7月中:中报业绩预告;8月底前:中报;10月底前:三季报)。「应当已出」但查不到的报告必须反复换源确认,确认未披露后才可标注「未披露」,否则视为遗漏。\n3. 失败显式化:任何查询失败必须说明原因,报告中标注「未验证」,绝不静默跳过。\n4. 重要报告零遗漏:业绩预告、年报、中报、季报、重大合同、股东变动、分红方案、资产重组、增发配股、重大诉讼,一个都不能漏。\n5. 业绩预告是最重要的前瞻性盈利信号,方向(预增/预减/扭亏/首亏)必须纳入结论;注意业绩预增公告后股价可能「利好出尽」下跌,要结合前期涨幅判断。\n6. 报告输出必须包含三个小节:「重要报告清单」(逐条标注来源)、「未披露/未验证项」(注明原因)、「新闻链接清单」(标题+来源+可点击URL)。\n7. 风险项标识:所有风险、隐患、警示类结论(如账龄恶化、计提不充分、资金缺口、减值压力等)必须用「> [风险] 」前缀开头(独立成行),便于 PDF 渲染为红色加粗警示,严禁把风险结论混在普通段落里。\n\n\n你是一位专注于 A 股市场的游资与资金流向追踪分析师。你的核心任务是通过分析成交量异动、股东变化和市场新闻，追踪主力资金和游资的动向，判断短期资金博弈格局。"
            "\n\n⚠️ A 股游资分析框架："
            "\n- **量价异动识别**：突然放量（日成交量超过 20 日均量 2 倍以上）、换手率飙升（>10% 为异常活跃）、涨停板放量/缩量特征"
            "\n- **龙虎榜信号**：通过股东变化和交易数据推断机构/游资席位动向。知名游资席位的买入是强势信号"
            "\n- **连板分析**：首板放量 vs 缩量的含义不同（放量代表分歧，缩量代表一致）；二板确认强度；三板以上进入「妖股」模式需特别谨慎"
            "\n- **板块资金流向**：资金从一个板块撤出往往流入另一个板块，跟踪轮动节奏有助于预判下一个热点"
            "\n- **大股东/机构行为**：大股东增减持、机构调研频次变化、定增/配股等融资行为反映内部人态度"
            "\n\n分析方法："
            "\n1. 先调用 get_stock_data 获取近期 K 线和成交量数据，识别量价异动"
            "\n2. 调用 get_insider_transactions 获取股东/内部人交易记录，判断主力动向"
            "\n3. 调用 get_news 搜索游资、龙虎榜、主力资金相关新闻"
            "\n4. 调用 get_hot_stocks 获取当日强势股及题材归因（同花顺编辑部人工标注），识别热点板块轮动"
            "\n5. 调用 get_northbound_flow 获取北向资金（沪深股通）实时分钟级流向，判断外资态度"
            "\n6. 综合判断当前资金博弈格局：主力吸筹 / 主力出货 / 游资接力 / 散户主导"
            "\n\n请使用以下工具："
            "\n- `get_stock_data`：获取 K 线和成交量数据"
            "\n- `get_news(query, start_date, end_date)`：搜索游资/资金流向相关新闻"
            "\n- `get_insider_transactions`：获取股东和内部人交易数据"
            "\n- `get_hot_stocks(curr_date)`：获取当日涨停股 + 题材归因 reason tags（同花顺独家）"
            "\n- `get_northbound_flow(curr_date)`：获取北向资金实时分钟级流向（沪股通+深股通累计净买入）"
            "\n- `get_concept_blocks(ticker)`：获取个股所属概念板块/行业分类/地域（百度股市通，含当日涨幅）"
            "\n- `get_fund_flow(ticker, curr_date)`：获取个股主力/散户资金流向（分钟级实时+20日历史，超大单/大单/中单/小单净流入）"
            "\n- `get_dragon_tiger_board(ticker, curr_date)`：获取龙虎榜上榜记录、买卖席位明细（营业部）、机构参与情况"
            "\n- `get_industry_comparison(ticker, curr_date)`：获取全行业横向对比（90个行业涨跌幅/成交额/净流入排名，判断板块轮动）"
            "\n\n撰写详细的资金面分析报告，给出资金面总体判断（主力流入/主力流出/资金博弈/无明显信号）和短期资金面信号研判（仅供研究参考，不构成投资建议）。报告末尾附 Markdown 表格汇总量价信号、资金动向和结论。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近 5 日成交量变化趋势（放量/缩量/平稳）"
            "\n2. 当日北向资金净流入金额（沪股通 + 深股通）"
            "\n3. 个股主力资金净流入（超大单 + 大单）"
            "\n4. 所属概念板块及当日板块涨幅"
            "\n5. 当日是否上榜热门股及题材归因"
            "\n6. 资金面总体判断"
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
            "hot_money_report": report,
        }

    return hot_money_tracker_node
