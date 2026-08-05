# -*- coding: utf-8 -*-
"""Python(matplotlib)版标注三图:利润/资产负债/现金流。
用法: python plot_finance_py.py <ticker> [--outdir DIR] [--forecast low,high]
--forecast: 业绩预告区间(亿元,如 2.3,3.0),最新期为 Q1 时画 Q2 预估点
输出: <ticker>_利润_季度折线_含Q2预估.png / 资产负债 / 现金流(节点标注)
"""
import os
import sys
import argparse
from datetime import datetime

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load(outdir: str):
    inc = pd.read_csv(os.path.join(outdir, "fin_income.csv"), parse_dates=["REPORT_DATE"])
    bs = pd.read_csv(os.path.join(outdir, "fin_balance.csv"), parse_dates=["REPORT_DATE"])
    cf = pd.read_csv(os.path.join(outdir, "fin_cashflow.csv"), parse_dates=["REPORT_DATE"])
    for df in (inc, bs, cf):
        df.sort_values("REPORT_DATE", inplace=True)
        df.reset_index(drop=True, inplace=True)
    return inc, bs, cf


def mask_2016(df):
    return df[df["REPORT_DATE"] >= "2016-01-01"]


def plot_profit(ticker, outdir, inc, forecast):
    d = mask_2016(inc)
    fig, ax = plt.subplots(figsize=(14, 5.6))
    y1 = d["PARENT_NETPROFIT"] / 1e8
    y2 = d["NETPROFIT"] / 1e8
    ax.plot(d["REPORT_DATE"], y1, "b-o", lw=1.3, ms=4, label="归母净利(亿)")
    ax.plot(d["REPORT_DATE"], y2, "r--s", lw=1, ms=4, label="净利润(亿)")
    ax.axhline(0, color="k", lw=0.8)
    ax.grid(True, alpha=0.3)
    for x, v in zip(d["REPORT_DATE"], y1):
        ax.annotate(f"{v:.1f}", (x, v), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=6.2, color=(0, 0, 0.7))
    for x, v in zip(d["REPORT_DATE"], y2):
        ax.annotate(f"{v:.1f}", (x, v), textcoords="offset points", xytext=(0, -13),
                    ha="center", fontsize=6.2, color=(0.7, 0, 0))
    # Q2 预估(可选)
    if forecast and len(d) and d["REPORT_DATE"].iloc[-1].month == 3:
        lo, hi = forecast
        q1 = float(y1.iloc[-1])
        mid = (lo + hi) / 2 - q1
        xq2 = d["REPORT_DATE"].iloc[-1] + pd.DateOffset(months=3)
        ax.plot([d["REPORT_DATE"].iloc[-1], xq2], [y1.iloc[-1], mid], "b:", lw=1.3)
        ax.plot(xq2, mid, "b*", ms=14)
        ax.annotate(f"2026Q2 预估 {lo+q1:.1f}~{hi+q1:.1f}亿", (xq2, mid),
                    textcoords="offset points", xytext=(0, 12), ha="center",
                    fontsize=9, color=(0, 0, 0.8), fontweight="bold")
    ax.legend(loc="upper left", fontsize=9)
    ax.set_ylabel("亿元")
    ax.set_title(f"{ticker} 季度利润走势(节点标注)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"{ticker}_利润_季度折线_含Q2预估.png"), dpi=130)
    plt.close(fig)


def plot_balance(ticker, outdir, bs):
    d = mask_2016(bs)
    fig, ax = plt.subplots(figsize=(14, 5.6))
    a1 = d["TOTAL_ASSETS"] / 1e8
    a2 = d["TOTAL_LIABILITIES"] / 1e8
    a3 = d["TOTAL_LIABILITIES"] / d["TOTAL_ASSETS"] * 100
    ax.plot(d["REPORT_DATE"], a1, "b-o", lw=1.3, ms=4, label="总资产(亿)")
    ax.plot(d["REPORT_DATE"], a2, "r--s", lw=1.2, ms=4, label="总负债(亿)")
    ax.set_ylabel("亿元")
    ax.grid(True, alpha=0.3)
    ax2 = ax.twinx()
    ax2.plot(d["REPORT_DATE"], a3, "g-^", lw=1.2, ms=4, label="资产负债率(%)")
    ax2.set_ylabel("资产负债率(%)")
    ax2.set_ylim(40, 80)
    for x, v in zip(d["REPORT_DATE"], a1):
        ax.annotate(f"{v:.0f}", (x, v), textcoords="offset points", xytext=(0, 7),
                    ha="center", fontsize=6.2, color=(0, 0, 0.7))
    for x, v in zip(d["REPORT_DATE"], a2):
        ax.annotate(f"{v:.0f}", (x, v), textcoords="offset points", xytext=(0, -14),
                    ha="center", fontsize=6.2, color=(0.7, 0, 0))
    for x, v in zip(d["REPORT_DATE"], a3):
        ax2.annotate(f"{v:.0f}%", (x, v), textcoords="offset points", xytext=(0, 6),
                     ha="center", fontsize=6.2, color=(0, 0.5, 0))
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)
    ax.set_title(f"{ticker} 资产负债走势(节点标注)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"{ticker}_资产负债_含Q2标注.png"), dpi=130)
    plt.close(fig)


def plot_cashflow(ticker, outdir, cf):
    d = mask_2016(cf)
    fig, ax = plt.subplots(figsize=(14, 5.6))
    series = [
        ("NETCASH_OPERATE", "经营净现金流", "b-o"),
        ("NETCASH_INVEST", "投资净现金流", "r--s"),
        ("NETCASH_FINANCE", "筹资净现金流", "g-^"),
    ]
    colors = [(0, 0, 0.7), (0.7, 0, 0), (0, 0.5, 0)]
    for (col, label, style), c in zip(series, colors):
        v = d[col] / 1e8
        ax.plot(d["REPORT_DATE"], v, style, lw=1.2, ms=4, label=f"{label}(亿)")
        for x, val in zip(d["REPORT_DATE"], v):
            off = 9 if col == "NETCASH_OPERATE" else (-14 if col == "NETCASH_INVEST" else 14)
            ax.annotate(f"{val:.0f}", (x, val), textcoords="offset points",
                        xytext=(0, off), ha="center", fontsize=6.2, color=c)
    ax.axhline(0, color="k", lw=0.8)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=9)
    ax.set_ylabel("亿元")
    ax.set_title(f"{ticker} 现金流走势(节点标注)")
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.tight_layout()
    fig.savefig(os.path.join(outdir, f"{ticker}_现金流_含Q2标注.png"), dpi=130)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ticker")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--forecast", default=None, help="业绩预告区间,如 2.3,3.0")
    args = ap.parse_args()
    outdir = args.outdir or os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "results", args.ticker)
    forecast = None
    if args.forecast:
        lo, hi = (float(x) for x in args.forecast.split(","))
        forecast = (lo, hi)
    inc, bs, cf = load(outdir)
    plot_profit(args.ticker, outdir, inc, forecast)
    plot_balance(args.ticker, outdir, bs)
    plot_cashflow(args.ticker, outdir, cf)
    print("DONE: 3 charts (python/matplotlib)")


if __name__ == "__main__":
    main()
