"""
search_agent.py — core research agent built on the Claude Agent SDK.

The agent is deliberately sandboxed: it may ONLY search and fetch the web.
No shell, no file writes, hard caps on turns and dollar spend per task.
"""

import os
from dataclasses import dataclass

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    query,
)

SYSTEM_PROMPT = """You are a personal research agent. Your job: run web searches,
read pages, and return a concise, accurate answer.

Rules:
- Be skeptical. Prefer primary sources (official sites, .gov portals) over blogspam.
- Always report WHEN information was found/dated. Prices, schedules, and grant
  deadlines go stale fast — flag anything that might be outdated.
- If a site blocks you or data is unavailable, say so plainly. Never invent
  prices, class times, deadlines, or solicitation numbers.
- End with a short "Sources" list of the URLs you actually relied on.
- If the request is too ambiguous to search well, ask ONE clarifying question
  instead of guessing (start that reply with "QUESTION:").
- Keep the final answer under ~350 words unless the task demands more.
"""

# Per-task safety caps (override via environment)
MAX_TURNS = int(os.environ.get("AGENT_MAX_TURNS", "25"))
MAX_BUDGET_USD = float(os.environ.get("AGENT_MAX_BUDGET_USD", "0.50"))
MODEL = os.environ.get("AGENT_MODEL", "sonnet")


@dataclass
class SearchResult:
    text: str
    cost_usd: float | None
    num_turns: int | None
    is_error: bool


def _options() -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model=MODEL,
        allowed_tools=["WebSearch", "WebFetch"],
        disallowed_tools=["Bash", "Write", "Edit", "NotebookEdit"],
        permission_mode="bypassPermissions",  # headless; safety comes from the tool allowlist above
        max_turns=MAX_TURNS,
        max_budget_usd=MAX_BUDGET_USD,
    )


async def run_search(task: str, on_progress=None) -> SearchResult:
    """
    Run one research task to completion.

    on_progress: optional async callback(str) fired as the agent produces
    intermediate text — used by the Telegram bot to show signs of life.
    """
    final_text_parts: list[str] = []
    cost = None
    turns = None
    is_error = False

    async for message in query(prompt=task, options=_options()):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock) and block.text.strip():
                    final_text_parts.append(block.text)
                    if on_progress:
                        await on_progress(block.text)
        elif isinstance(message, ResultMessage):
            cost = message.total_cost_usd
            turns = message.num_turns
            is_error = message.is_error
            # ResultMessage.result is the canonical final answer when present
            if message.result:
                final_text_parts = [message.result]

    text = "\n\n".join(final_text_parts).strip() or "(agent returned no text)"
    return SearchResult(text=text, cost_usd=cost, num_turns=turns, is_error=is_error)
