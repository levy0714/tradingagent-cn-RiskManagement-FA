"""Shared 5-tier rating vocabulary and a deterministic heuristic parser.

The same five-tier scale (Buy, Overweight, Hold, Underweight, Sell) is used by:
- The Research Manager (investment plan recommendation)
- The Portfolio Manager (final position decision)
- The signal processor (rating extracted for downstream consumers)
- The memory log (rating tag stored alongside each decision entry)

Centralising it here avoids drift between those call sites.
"""

from __future__ import annotations

import re
from typing import Tuple


# Canonical, ordered 5-tier scale (most bullish to most bearish).
RATINGS_5_TIER: Tuple[str, ...] = (
    "Buy", "Overweight", "Hold", "Underweight", "Sell",
)

_RATING_SET = {r.lower() for r in RATINGS_5_TIER}

# 中文评级词 -> 英文五档(按文本出现顺序匹配时使用)
_CN_RATING_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ("卖出", "Sell"), ("回避", "Sell"), ("清仓", "Sell"), ("止损", "Sell"), ("离场", "Sell"),
    ("减持", "Underweight"), ("减仓", "Underweight"), ("规避", "Underweight"), ("低配", "Underweight"),
    ("持有", "Hold"), ("中性", "Hold"), ("观望", "Hold"),
    ("增持", "Overweight"), ("超配", "Overweight"), ("加仓", "Overweight"), ("偏多", "Overweight"),
    ("买入", "Buy"), ("强烈买入", "Buy"), ("建仓", "Buy"), ("重仓", "Buy"),
)


def _clean_token(token: str) -> str:
    """Strip markdown bold/backticks/punctuation around a rating token."""
    return re.sub(r"[*\s_#]", "", token)


# Matches "Rating: X" / "rating - X" / "Rating: **X**" — tolerates markdown
# bold wrappers and either a colon or hyphen separator.
_RATING_LABEL_RE = re.compile(r"rating.*?[:\-][\s*]*(\w+)", re.IGNORECASE)


def parse_rating(text: str, default: str = "Hold") -> str:
    """Extract a 5-tier rating from prose text (English label or Chinese wording).

    Passes:
    1. Explicit label lines: `Rating: X` / `rating - X` / `评级: X` / `评级：X`
       (tolerates markdown bold and backticks, e.g. `Underweight`).
    2. First 5-tier English rating word anywhere in the text (backtick-tolerant).
    3. First Chinese rating keyword anywhere in the text (e.g. 卖出/减持/持有/增持/买入).
    Returns a Title-cased rating string, or `default` if nothing matches.
    """
    label_re = re.compile(
        r"(?:rating|评级)\s*[:：\-]\s*[*\s]*([A-Za-z]+|[^*\n，。；]{2,8})",
        re.IGNORECASE,
    )
    # Pass 1: explicit label
    for line in text.splitlines():
        m = label_re.search(line)
        if m:
            tok = _clean_token(m.group(1))
            low = tok.lower()
            if low in _RATING_SET:
                return tok.title()
            cn = _cn_rating_match(line)
            if cn:
                return cn
    # Pass 2: first English rating word in the whole text
    for token in re.findall(r"[A-Za-z]+", text):
        if token.lower() in _RATING_SET:
            return token.title()
    # Pass 3: first Chinese rating keyword in the whole text
    cn = _cn_rating_match(text)
    if cn:
        return cn
    return default


def _cn_rating_match(text: str):
    """Return the 5-tier rating for the earliest Chinese keyword found in text."""
    best = None
    for kw, rating in _CN_RATING_KEYWORDS:
        i = text.find(kw)
        if i != -1 and (best is None or i < best[0]):
            best = (i, rating)
    return best[1] if best else None

