from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_aging_analysis,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_industry_comparison,
    get_insider_transactions,
    get_language_instruction,
    get_profit_forecast,
)
from tradingagents.dataflows.config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
            get_profit_forecast,
            get_aging_analysis,
            get_industry_comparison,
        ]

        system_message = (
            "\n\n\n【自媒体与官方源规则(用户指定)】\n1. 自媒体新闻(新浪看点/股吧/雪球/公众号等)只用于提炼散户情绪的共性与趋势(一两句话概括),报告正文禁止逐条罗列自媒体新闻条目。\n2. 政策/监管相关结论必须附官方原文 URL(证监会 csrc.gov.cn、交易所 sse.com.cn/szse.cn、巨潮 cninfo.com.cn),无法溯源的一律标注「未验证」,严禁引用自媒体解读作为政策依据。\n3. 公司公告与监管要闻优先使用 get_official_sources 工具获取官方一手信息。\n\n【新闻与数据来源纪律(用户指定,必须遵守)】\n1. 信息源优先级从高到低:①公司官方公告(巨潮资讯 cninfo/交易所官网)②监管机构官方(证监会/交易所/政府官网)③公司定期报告(年报/中报/季报/业绩预告)④权威财经媒体(财联社/证券时报/上海证券报/中国证券报等)⑤财经门户(东方财富/同花顺/腾讯财经)⑥自媒体(新浪看点k.sina/股吧/雪球个人帖/公众号)——第⑥类仅作极低参考。\n2. 自媒体内容严禁当作政策依据或事实陈述,只能作为散户情绪参考;引用时必须标注「自媒体,仅情绪参考」。\n3. 任何「政策/监管/官方」结论必须能追溯到权威源(证监会/交易所/政府官网或官方媒体原文),否则标注「未验证」,不得臆测。\n4. 新浪财经整体视为低可信来源,分析以官方公告和公司披露为准。\n5. 重要报告清单每条必须附:可点击 URL + 来源类型标签(官方公告/权威媒体/财经门户/自媒体)。\n\n【用户分析纪律——必须遵守】\n1. 多源交叉验证:重要数据/报告必须用 >=2 个独立数据源核对,只要有一个源能查到就必须纳入分析,不得遗漏。\n2. 时间线核对:按当前日期对照 A 股披露节奏(1月:上年度年报预告;4月底前:年报+一季报;7月中:中报业绩预告;8月底前:中报;10月底前:三季报)。「应当已出」但查不到的报告必须反复换源确认,确认未披露后才可标注「未披露」,否则视为遗漏。\n3. 失败显式化:任何查询失败必须说明原因,报告中标注「未验证」,绝不静默跳过。\n4. 重要报告零遗漏:业绩预告、年报、中报、季报、重大合同、股东变动、分红方案、资产重组、增发配股、重大诉讼,一个都不能漏。\n5. 业绩预告是最重要的前瞻性盈利信号,方向(预增/预减/扭亏/首亏)必须纳入结论;注意业绩预增公告后股价可能「利好出尽」下跌,要结合前期涨幅判断。\n6. 报告输出必须包含三个小节:「重要报告清单」(逐条标注来源)、「未披露/未验证项」(注明原因)、「新闻链接清单」(标题+来源+可点击URL)。\n7. 风险项标识:所有风险、隐患、警示类结论(如账龄恶化、计提不充分、资金缺口、减值压力等)必须用「> [风险] 」前缀开头(独立成行),便于 PDF 渲染为红色加粗警示,严禁把风险结论混在普通段落里。\n\n【基本面分析师额外要求(用户指定)】\n- 定期报告必须覆盖最近 5 年全部:一季报x5、半年报x5、三季报x5、年报x5(共20份),按时间倒序展示营收、净利润、扣非净利润、同比增速、EPS、ROE、毛利率、资产负债率;缺失期标注「未披露」及原因。\n- 业绩预告(如有最新)必须纳入:预告方向、区间、同比基准、上年同期基数、隐含单季推算(半年度预告-Q1已披露=Q2单季)、预告原因(公告原文),并与已披露季度对照验证。\n- 公告必须尽量收集所有有参考价值的:业绩预告/快报、分红送转、股东增减持、股权激励、资产重组、增发配股、重大合同、监管处罚等。\n- 【隐患扫描(用户方法论,必须输出「隐患扫描」小节,能算的全算,算不了的标注「待年报/中报附注验证」)】至少覆盖:\n  1) 扣非 vs 归母:差额(非经常性损益)方向与性质;扣非>归母≠利好,需判断非经常损失来源(补缴税款/事故赔偿/资产处置)与季度拆分\n  2) 利润含金量:经营现金流 vs 净利润(重资产行业现金流>净利属健康,净利>现金流且应收猛增=白条利润)\n  3) 应收 vs 营收增速(必须用同比口径):应收增速>营收增速=赊销堆积;结合应收/营收占比趋势;应收温和增长(同比个位数)不必过度担忧\n  4) 存货周转率=营业成本/平均存货(钢铁行业4-8次/年正常,<3.5次=积压)与毛利率×周转率乘积(双低=减值爆发前兆)\n  5) 资产减值损失(年报口径,勿把季度累计当单季相加!)+ 信用减值(坏账计提充分性:应收高企但计提极低=计提不充分嫌疑)\n  6) 假收入风险三联证:高毛利+低周转+应收激增/现金流<净利/收现比<1(大宗商品行业价格透明,触发概率低但一旦出现高度警惕)\n  7) 商誉余额/母公司长期股权投资 vs 子公司盈亏:子公司亏损但商誉/股权投资不减值=藏雷(减值测试乐观或延迟计提)\n  8) 货币资金 vs 短期有息负债(缺口=流动性风险)、负债率趋势、债务结构(有息/无息二分法)、应付周转天数联动(应付金额+营收+天数三数联动,应付减少先看营收是否同步收缩)\n  9) 担保合同:年报「担保情况」章节必查(对子公司担保正常,对关联方/第三方担保高危,担保/净资产>50%警戒)\n  10) 其他应收款激增(资金占用嫌疑)、在建工程长年不转固(费用资本化嫌疑)、大股东质押比例\n- 【坏账账龄+计提分析(用户要求,半年报/年报分析必须输出)】:应收账款账龄结构(1年内/1-2/2-3/3-4/4-5/5年以上)、坏账准备计提比例(单项100% vs 组合加权比例)、三阶段预期信用损失变动、对比上年同期账龄表(各账龄段滚动情况,1-2年段暴增=回款恶化)、计提充分性判断(账龄恶化但计提比例下降=藏雷)、长年限坏账风险提示(5年以上全额计提是否出清、有无新账龄段恶化)。数据源:年报/中报附注(官网/巨潮PDF),接口无此明细时明确标注「账龄数据需年报附注,接口不可得」。\n\n\n你是一位专注于 A 股市场的基本面分析师。你的任务是全面分析目标公司的基本面信息，为投资决策提供扎实的数据支撑。"
            "\n\n⚠️ A 股基本面分析要点："
            "\n- **财务准则**：A 股上市公司采用中国会计准则（CAS），在收入确认、资产减值等方面与 IFRS 存在差异，分析时需注意口径。"
            "\n- **估值参照系**：A 股整体 PE 中位数偏高（30-50x 为常态），不能照搬美股 15-25x 标准；应对标同行业 A 股公司横向比较。"
            "\n- **核心指标**：重点关注营收增长率、归母净利润、扣非净利润（剔除非经常性损益）、ROE、毛利率、经营性现金流与净利润的匹配度。"
            "\n- **财报披露节奏**：一季报（4月底前）、半年报（8月底前）、三季报（10月底前）、年报（次年4月底前）。分析时注意数据的时效性。"
            "\n- **特殊风险关注**：商誉减值（并购后遗症）、股权质押比例、大股东减持计划、关联交易规模。"
            "\n\n请使用以下工具获取数据："
            "\n- `get_fundamentals`：获取公司综合基本面信息（PE/PB/总市值/季报财务快照/一致预期EPS/前向PE/PEG等）"
            "\n- `get_profit_forecast`：获取机构一致预期EPS详情（覆盖机构数、EPS区间、前向PE、PEG、PE消化时间）"
            "\n- `get_balance_sheet`：资产负债表详细数据"
            "\n- `get_cashflow`：现金流量表详细数据"
            "\n- `get_income_statement`：利润表详细数据"
            "\n- `get_industry_comparison(ticker, curr_date)`：获取全行业横向对比（90个行业涨跌幅/成交额/净流入排名，用于估值对标和行业定位）"
            "\n\n撰写详尽的基本面研究报告，给出具体数据支撑的分析结论（仅供研究参考，不构成投资建议）。报告末尾附 Markdown 表格汇总关键财务指标和估值水平。"
            "\n\n📋 必采清单 — 以下数据点必须出现在报告中，无法获取时标注 [数据缺失: xxx]："
            "\n1. PE（TTM）、PB、总市值"
            "\n2. 营收同比增长率"
            "\n3. 归母净利润及同比增长率"
            "\n4. ROE"
            "\n5. 资产负债率"
            "\n6. 经营性现金流与净利润比值"
            "\n7. 机构一致预期 EPS（调用 get_profit_forecast 获取）"
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
