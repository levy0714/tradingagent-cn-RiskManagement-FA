# -*- coding: utf-8 -*-
"""并行分析多只 A 股股票:每只股票一条独立流水线(7分析师→辩论→风控→决策),多只同时跑。

用法:
    python run_parallel.py 600519 000858 300750                # 默认分析今天
    python run_parallel.py 600519 000858 --date 2026-07-30     # 指定日期
    python run_parallel.py 600519 000858 300750 --workers 3    # 指定并行数
"""
import os
import sys
import argparse
import copy
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# 必须在 import tradingagents 之前设置:调大东财限流间隔,降低多线程竞态触发风控的风险
os.environ.setdefault("EM_MIN_INTERVAL", "1.5")

PROJ = os.path.dirname(os.path.abspath(__file__))

# 显式加载项目 .env(项目代码本身不自动加载 dotenv)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(PROJ, ".env"))
except Exception:
    pass
sys.path.insert(0, PROJ)

from tradingagents.graph.trading_graph import TradingAgentsGraph  # noqa: E402
from tradingagents.default_config import DEFAULT_CONFIG          # noqa: E402



def _is_etf(code: str) -> bool:
    """ETF 代码检测:沪 51/56/58 开头,深 15 开头。ETF 不跑游资/解禁角色。"""
    return code.startswith("15") or code.startswith(("51", "56", "58"))


def build_config(ticker: str) -> dict:
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(
        {
            "llm_provider": "deepseek",
            "deep_think_llm": "deepseek-v4-pro",
            "quick_think_llm": "deepseek-v4-flash",
            "output_language": "Chinese",
            "results_dir": os.path.join(PROJ, "results", ticker),
            "memory_log_path": os.path.join(PROJ, "results", ticker, "memory_log.md"),
            "checkpoint_enabled": False,
        }
    )
    return cfg


def analyze_one(ticker: str, trade_date: str):
    try:
        cfg = build_config(ticker)
        graph_kwargs = {}
        if _is_etf(ticker):
            graph_kwargs["selected_analysts"] = ["market", "social", "news", "fundamentals", "policy"]
        ta = TradingAgentsGraph(debug=False, config=cfg, **graph_kwargs)
        result = ta.propagate(ticker, trade_date)
        print(f"[DONE] {ticker}: {result}", flush=True)
        return ticker, True, result
    except Exception as e:
        print(f"[FAIL] {ticker}: {type(e).__name__}: {e}", flush=True)
        traceback.print_exc()
        return ticker, False, str(e)


def main():
    ap = argparse.ArgumentParser(description="并行分析多只 A 股股票")
    ap.add_argument("tickers", nargs="+", help="6 位股票代码,如 600519 000858")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="分析日期,默认今天")
    ap.add_argument("--workers", type=int, default=None, help="并行数,默认 min(3, 股票数)")
    args = ap.parse_args()

    workers = args.workers or min(3, len(args.tickers))
    print(f"[MAIN] 并行分析 {len(args.tickers)} 只: {args.tickers} | workers={workers} | date={args.date}", flush=True)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(analyze_one, t, args.date): t for t in args.tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                fut.result()
            except Exception as e:
                print(f"[UNEXPECTED] {t}: {e}", flush=True)
    print(f"[MAIN] 全部完成。报告目录: {os.path.join(PROJ, 'results', '<ticker>')}", flush=True)


if __name__ == "__main__":
    main()
