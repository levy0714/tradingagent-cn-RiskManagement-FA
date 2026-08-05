# -*- coding: utf-8 -*-
"""分析单只 A 股(融合版)并生成 PDF 报告。

用法:
    python analyze_one.py 600010                # 分析今天
    python analyze_one.py 600010 --date 2026-07-31
"""
import os
import sys
import argparse
import copy
from datetime import datetime

os.environ.setdefault("EM_MIN_INTERVAL", "1.5")

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJ, ".env"))
except Exception:
    pass

from tradingagents.graph.trading_graph import TradingAgentsGraph  # noqa: E402
from tradingagents.default_config import DEFAULT_CONFIG          # noqa: E402
from web.pdf_export import generate_pdf                           # noqa: E402



def _is_etf(code: str) -> bool:
    """ETF 代码检测:沪 51/56/58 开头,深 15 开头。ETF 不跑游资/解禁角色。"""
    return code.startswith("15") or code.startswith(("51", "56", "58"))


def main():
    ap = argparse.ArgumentParser(description="分析单只 A 股并生成 PDF(融合版)")
    ap.add_argument("ticker", help="6 位股票代码,如 600010")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="分析日期,默认今天")
    ap.add_argument("--out", default=None, help="PDF 输出路径")
    args = ap.parse_args()

    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(
        {
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-v4-pro",
            "quick_think_llm": "deepseek-v4-flash",
            "output_language": "Chinese",
            "results_dir": os.path.join(PROJ, "results", args.ticker),
            "memory_log_path": os.path.join(PROJ, "results", args.ticker, "memory_log.md"),
            "checkpoint_enabled": False,
        }
    )
    os.makedirs(cfg["results_dir"], exist_ok=True)

    print(f"[MAIN] 开始分析 {args.ticker} @ {args.date} (融合版)", flush=True)
    graph_kwargs = {}
    if _is_etf(args.ticker):
        graph_kwargs["selected_analysts"] = ["market", "social", "news", "fundamentals", "policy"]
        print("[MAIN] ETF 检测: 精简角色(市场/舆情/新闻/基本面/政策, 不含游资/解禁)", flush=True)
    ta = TradingAgentsGraph(debug=False, config=cfg, **graph_kwargs)
    final_state, signal = ta._run_graph(args.ticker, args.date)
    print(f"[SIGNAL] {args.ticker}: {signal}", flush=True)

    out = args.out or os.path.join(cfg["results_dir"], f"{args.ticker}_{args.date}.pdf")

    # 基本面图表:先生成 CSV + 三图 PNG(失败不阻塞主报告)
    charts_dir = os.path.join(cfg["results_dir"], args.ticker)
    os.makedirs(charts_dir, exist_ok=True)
    try:
        from gen_finance_charts import export_csvs, run_charts

        export_csvs(args.ticker, charts_dir)
        pngs = run_charts(args.ticker, charts_dir)
        print(f"[CHARTS] 三图已生成: {len(pngs)} 张", flush=True)
    except Exception as e:
        print(f"[CHARTS] 图表生成跳过(不影响主报告): {str(e)[:120]}", flush=True)

    pdf_bytes = generate_pdf(final_state, args.ticker, args.date, str(signal), charts_dir=charts_dir)
    with open(out, "wb") as f:
        f.write(pdf_bytes)
    print(f"[PDF] {out} ({len(pdf_bytes)} bytes)", flush=True)
    print("[DONE]", flush=True)


if __name__ == "__main__":
    main()
