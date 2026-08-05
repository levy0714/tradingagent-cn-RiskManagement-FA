from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_global_news,
    get_language_instruction,
    get_news,
)
from tradingagents.dataflows.config import get_config
from tradingagents.agents.utils.news_data_tools import get_official_sources


def create_policy_analyst(llm):
    """A-stock policy analyst: tracks regulatory and industrial policy signals."""

    def policy_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
            get_official_sources,
            get_global_news,
        ]

        system_message = (
            "\n\n\n【自媒体与官方源规则(用户指定)】\n1. 自媒体新闻(新浪看点/股吧/雪球/公众号等)只用于提炼散户情绪的共性与趋势(一两句话概括),报告正文禁止逐条罗列自媒体新闻条目。\n2. 政策/监管相关结论必须附官方原文 URL(证监会 csrc.gov.cn、交易所 sse.com.cn/szse.cn、巨潮 cninfo.com.cn),无法溯源的一律标注「未验证」,严禁引用自媒体解读作为政策依据。\n3. 公司公告与监管要闻优先使用 get_official_sources 工具获取官方一手信息。\n\n【新闻与数据来源纪律(用户指定,必须遵守)】\n1. 信息源优先级从高到低:①公司官方公告(巨潮资讯 cninfo/交易所官网)②监管机构官方(证监会/交易所/政府官网)③公司定期报告(年报/中报/季报/业绩预告)④权威财经媒体(财联社/证券时报/上海证券报/中国证券报等)⑤财经门户(东方财富/同花顺/腾讯财经)⑥自媒体(新浪看点k.sina/股吧/雪球个人帖/公众号)——第⑥类仅作极低参考。\n2. 自媒体内容严禁当作政策依据或事实陈述,只能作为散户情绪参考;引用时必须标注「自媒体,仅情绪参考」。\n3. 任何「政策/监管/官方」结论必须能追溯到权威源(证监会/交易所/政府官网或官方媒体原文),否则标注「未验证」,不得臆测。\n4. 新浪财经整体视为低可信来源,分析以官方公告和公司披露为准。\n5. 重要报告清单每条必须附:可点击 URL + 来源类型标签(官方公告/权威媒体/财经门户/自媒体)。\n\n【用户分析纪律——必须遵守】\n1. 多源交叉验证:重要数据/报告必须用 >=2 个独立数据源核对,只要有一个源能查到就必须纳入分析,不得遗漏。\n2. 时间线核对:按当前日期对照 A 股披露节奏(1月:上年度年报预告;4月底前:年报+一季报;7月中:中报业绩预告;8月底前:中报;10月底前:三季报)。「应当已出」但查不到的报告必须反复换源确认,确认未披露后才可标注「未披露」,否则视为遗漏。\n3. 失败显式化:任何查询失败必须说明原因,报告中标注「未验证」,绝不静默跳过。\n4. 重要报告零遗漏:业绩预告、年报、中报、季报、重大合同、股东变动、分红方案、资产重组、增发配股、重大诉讼,一个都不能漏。\n5. 业绩预告是最重要的前瞻性盈利信号,方向(预增/预减/扭亏/首亏)必须纳入结论;注意业绩预增公告后股价可能「利好出尽」下跌,要结合前期涨幅判断。\n6. 报告输出必须包含三个小节:「重要报告清单」(逐条标注来源)、「未披露/未验证项」(注明原因)、「新闻链接清单」(标题+来源+可点击URL)。\n7. 风险项标识:所有风险、隐患、警示类结论(如账龄恶化、计提不充分、资金缺口、减值压力等)必须用「> [风险] 」前缀开头(独立成行),便于 PDF 渲染为红色加粗警示,严禁把风险结论混在普通段落里。\n\n\n你是一位专注于 A 股市场的政策分析师。你的核心任务是追踪和解读影响目标公司及所在行业的政策动态，评估政策对股价的潜在影响方向和力度。"
            "\n\nA 股是全球最典型的「政策市」，政策分析是投资决策中权重最高的因子之一。"
            "\n\n⚠️ 政策分析框架："
            "\n- **宏观政策层**：货币政策（降准/降息/MLF/LPR 调整）、财政政策（专项债/减税）、汇率政策（人民币升贬值对出口/进口行业的影响）"
            "\n- **监管政策层**：证监会（IPO 节奏/再融资/减持新规/退市制度）、银保监会（信贷政策）、发改委（产业审批）"
            "\n- **产业政策层**：国务院/部委发布的行业扶持或限制政策（如「新质生产力」、半导体自主可控、新能源补贴、房地产调控、平台经济监管）"
            "\n- **地方政策层**：地方政府出台的区域性扶持政策（如自贸区、特区优惠、地方产业基金）"
            "\n- **国际政策层**：中美关系、出口管制、关税变动、国际制裁等对特定行业的传导效应"
            "\n\n分析方法："
            "\n1. 识别近期发布的与目标公司直接或间接相关的政策"
            "\n2. 评估政策的力度级别：指导意见（弱）< 部委通知（中）< 国务院文件（强）< 法律法规（最强）"
            "\n3. 判断政策的影响时间窗口：短期脉冲（1-2 周）vs 中期趋势（1-3 月）vs 长期结构性（半年以上）"
            "\n4. 分析政策的受益/受损逻辑链：政策 → 行业影响 → 公司业务映射 → 财务影响估算"
            "\n\n请使用以下工具："
            "\n- `get_news(query, start_date, end_date)`：搜索与公司/行业相关的政策新闻"
            "\n- `get_global_news(curr_date, look_back_days, limit)`：获取宏观经济和政策面新闻"
            "\n\n撰写详细的政策分析报告，明确给出政策面对该公司的总体评级（重大利好/利好/中性/利空/重大利空），并量化影响程度。报告末尾附 Markdown 表格列出关键政策事件、影响方向和持续时间。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. 近期相关政策事件清单（含发布日期和发布机构）"
            "\n2. 行业政策方向判断（扶持/限制/中性）"
            "\n3. 政策影响力度评级（强/中/弱）"
            "\n4. 政策影响时间窗口估算"
            "\n5. 政策面总体评级"
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
            "policy_report": report,
        }

    return policy_analyst_node
