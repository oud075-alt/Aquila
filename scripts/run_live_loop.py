"""Continuous diagnosis loop — runs the orchestrator on a schedule."""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from brain.orchestrator import Orchestrator


async def _loop(args: argparse.Namespace) -> None:
    orchestrator = Orchestrator()
    stop_event = asyncio.Event()

    def _handle_signal(*_: object) -> None:
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal)
        except NotImplementedError:
            pass

    try:
        while not stop_event.is_set():
            try:
                diag = await orchestrator.diagnose_symbol(
                    symbol=args.symbol,
                    timeframe=args.timeframe,
                    exchange=args.exchange,
                    include_gpt=not args.no_gpt,
                )
                print(diag.diagnostic_summary, flush=True)
            except Exception as e:
                print(f"diagnosis error: {e}", file=sys.stderr, flush=True)
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=args.interval)
            except asyncio.TimeoutError:
                pass
    finally:
        await orchestrator.shutdown()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MSPIS continuous diagnostic loop.")
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--timeframe", default="1m")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--interval", type=float, default=60.0, help="Seconds between diagnoses")
    p.add_argument("--no-gpt", action="store_true")
    return p.parse_args()


def main() -> None:
    asyncio.run(_loop(parse_args()))


if __name__ == "__main__":
    main()
