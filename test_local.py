from __future__ import annotations

import argparse
import asyncio
import json

from main import _run


async def amain() -> None:
    parser = argparse.ArgumentParser(description="Local test for clean_search_mcp")
    parser.add_argument("query", help="search query")
    parser.add_argument("-n", "--max-results", type=int, default=5)
    parser.add_argument("--no-content", action="store_true")
    parser.add_argument("--deep", action="store_true", help="use Playwright fallback")
    args = parser.parse_args()

    results = await _run(query=args.query, max_results=args.max_results, with_content=not args.no_content, deep_mode=args.deep)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(amain())
