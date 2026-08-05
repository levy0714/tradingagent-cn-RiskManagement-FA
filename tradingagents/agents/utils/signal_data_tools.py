from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor


@tool
def get_profit_forecast(
    ticker: Annotated[str, "A-stock code (e.g. 688017)"],
) -> str:
    """
    Retrieve consensus EPS forecasts with forward valuation metrics.
    Returns analyst coverage count, EPS range, forward PE, PEG, and PE digestion time.
    Uses the configured signal_data vendor.
    Args:
        ticker (str): A-stock code
    Returns:
        str: Consensus forecast report with valuation metrics
    """
    return route_to_vendor("get_profit_forecast", ticker)


@tool
def get_hot_stocks(
    curr_date: Annotated[str, "Date in YYYY-MM-DD format, empty for today"] = "",
) -> str:
    """
    Retrieve today's strong stocks with topic attribution reason tags.
    Shows WHY stocks surged (e.g. '算力租赁+AI政务'), curated by 同花顺 editorial team.
    Includes theme frequency analysis.
    Uses the configured signal_data vendor.
    Args:
        curr_date (str): Date in YYYY-MM-DD format, empty string for today
    Returns:
        str: Hot stocks list with reason tags and theme frequency
    """
    return route_to_vendor("get_hot_stocks", curr_date)


@tool
def get_northbound_flow(
    curr_date: Annotated[str, "Date in YYYY-MM-DD format"],
    include_history: Annotated[
        bool, "Include historical daily data (last 20 trading days)"
    ] = False,
) -> str:
    """
    Retrieve northbound capital flow (沪深股通) data.
    Realtime: minute-level cumulative net buying for HGT + SGT.
    History (optional): daily-level data for trend analysis.
    Uses the configured signal_data vendor.
    Args:
        curr_date (str): Date in YYYY-MM-DD format
        include_history (bool): Whether to include historical daily data
    Returns:
        str: Northbound capital flow report with bullish/bearish signal
    """
    return route_to_vendor("get_northbound_flow", curr_date, include_history)


@tool
def get_concept_blocks(
    ticker: Annotated[str, "A-stock code (e.g. 688017)"],
) -> str:
    """
    Retrieve concept/sector/region blocks that a stock belongs to.
    Shows industry (申万), concept themes (e.g. 机器人概念, 减速器), and region.
    Each block includes current day's change percentage.
    Uses the configured signal_data vendor.
    Args:
        ticker (str): A-stock code
    Returns:
        str: Concept and sector block membership with daily changes
    """
    return route_to_vendor("get_concept_blocks", ticker)


@tool
def get_fund_flow(
    ticker: Annotated[str, "A-stock code"],
    curr_date: Annotated[str, "Date in YYYY-MM-DD format"],
    include_history: Annotated[
        bool, "Include historical daily fund flow (last 20 days)"
    ] = True,
) -> str:
    """
    Retrieve individual stock fund flow (main force vs retail investor).
    Realtime: minute-level super/large/medium/small order flow.
    History: daily net inflow by order size for 20 trading days.
    Uses the configured signal_data vendor.
    Args:
        ticker (str): A-stock code
        curr_date (str): Date in YYYY-MM-DD format
        include_history (bool): Include 20-day historical daily flow
    Returns:
        str: Fund flow report with main force signal
    """
    return route_to_vendor("get_fund_flow", ticker, curr_date, include_history)


@tool
def get_dragon_tiger_board(
    ticker: Annotated[str, "A-stock code (e.g. 000858)"],
    curr_date: Annotated[str, "Date in YYYY-MM-DD format"],
    look_back_days: Annotated[int, "Days to look back (default 30)"] = 30,
) -> str:
    """
    Retrieve dragon-tiger board (龙虎榜) data for a stock.
    Shows recent LHB appearances, top buyer/seller seats (营业部),
    and institutional involvement. Key signal for hot money tracking.
    Args:
        ticker (str): A-stock code
        curr_date (str): Date in YYYY-MM-DD format
        look_back_days (int): How many days back to search
    Returns:
        str: LHB appearances with seat details and institutional activity
    """
    return route_to_vendor("get_dragon_tiger_board", ticker, curr_date, look_back_days)


@tool
def get_efinance_fund_flow(
    ticker: Annotated[str, "A-stock code (e.g. 600010)"],
    days: Annotated[int, "历史天数(默认60)"] = 60,
) -> str:
    """efinance 资金流补充源:主力/小单/中单净流入日线历史。
    与 get_fund_flow 互为备份,一个失败用另一个。"""
    try:
        import efinance as ef
        df = ef.stock.get_history_bill(ticker)
        if df is None or len(df) == 0:
            return "(efinance 资金流:无数据)"
        df = df.tail(days)
        lines = []
        for _, r in df.iterrows():
            t = str(r.get('日期', ''))[:10]
            try:
                main_flow = float(r.get('主力净流入', 0)) / 1e8
                small_flow = float(r.get('小单净流入', 0)) / 1e8
                mid_flow = float(r.get('中单净流入', 0)) / 1e8
                lines.append(f"{t}: 主力净流入 {main_flow:+.2f}亿 | 中单 {mid_flow:+.2f}亿 | 小单 {small_flow:+.2f}亿")
            except (TypeError, ValueError):
                continue
        if not lines:
            return "(efinance 资金流:解析为空)"
        return "## efinance 主力资金流(补充源):\n" + "\n".join(lines)
    except Exception as e:
        return f"(efinance 资金流失败: {type(e).__name__}: {str(e)[:80]})"


@tool
def get_efinance_billboard(
    ticker: Annotated[str, "A-stock code (e.g. 600010)"],
    date: Annotated[str, "查询日期 YYYY-MM-DD,默认最近交易日"] = "",
) -> str:
    """efinance 龙虎榜补充源:查询指定日期全市场龙虎榜,返回该股上榜详情(净买额/买入额/卖出额)。
    未上榜返回提示。与 get_dragon_tiger_board 互为备份。"""
    try:
        import efinance as ef
        from datetime import datetime as _dt
        d = date or _dt.now().strftime("%Y-%m-%d")
        df = ef.stock.get_daily_billboard(d)
        if df is None or len(df) == 0:
            return f"({d} 龙虎榜:当日无上榜数据)"
        row = df[df['股票代码'].astype(str).str.contains(ticker)]
        if len(row) == 0:
            return f"({ticker} 在 {d} 龙虎榜未上榜;当日全市场上榜 {len(df)} 只)"
        r = row.iloc[0]
        return (
            f"## {ticker} 龙虎榜({d}):\n"
            f"- 上榜解读: {r.get('解读', '-')}\n"
            f"- 收盘价: {r.get('收盘价', '-')} | 涨跌幅: {r.get('涨跌幅', '-')}% | 换手率: {r.get('换手率', '-')}%\n"
            f"- 龙虎榜净买额: {r.get('龙虎榜净买额', '-')} | 买入额: {r.get('龙虎榜买入额', '-')} | 卖出额: {r.get('龙虎榜卖出额', '-')}"
        )
    except Exception as e:
        return f"(efinance 龙虎榜失败: {type(e).__name__}: {str(e)[:80]})"


@tool
def get_lockup_expiry(
    ticker: Annotated[str, "A-stock code (e.g. 000858)"],
    curr_date: Annotated[str, "Date in YYYY-MM-DD format"],
    forward_days: Annotated[int, "Days forward to check (default 90)"] = 90,
) -> str:
    """
    Retrieve lockup expiry (限售解禁) schedule for a stock.
    Shows historical unlock records and upcoming expiry calendar
    with impact metrics (unlock quantity, market cap ratio).
    Args:
        ticker (str): A-stock code
        curr_date (str): Date in YYYY-MM-DD format
        forward_days (int): How many days forward to check
    Returns:
        str: Lockup expiry schedule with impact assessment
    """
    return route_to_vendor("get_lockup_expiry", ticker, curr_date, forward_days)


@tool
def get_industry_comparison(
    ticker: Annotated[str, "A-stock code (e.g. 000858)"],
    curr_date: Annotated[str, "Date in YYYY-MM-DD format"],
) -> str:
    """
    Retrieve industry sector performance comparison (行业横向对比).
    Shows all 90 THS industries ranked by performance with turnover,
    net capital flow, and leading stocks. Useful for sector rotation analysis.
    Args:
        ticker (str): A-stock code (used to identify relevant sector)
        curr_date (str): Date in YYYY-MM-DD format
    Returns:
        str: Industry performance ranking with key metrics
    """
    return route_to_vendor("get_industry_comparison", ticker, curr_date)
