# A-Share Analysis Discipline(完整版)

基于 TradingAgents-astock 的 **A 股完整多 Agent 分析系统**,注入严谨的分析纪律:信息源分级、财报五源换源、坏账账龄分析、隐患扫描、标注三图与可点击目录 PDF。**下载即用。**

## 功能

- **7 位分析师**:市场 → 情绪 → 新闻 → 基本面 → 政策 → 游资 → 解禁 → 质量门控 → 交易员 → 组合经理(最终决策)
- **信息源严谨**:新闻分级(官方>权威媒体>门户>自媒体)、政策结论必须附官方原文 URL、自媒体仅作情绪参考
- **财报不摆烂**:五源换源链(新浪→东财→同花顺→巨潮→全网搜索),全挂才报失败并列明各源原因
- **坏账账龄分析**:自动下载年报/中报 PDF,解析应收账款账龄 6 段 + 计提充分性判断
- **隐患扫描**:21 项财务排雷清单,每份报告默认输出
- **PDF 报告**:可点击目录、完整网格表格、风险红色标识、基本面章节内嵌三图(matplotlib 标注)
- **原生适配 DeepSeek**(deepseek-v4-flash / deepseek-v4-pro),也支持 OpenAI/Gemini 等主流模型

## 安装(约 5 分钟)

```bash
# 1. 需要 Python 3.10+
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2. 安装依赖(大陆网络建议加 -i https://pypi.tuna.tsinghua.edu.cn/simple)
pip install -r requirements.txt

# 3. 配置你的 LLM API key
cp .env.example .env
# 编辑 .env,填入你的 key(至少一个):
#   DEEPSEEK_API_KEY=sk-xxxx      (推荐,本项目原生适配)
#   OPENAI_API_KEY=sk-xxxx
```

## 运行

```bash
# 单只股票分析(输出 PDF 到 results/<代码>/)
python analyze_one.py 000932

# 多只股票并行
python run_parallel.py 600010 000932

# 坏账账龄分析(单独跑)
python tradingagents/agents/utils/aging_tools.py 000932

# 标注三图(单独跑)
python plot_finance_py.py 000932
```

输出:`.pdf` 报告(含目录/三图/风险标识/隐患扫描)+ `results/<代码>/` 下分析日志。

## 使用前:功能询问(按你的环境降级)

1. **图表**:有 MATLAB 吗?没有的话有 matplotlib 吗?都没有的话,要不要装?不装就不画图,其余功能不受影响。
2. **账龄**:要不要下载近三年(半)年报分析账龄?如果不要,这项就不做——但坏账信息只存在于年报/中报附注,不做账龄分析,5 年以上大额应收、账龄滚动恶化这类风险是看不见的。

## 目录

```
├── tradingagents/          # 核心框架(agents/graph/dataflows/llm_clients)
│   └── agents/utils/       #   工具:aging_tools(账龄)、signal_data_tools(资金流/龙虎榜)等
├── web/                    # PDF 导出(pdf_export/stock_display;网页 UI 已移除)
├── analyze_one.py          # 单股分析入口
├── run_parallel.py         # 多股并行分析
├── gen_finance_charts.py   # 三图 + PDF 合并
├── plot_finance_py.py      # matplotlib 标注三图
├── red_flag_scan.md        # 隐患扫描 21 条
├── docs/                   # 方法论(纪律/数据源/接入说明)
├── tests/                  # pytest 测试
├── .env.example            # LLM key 配置模板
└── requirements.txt
```

## 测试

```bash
pip install pytest
python -m pytest tests/ -q
```

## 免责声明

本仓库仅供**学习研究与技术演示**,不构成任何投资建议。投资决策请咨询持牌专业机构;使用本仓库产生的任何损失由使用者自行承担。

## 许可

MIT。框架衍生自 [TradingAgents-astock](https://github.com/simonlin1212/TradingAgents-astock)(基于 [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents));原框架文档见 `README-UPSTREAM.md`。
