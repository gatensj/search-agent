"""
cli.py — Phase 1: run a research task from your terminal.

Usage:
    python cli.py "search all the yoga studios in Philadelphia and list today's classes"
    python cli.py            # interactive prompt
"""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from search_agent import run_search  # noqa: E402  (needs env loaded first)


async def main() -> None:
    task = " ".join(sys.argv[1:]).strip() or input("Task> ").strip()
    if not task:
        print("No task given.")
        return

    print(f"\n>>> Working on: {task}\n{'-' * 60}")

    async def progress(chunk: str) -> None:
        print(f"[agent] {chunk[:200]}{'…' if len(chunk) > 200 else ''}")

    result = await run_search(task, on_progress=progress)

    print("-" * 60)
    print(result.text)
    print("-" * 60)
    print(f"turns={result.num_turns}  cost=${result.cost_usd or 0:.4f}  error={result.is_error}")


if __name__ == "__main__":
    asyncio.run(main())
