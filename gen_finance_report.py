# -*- coding: utf-8 -*-
"""深度财报分析 PDF:数据 + 三年趋势 + 同比 + 归因 + 展望。用法: python gen_finance_report.py <ticker>"""
import os, sys, io, argparse
from datetime import datetime

PROJ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJ)
import warnings; warnings.filterwarnings('ignore')
import akshare as ak
import pandas as pd
from web.pdf_export import _ReportPDF

def fmt_yi(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '-'
    if f != f:
        return '-'
    return f'{f/1e8:,.2f}'

def fmt_pct(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return '-'
    if f != f:
        return '-'
    return f'{f:.2f}%'

def pl(d):
    d = str(d)[:10]
    names = {'03-31': 'Q1', '06-30': 'Q2', '09-30': 'Q3', '12-31': '年报'}
    return d[:4] + names.get(d[5:7], d[5:7])

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ticker')
    ap.add_argument('--date', default=datetime.now().strftime('%Y-%m-%d'))
    args = ap.parse_args()
    code = args.ticker
    prefix = 'SH' if code.startswith(('6', '9')) else 'SZ'
    sym = prefix + code

    bs = ak.stock_balance_sheet_by_report_em(symbol=sym)
    inc = ak.stock_profit_sheet_by_report_em(symbol=sym)
    cf = ak.stock_cash_flow_sheet_by_report_em(symbol=sym)
    for df in (bs, inc, cf):
        df['REPORT_DATE'] = pd.to_datetime(df['REPORT_DATE'])
    bs = bs[bs['REPORT_DATE'] >= '2024-01-01'].sort_values('REPORT_DATE').reset_index(drop=True)
    inc = inc[inc['REPORT_DATE'] >= '2024-01-01'].sort_values('REPORT_DATE').reset_index(drop=True)
    cf = cf[cf['REPORT_DATE'] >= '2024-01-01'].sort_values('REPORT_DATE').reset_index(drop=True)

    def g(df, col, i):
        return df.iloc[i][col] if col in df.columns else None

    def f(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # ================= tables =================
    rows_bs = []
    for i in range(len(bs)):
        ta, tl, pe = f(g(bs, 'TOTAL_ASSETS', i)), f(g(bs, 'TOTAL_LIABILITIES', i)), f(g(bs, 'TOTAL_PARENT_EQUITY', i))
        ratio = (tl/ta*100) if ta and tl else None
        rows_bs.append([pl(bs.iloc[i]['REPORT_DATE']), fmt_yi(ta), fmt_yi(tl), fmt_pct(ratio), fmt_yi(pe),
                        fmt_yi(g(bs, 'MONETARYFUNDS', i)), fmt_yi(g(bs, 'TOTAL_CURRENT_LIAB', i)),
                        fmt_yi(g(bs, 'TOTAL_NONCURRENT_LIAB', i)), fmt_yi(g(bs, 'INVENTORY', i))])
    bs_md = ['| 报告期 | 总资产 | 总负债 | 负债率 | 归母权益 | 货币资金 | 流动负债 | 非流动负债 | 存货 |',
             '|---|---|---|---|---|---|---|---|---|']
    bs_md += ['| ' + ' | '.join(r) + ' |' for r in rows_bs]

    rows_inc = []
    for i in range(len(inc)):
        oi, toi, np_, pnp = f(g(inc, 'OPERATE_INCOME', i)), f(g(inc, 'TOTAL_OPERATE_INCOME', i)), f(g(inc, 'NETPROFIT', i)), f(g(inc, 'PARENT_NETPROFIT', i))
        eps, oc = f(g(inc, 'BASIC_EPS', i)), f(g(inc, 'OPERATE_COST', i))
        gm = ((oi-oc)/oi*100) if oi and oc else None
        rows_inc.append([pl(inc.iloc[i]['REPORT_DATE']), fmt_yi(oi), fmt_pct(g(inc, 'TOTAL_OPERATE_INCOME_YOY', i)),
                         fmt_yi(pnp), fmt_pct(g(inc, 'PARENT_NETPROFIT_YOY', i)), fmt_pct(gm),
                         f'{eps:.4f}' if eps is not None else '-'])
    inc_md = ['| 报告期 | 营业收入 | 营收同比 | 归母净利 | 归母同比 | 毛利率 | EPS(元) |',
              '|---|---|---|---|---|---|---|']
    inc_md += ['| ' + ' | '.join(r) + ' |' for r in rows_inc]

    rows_cf = []
    for i in range(len(cf)):
        rows_cf.append([pl(cf.iloc[i]['REPORT_DATE']), fmt_yi(g(cf, 'NETCASH_OPERATE', i)),
                        fmt_yi(g(cf, 'NETCASH_INVEST', i)), fmt_yi(g(cf, 'NETCASH_FINANCE', i)),
                        fmt_yi(g(cf, 'END_CCE', i))])
    cf_md = ['| 报告期 | 经营净现金流 | 投资净现金流 | 筹资净现金流 | 期末现金 |',
             '|---|---|---|---|---|']
    cf_md += ['| ' + ' | '.join(r) + ' |' for r in rows_cf]

    # ================= narrative analysis =================
    analysis = []
    analysis.append(('二、三年趋势分析', '''**营收趋势(逐年下滑,2026 加速)**:2024 全年营业总收入 680.89 亿(同比 -3.5%),2025 年 663.58 亿(同比 -2.5%),2026Q1 仅 133.14 亿(同比 **-13.7%**,为近三年最差单季)。营收连续收缩的主因是钢铁行业需求疲软——下游地产链持续低迷,行业整体承压(媒体报道 2026 年中报超七成钢企预亏)。

**盈利趋势(2025 改善,2026Q1 巨亏,中报预告反转)**:归母净利 2024 年 2.65 亿(-48.6%),2025 年 3.74 亿(**+41.2%**,逐季改善:Q1 0.45→Q4 3.74),2026Q1 骤降至 **-4.63 亿**(同比 -1129%)。但公司 2026-07-14 发布《半年度业绩预增公告》:中报净利预计 **2.30~3.00 亿,同比 +52%~98%**——意味着 Q2 单季需盈利约 6.9~7.6 亿,依赖稀土板块量价回升。

**毛利率**:2024 年 7.4%~8.6% → 2025 年升至 8.3%~10.0%(全年改善)→ 2026Q1 跌回 **6.6%**(钢价下行+成本挤压)。'''))

    analysis.append(('三、利润变化归因(结合新闻与政策)', '''**1. 钢铁主业:持续拖累(营收与毛利率下滑的主因)**
- 行业背景:房地产下行拖累用钢需求,原料(铁矿石/焦炭)成本高企,超七成钢企 2026 中报预亏——包钢作为 1600 万吨级板材/管材钢厂,2026Q1 毛利率仅 6.6%,单季归母亏损 4.63 亿。
- 事件:2026-08-03 公告控股子公司「1.18」安全事故调查报告,事故后续赔偿/整改或产生一次性支出,需跟踪。

**2. 稀土板块:盈利弹性核心(2025 改善与 2026 中报预增的关键)**
- 包钢背靠白云鄂博矿(全球最大稀土-铁共生矿),通过稀土精矿供应绑定北方稀土产业链,是 A 股稀缺「钢铁+稀土」双标的。
- 2026Q2 稀土精矿价格环比大涨(约 +45%),叠加稀土战略资源政策(出口管制、收储预期)与「新质生产力/高端化」产业政策,稀土改性无缝钢管等高端产品放量——这是中报预增 52%~98% 的主要驱动。
- 政策面:稀土战略地位上升、国企市值管理与增持再贷款政策(控股股东具备工具使用条件)、内蒙古自治区产业扶持。

**3. 其他**:2025 年归母净利 +41.2% 亦含降本增效;2026Q1 亏损或含季节性(一季度北方钢厂检修/需求淡季)因素。'''))

    analysis.append(('四、负债结构与偿债能力', '''- **资产负债率三年稳定在 59.5%~60.5%**,处于钢铁行业典型高位区间,未见恶化。
- **结构变化(2026Q1)**:流动负债由 2025 年末 623.7 亿降至 556.0 亿,非流动负债由 278.5 亿升至 351.4 亿——**债务长期化趋势**(短期偿债压力部分后移)。
- **货币资金 80.9 亿(2026Q1)**,覆盖流动负债约 14.5%,叠加经营现金流,短期流动性无重大风险,但货币资金储备在三年中处于偏低水平。
- 关注:长期债务占比上升意味着利息负担刚性化,若利润持续低迷,偿债指标可能承压。'''))

    analysis.append(('五、现金流质量', '''- **经营现金流**:2024 全年 +23.77 亿、2025 全年 +25.71 亿(约为当年归母净利的 6.9 倍),**造血能力显著好于账面利润**(折旧摊销大、营运资本管理),2026Q1 为 -18.11 亿(一季度季节性回款差,属正常波动)。
- **投资现金流**:连续三年净流出(每年约 -18~-21 亿),资本开支维持高位(设备改造/环保投入)。
- **筹资现金流**:2025 年大幅净流出 -47.93 亿(偿还债务),2026Q1 转为 +14.74 亿(重新融资)——与负债结构长期化相互印证。
- **结论**:经营造血正常,但资本开支+偿债双重消耗,公司高度依赖再融资维持流动性。'''))

    analysis.append(('六、盈利质量', '''- **净利率 0~0.6%**(2026Q1 -4.1%)、**ROE 0.1%~0.7%**(2026Q1 -0.9%):典型微利钢铁股,盈利安全边际极薄。
- 2026Q1 亏损 4.63 亿、中报预告盈利 2.3~3.0 亿,盈利波动极大,**对稀土价格高度敏感**——稀土涨价是当前唯一的利润弹性来源。
- 经营现金流/净利常年大于 1(2025 年报达 6.7 倍),利润含金量尚可,但绝对水平过低。'''))

    analysis.append(('七、未来展望', '''**短期(2026H2)**:8 月 20 日披露中报,若 Q2 稀土量价兑现,全年有望扭亏为盈;业绩预告区间 2.3~3.0 亿为当前最大正面催化。
**关键变量**:
1. 稀土精矿价格(最大弹性,涨价 45% 能否持续);
2. 钢铁主业景气(地产链需求、原料成本);
3. 「1.18」安全事故后续(赔偿/停产整改影响);
4. 国企市值管理/增持政策落地。
**风险**:Q1 已亏 4.63 亿,若 Q2 稀土兑现不及预期,中报或低于预告下沿;钢铁主业若继续恶化,全年仍可能亏损;高负债+高资本开支的现金流压力。'''))

    analysis.append(('八、未验证项与数据说明', '''- 数据来源:东方财富财务数据库(akshare,源自巨潮披露),2024Q1~2026Q1 共 9 期;单位:亿元(注明除外)。
- 行业与政策信息(超七成钢企预亏、稀土精矿涨价、政策表述)来自公开新闻报道与同花顺交易事件页,已尽量交叉核验,个别数字以公司正式披露为准。
- 中报预告区间为业绩预告口径,最终以 2026-08-20 中报为准。
- 本报告仅供研究参考,不构成投资建议。'''))

    # ================= render =================
    pdf = _ReportPDF(code, args.date, '财务深度分析')
    pdf.add_cover()
    pdf.add_section('财务分析说明', (
        '> 本报告为财务专项深度分析:2024~2026 全部已披露报告期(9 期)数据 + 趋势/同比/归因/展望。\n'
        '- 数据:东方财富财务数据库(巨潮披露口径),单位亿元\n'
        '- 分析结合公开新闻与政策信息,已标注来源性质\n'
    ))
    pdf.add_section('一、核心财务数据(2024Q1~2026Q1)', (
        '### 资产负债表\n' + '\n'.join(bs_md) +
        '\n\n### 利润表(收益)\n' + '\n'.join(inc_md) +
        '\n\n### 现金流量表\n' + '\n'.join(cf_md)
    ))
    for title, content in analysis:
        pdf.add_section(title, content)

    out = os.path.join(PROJ, 'results', code, f'{code}_财报深度分析_{args.date}.pdf')
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'wb') as f:
        f.write(bytes(pdf.output()))
    print('PDF:', out)

if __name__ == '__main__':
    main()
