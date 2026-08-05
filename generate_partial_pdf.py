# -*- coding: utf-8 -*-
"""从「最终投资建议」章节开始生成 PDF(前面的分析师报告不进 PDF)。
用法: python generate_partial_pdf.py <ticker> [date]
"""
import json
import sys
import argparse
import io
import os
from datetime import datetime

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)

from web.pdf_export import _ReportPDF, _collect_sections  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = ap.parse_args()

    state_path = os.path.join(
        PROJ, "results", args.ticker, args.ticker,
        "TradingAgentsStrategy_logs", f"full_states_log_{args.date}.json",
    )
    state = json.load(io.open(state_path, encoding="utf-8"))
    signal = str(state.get("final_trade_decision", "Hold"))

    sections = _collect_sections(state, args.ticker)
    keep, started = [], False
    for title, content in sections:
        if title == "最终投资建议":
            started = True
        if started:
            keep.append((title, content))
    print("PDF sections kept:", [t for t, _ in keep], flush=True)

    pdf = _ReportPDF(args.ticker, args.date, signal, state)
    pdf.add_cover()
    for title, content in keep:
        pdf.add_section(title, content)
    out = os.path.join(PROJ, "results", args.ticker, f"{args.ticker}_{args.date}_partial.pdf")
    with open(out, "wb") as f:
        f.write(bytes(pdf.output()))
    print("PARTIAL PDF:", out, flush=True)


if __name__ == "__main__":
    main()
