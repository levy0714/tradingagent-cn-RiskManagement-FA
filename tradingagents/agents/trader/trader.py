"""Trader: turns the Research Manager's investment plan into a concrete transaction proposal."""

from __future__ import annotations

import functools

from langchain_core.messages import AIMessage

from tradingagents.agents.schemas import TraderProposal, render_trader_proposal
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction
from tradingagents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_trader(llm):
    structured_llm = bind_structured(llm, TraderProposal, "Trader")

    def trader_node(state, name):
        company_name = state["company_of_interest"]
        instrument_context = build_instrument_context(company_name)

        # Collect analyst reports (research manager removed; use analyst outputs directly)
        report_map = {
            "Market Analysis Report": state.get("market_report", ""),
            "Sentiment Analysis Report": state.get("sentiment_report", ""),
            "News Analysis Report": state.get("news_report", ""),
            "Fundamentals Analysis Report": state.get("fundamentals_report", ""),
            "Policy Analysis Report": state.get("policy_report", ""),
            "Hot Money / Capital Flow Report": state.get("hot_money_report", ""),
        }
        analyst_reports = "\n\n".join(
            f"{k}:\n{v}" for k, v in report_map.items() if v
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a trading agent specialising in A-share (China mainland) stocks. "
                    "Based on the analysts' reports, craft a concrete, executable transaction "
                    "proposal. You must factor in A-stock trading constraints:\n"
                    "- T+1 settlement: shares bought today cannot be sold until the next trading day\n"
                    "- Daily price limits: main board ±10%, STAR/ChiNext ±20%, ST stocks ±5%\n"
                    "- Minimum lot: 100 shares (main board) or 200 shares (STAR/ChiNext)\n"
                    "- Trading hours: 09:30-11:30, 13:00-15:00 Beijing time\n"
                    "Anchor your reasoning in the analysts' reports. "
                    "Be specific about entry price, stop loss, and position sizing. "
                    "（以上参数仅供技术研究参考，不构成投资建议）"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Based on a comprehensive analysis by a team of analysts (market, "
                    f"sentiment, news, fundamentals, policy, capital flow), here are the "
                    f"analyst reports for {company_name}.\n\n"
                    f"{instrument_context}\n\n"
                    f"Analyst Reports:\n{analyst_reports}\n\n"
                    + "Leverage these insights to craft a precise transaction proposal."
                    + get_language_instruction()
                ),
            },
        ]

        trader_plan = invoke_structured_or_freetext(
            structured_llm,
            llm,
            messages,
            render_trader_proposal,
            "Trader",
        )

        return {
            "messages": [AIMessage(content=trader_plan)],
            "trader_investment_plan": trader_plan,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
