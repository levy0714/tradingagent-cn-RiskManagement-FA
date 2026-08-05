# -*- coding: utf-8 -*-
"""应收账款账龄+坏账计提分析工具(下载年报/中报 PDF,解析账龄结构)。
数据链路: 巨潮公告列表(显式日期) → detail 页拿 PDF 链接 → 下载 → pypdf 提取 → 账龄解析
"""
import re
import io
import warnings
warnings.filterwarnings("ignore")

import requests


_CNINFO_DETAIL = "http://www.cninfo.com.cn/new/disclosure/detail"
_CNINFO_STATIC = "https://static.cninfo.com.cn/{adjunct}"


def _fetch_cninfo_announcements(ticker: str, start: str, end: str):
    """巨潮公告列表(akshare,显式日期防默认2023陷阱)。
    从公告链接提取 announcementId,按 cninfo 直链规则拼 PDF 地址:
    https://static.cninfo.com.cn/finalpage/{YYYY-MM-DD}/{announcementId}.PDF"""
    import akshare as ak

    df = ak.stock_zh_a_disclosure_report_cninfo(
        symbol=ticker, start_date=start, end_date=end
    )
    out = []
    for _, row in df.iterrows():
        title = str(row.get("公告标题", ""))
        t = str(row.get("公告时间", ""))
        link = str(row.get("公告链接", ""))
        m = re.search(r"announcementId=(\d+)", link)
        if not m:
            continue
        ann_id = m.group(1)
        dm = re.match(r"(\d{4}-\d{2}-\d{2})", t)
        date_part = dm.group(1) if dm else ""
        if not date_part:
            continue
        out.append({
            "title": title,
            "date": t[:10],
            "pdf_url": f"https://static.cninfo.com.cn/finalpage/{date_part}/{ann_id}.PDF",
        })
    return out


def _get_pdf_url(detail_url: str) -> str | None:
    """从公告 detail 页 JSON 取 adjunctUrl,拼出 PDF 直链"""
    try:
        r = requests.get(detail_url, timeout=20, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        data = r.json()
        adj = data.get("adjunctUrl") or (data.get("announcement") or {}).get("adjunctUrl")
        if adj:
            return _CNINFO_STATIC.format(adjunct=adj)
    except Exception:
        pass
    return None


def _download_pdf(url: str, timeout: int = 60) -> bytes | None:
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        if r.status_code == 200 and len(r.content) > 5000 and r.content[:4] == b"%PDF":
            return r.content
    except Exception:
        pass
    return None


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(pdf_bytes))
    parts = []
    for p in r.pages:
        parts.append(p.extract_text() or "")
    return "\n".join(parts)


_AGE_PATTERNS = [
    (r"1\s*年以内", "1年以内"),
    (r"1\s*[-～至]?\s*2\s*年", "1至2年"),
    (r"2\s*[-～至]?\s*3\s*年", "2至3年"),
    (r"3\s*[-～至]?\s*4\s*年", "3至4年"),
    (r"4\s*[-～至]?\s*5\s*年", "4至5年"),
    (r"5\s*年以上", "5年以上"),
]


def _parse_aging(text: str) -> str:
    """从年报文本中解析应收账款账龄表 + 坏账准备信息"""
    # 定位账龄披露区域(通常在"按账龄披露"或"应收账款"附注)
    start_idx = len(text)
    for kw in ["按账龄披露", "按账龄", "账龄披露"]:
        i = text.find(kw)
        if i != -1 and i < start_idx:
            start_idx = i
    if start_idx == len(text):
        # 找不到标题,回退到"应收账款"附注区附近
        for kw in ["应收账款", "应收账款披露"]:
            i = text.find(kw)
            if i != -1:
                start_idx = max(0, i)
                break
    region = text[start_idx:start_idx + 8000]

    lines_out = []
    for pat, label in _AGE_PATTERNS:
        m = re.search(pat, region)
        if not m:
            continue
        # 取该账龄行后面 120 字符内的数字(金额,通常以千元/元为单位)
        after = region[m.end():m.end() + 140].replace("\n", " ")
        nums = re.findall(r"[\d,]{6,}", after)
        if nums:
            lines_out.append(f"{label}: {nums[0]}")
            if len(nums) > 1:
                lines_out[-1] += f" | {nums[1]}"
    if not lines_out:
        return "账龄表未能在年报文本中解析(可能需要人工查看附注)"

    # 坏账准备/计提比例
    prov = []
    for kw in ["坏账准备", "计提比例", "单项计提", "组合计提", "预期信用损失"]:
        if kw in region:
            prov.append(kw)
    res = "## 应收账款账龄结构(年报附注解析):\n" + "\n".join(lines_out)
    if prov:
        res += "\n## 坏账计提相关段落包含: " + "、".join(prov)
    return res


def get_aging_analysis(ticker: str, start_date: str = "", end_date: str = "") -> str:
    """下载最新年报/中报 PDF 并解析应收账款账龄结构+坏账计提信息。

    Args:
        ticker: 6 位 A 股代码
        start_date/end_date: 公告日期范围 YYYYMMDD(默认自动取最近一年)
    Returns:
        str: 账龄表 + 坏账计提信息;失败时列明各环节原因
    """
    from datetime import datetime, timedelta
    end = end_date or datetime.now().strftime("%Y%m%d")
    start = start_date or (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")

    # 1) 公告列表
    try:
        anns = _fetch_cninfo_announcements(ticker, start, end)
    except Exception as e:
        return f"(巨潮公告列表获取失败: {type(e).__name__}: {str(e)[:120]})"
    if not anns:
        return f"({ticker} 在 {start}~{end} 无巨潮公告)"

    # 2) 找最新定期报告(优先年报,其次中报)
    ann_report = next((a for a in anns if "年度报告" in a["title"]), None)
    if not ann_report:
        ann_report = next((a for a in anns if ("半年度报告" in a["title"] or "半年报" in a["title"])), None)
    if not ann_report:
        return f"({ticker} 近一年无年报/中报公告,无法解析账龄;三表接口无账龄明细)"
    title = ann_report["title"]
    pdf_url = ann_report["pdf_url"]

    # 4) 下载 PDF
    pdf_bytes = _download_pdf(pdf_url)
    if not pdf_bytes:
        return f"({title} PDF 下载失败)"

    # 5) 提取文本 + 解析账龄
    try:
        text = _extract_pdf_text(pdf_bytes)
    except Exception as e:
        return f"(PDF 文本提取失败: {type(e).__name__}: {str(e)[:120]})"
    aging = _parse_aging(text)

    return (
        f"## 账龄分析数据源: {title}(巨潮原文 PDF,{len(pdf_bytes)//1024}KB)\n"
        f"{aging}\n"
        f"## 说明: 以上为年报附注账龄结构,与三表接口(无此明细)互补;"
        f"坏账充分性判断需结合上年账龄对比(见「账龄滚动分析」)。"
    )


if __name__ == "__main__":
    import sys
    t = sys.argv[1] if len(sys.argv) > 1 else "000932"
    print(get_aging_analysis(t))
