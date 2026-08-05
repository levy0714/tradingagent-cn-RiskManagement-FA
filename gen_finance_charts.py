# -*- coding: utf-8 -*-
"""基本面图表集成:分析完成后自动画 MATLAB 标注三图并合并进主报告 PDF。
用法: python gen_finance_charts.py <ticker> <main_pdf> [--date YYYY-MM-DD]
依赖: akshare(拉三表)、MATLAB(plot_finance_split.m)、fpdf2、pypdf
"""
import os
import sys
import subprocess
import argparse
from datetime import datetime

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)

import warnings
warnings.filterwarnings("ignore")
import akshare as ak
import pandas as pd

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter


def export_csvs(ticker: str, outdir: str) -> None:
    """拉三表并导出 CSV(覆盖式,文件名固定:fin_income/fin_balance/fin_cashflow.csv)"""
    prefix = "SH" if ticker.startswith(("6", "9")) else "SZ"
    sym = prefix + ticker
    bs = ak.stock_balance_sheet_by_report_em(symbol=sym)
    inc = ak.stock_profit_sheet_by_report_em(symbol=sym)
    cf = ak.stock_cash_flow_sheet_by_report_em(symbol=sym)
    for df in (bs, inc, cf):
        df["REPORT_DATE"] = pd.to_datetime(df["REPORT_DATE"])
    bs_cols = ["REPORT_DATE", "TOTAL_ASSETS", "TOTAL_LIABILITIES", "TOTAL_PARENT_EQUITY",
               "MONETARYFUNDS", "TOTAL_CURRENT_LIAB", "TOTAL_NONCURRENT_LIAB", "INVENTORY", "ACCOUNTS_RECE"]
    inc_cols = ["REPORT_DATE", "OPERATE_INCOME", "TOTAL_OPERATE_INCOME", "NETPROFIT", "PARENT_NETPROFIT",
                "TOTAL_OPERATE_INCOME_YOY", "PARENT_NETPROFIT_YOY", "BASIC_EPS", "OPERATE_COST", "TOTAL_PROFIT"]
    cf_cols = ["REPORT_DATE", "NETCASH_OPERATE", "NETCASH_INVEST", "NETCASH_FINANCE", "END_CCE", "NETPROFIT"]
    bs[[c for c in bs_cols if c in bs.columns]].to_csv(os.path.join(outdir, "fin_balance.csv"), index=False)
    inc[[c for c in inc_cols if c in inc.columns]].to_csv(os.path.join(outdir, "fin_income.csv"), index=False)
    cf[[c for c in cf_cols if c in cf.columns]].to_csv(os.path.join(outdir, "fin_cashflow.csv"), index=False)


def run_charts(ticker: str, outdir: str, forecast: str = None) -> list:
    """生成标注三图:优先 Python(matplotlib),失败回退 MATLAB。返回 PNG 路径列表"""
    # 1) Python/matplotlib
    try:
        import matplotlib  # noqa: F401
        cmd = [sys.executable, os.path.join(PROJ, "plot_finance_py.py"),
               ticker, "--outdir", outdir]
        if forecast:
            cmd += ["--forecast", forecast]
        subprocess.run(cmd, capture_output=True, timeout=600, check=True)
        names = [f"{ticker}_利润_季度折线_含Q2预估.png",
                 f"{ticker}_资产负债_含Q2标注.png",
                 f"{ticker}_现金流_含Q2标注.png"]
        pngs = [os.path.join(outdir, n) for n in names]
        if all(os.path.exists(p) for p in pngs):
            return pngs
    except Exception:
        pass
    # 2) MATLAB fallback
    try:
        m_script = os.path.join(PROJ, "results", "600010", "plot_finance_split.m")
        dest_script = os.path.join(outdir, "plot_finance_split.m")
        import shutil
        shutil.copy(m_script, dest_script)
        subprocess.run(["matlab", "-batch", f"cd('{outdir}'); plot_finance_split"],
                       capture_output=True, timeout=600)
        names = ["600010_利润_季度折线_含Q2预估.png",
                 "600010_资产负债_含Q2标注.png",
                 "600010_现金流_含Q2标注.png"]
        pngs = [os.path.join(outdir, n) for n in names]
        return [p for p in pngs if os.path.exists(p)]
    except Exception:
        return []


def make_charts_pdf(ticker: str, date: str, pngs: list, outdir: str) -> str:
    """生成图表 PDF(横向,一图一页)"""
    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("CJK", "", r"C:/Windows/Fonts/msyh.ttc", collection_font_number=0)
    pdf.add_font("CJK", "B", r"C:/Windows/Fonts/msyhbd.ttc", collection_font_number=0)

    pdf.add_page()
    pdf.set_font("CJK", "B", 22)
    pdf.ln(40)
    pdf.cell(0, 15, f"{ticker} 基本面图表", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("CJK", "", 12)
    pdf.cell(0, 10, f"季度利润 / 资产负债 / 现金流(节点标注版, 数据截至 {date})",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)
    pdf.set_font("CJK", "", 10)
    pdf.cell(0, 8, "数据源: 东方财富(巨潮披露口径), 单位: 亿元; 2026Q2 归母净利为业绩预告推算(如适用)",
             new_x="LMARGIN", new_y="NEXT", align="C")

    captions = [
        ("图1: 季度利润走势(含 2026Q2 预估)", "归母净利/净利润, 节点标注数值; ★=2026Q2 预估(公告推算)"),
        ("图2: 资产负债走势", "总资产/总负债/资产负债率(右轴), 节点标注数值"),
        ("图3: 现金流走势", "经营/投资/筹资净现金流, 节点标注数值"),
    ]
    for png, (title, cap) in zip(pngs, captions):
        pdf.add_page()
        pdf.set_font("CJK", "B", 15)
        pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(3)
        pdf.set_font("CJK", "", 10)
        pdf.cell(0, 8, cap, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.image(png, x=8, y=pdf.get_y(), w=281)
        pdf.ln(2)

    out = os.path.join(outdir, f"{ticker}_charts.pdf")
    pdf.output(out)
    return out


def merge_pdfs(main_pdf: str, charts_pdf: str, out_pdf: str) -> None:
    """合并主报告 + 图表 PDF(图表附在末尾)"""
    reader = PdfReader(main_pdf)
    writer = PdfWriter()
    for p in reader.pages:
        writer.add_page(p)
    charts = PdfReader(charts_pdf)
    for p in charts.pages:
        writer.add_page(p)
    with open(out_pdf, "wb") as f:
        writer.write(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("main_pdf", help="主报告 PDF 路径")
    ap.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    ap.add_argument("--forecast", default=None, help="业绩预告区间,如 2.3,3.0(可选,Q1 后画 Q2 预估)")
    args = ap.parse_args()

    outdir = os.path.join(PROJ, "results", args.ticker)
    os.makedirs(outdir, exist_ok=True)

    print("[1/4] 拉取三表数据...")
    export_csvs(args.ticker, outdir)

    print("[2/4] 绘制标注三图(Python/matplotlib 优先)...")
    pngs = run_charts(args.ticker, outdir, args.forecast)
    if not pngs:
        print("WARN: 图表生成失败,跳过图表合并")
        return
    print("  pngs:", [os.path.basename(p) for p in pngs])

    print("[3/4] 生成图表 PDF...")
    charts_pdf = make_charts_pdf(args.ticker, args.date, pngs, outdir)

    print("[4/4] 合并进主报告...")
    out_pdf = args.main_pdf.replace(".pdf", "_with_charts.pdf")
    merge_pdfs(args.main_pdf, charts_pdf, out_pdf)
    print("FINAL:", out_pdf)


if __name__ == "__main__":
    main()
