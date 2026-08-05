from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

@tool
def get_news(
    ticker: Annotated[str, "6-digit A-stock code (e.g. 600379). Must be numeric, NOT company name or Chinese text"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve news data for a given stock code.
    Uses the configured news_data vendor.
    Args:
        ticker (str): 6-digit A-stock code, e.g. 600379, 300750. Must be the numeric code, not the company name.
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    return route_to_vendor("get_news", ticker, start_date, end_date)

@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back (default 7)
        limit (int): Maximum number of articles to return (default 5)
    Returns:
        str: A formatted string containing global news data
    """
    return route_to_vendor("get_global_news", curr_date, look_back_days, limit)

@tool
def get_insider_transactions(
    ticker: Annotated[str, "6-digit A-stock code (e.g. 600379). Must be numeric, NOT company name"],
) -> str:
    """
    Retrieve insider transaction information about a company.
    Uses the configured news_data vendor.
    Args:
        ticker (str): 6-digit A-stock code, e.g. 600379
    Returns:
        str: A report of insider transaction data
    """
    return route_to_vendor("get_insider_transactions", ticker)


@tool
def get_official_sources(
    ticker: Annotated[str, "6-digit A-stock code (e.g. 600519)"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """官方一手信息来源:巨潮资讯公司公告 + 证监会官网要闻(带官方 URL)。政策/公告结论必须以此为准。"""
    import re as _re
    import requests as _requests

    parts = []

    # 1) 巨潮资讯公司公告(akshare,必须显式传日期,否则默认2023年)
    try:
        import akshare as ak
        sd = start_date.replace("-", "")
        ed = end_date.replace("-", "")
        df = ak.stock_zh_a_disclosure_report_cninfo(symbol=ticker, start_date=sd, end_date=ed)
        if df is not None and len(df) > 0:
            parts.append(f"## 巨潮资讯公司公告({ticker}) {start_date}~{end_date}(前30条):\n{df.head(30).to_string()}")
        else:
            parts.append("## 巨潮资讯公司公告:该区间无公告")
    except Exception as e:
        parts.append(f"## 巨潮资讯公司公告:获取失败({type(e).__name__}: {str(e)[:120]})")

    # 2) 证监会官网要闻(最新列表,带官方URL)
    try:
        url = "https://www.csrc.gov.cn/csrc/c100028/common_list.shtml"
        resp = _requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
        resp.encoding = "utf-8"
        html = resp.text
        items = _re.findall(r"href=[\'\"]([^\'\"]*content\.shtml)[\'\"][^>]*>([^<]{8,60})</a>", html)
        lines = []
        for href, title in items[:20]:
            if not href.startswith("http"):
                href = "https://www.csrc.gov.cn" + (href if href.startswith("/") else "/" + href)
            lines.append(f"- {title.strip()} | {href}")
        if lines:
            parts.append("## 证监会要闻(官网,近20条):\n" + "\n".join(lines))
        else:
            parts.append("## 证监会要闻:列表页解析为空,请直接访问 https://www.csrc.gov.cn")
    except Exception as e:
        parts.append(f"## 证监会要闻:获取失败({type(e).__name__}: {str(e)[:120]})")

    return "\n\n".join(parts)
