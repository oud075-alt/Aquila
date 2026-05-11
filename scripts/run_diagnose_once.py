"""One-shot diagnosis runner — produces a single diagnosis and prints it."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to sys.path when executed directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain.execution.report_generator import ReportGenerator
from brain.orchestrator import Orchestrator


async def _run(args: argparse.Namespace) -> int:
    orchestrator = Orchestrator()
    try:
        diag = await orchestrator.diagnose_symbol(
            symbol=args.symbol,
            timeframe=args.timeframe,
            exchange=args.exchange,
            include_gpt=not args.no_gpt,
        )
    finally:
        await orchestrator.shutdown()

    if args.format == "json":
        print(json.dumps(diag.to_dict(), indent=2, default=str))
    elif args.format == "markdown":
        print(ReportGenerator().build_markdown(diag))
    else:
        print(diag.diagnostic_summary)
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run a single MSPIS diagnosis.")
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--timeframe", default="5m")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--format", choices=["summary", "markdown", "json"], default="summary")
    p.add_argument("--no-gpt", action="store_true", help="Skip GPT interpretation")
    return p.parse_args()


def main() -> None:
    code = asyncio.run(_run(parse_args()))
    sys.exit(code)


if __name__ == "__main__":
    main()
