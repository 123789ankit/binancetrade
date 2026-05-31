"""Command-line interface for BinanceTrade."""

from __future__ import annotations

import argparse
import json

from .config import load_config
from .engine import TradingEngine


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper-first Binance spot trading bot")
    parser.add_argument("command", choices=["scan", "paper-once", "config"], help="Action to run")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = load_config()
    if args.command == "config":
        safe_config = {key: str(value) for key, value in config.__dict__.items() if "secret" not in key and "api_key" not in key}
        print(json.dumps(safe_config, indent=2))
        return

    engine = TradingEngine(config)
    if args.command == "scan":
        for signal in engine.scan_once():
            print(json.dumps({"symbol": signal.symbol, "action": signal.action.value, "confidence": str(signal.confidence), "price": str(signal.price), "reason": signal.reason}))
        return
    if args.command == "paper-once":
        for order in engine.run_paper_once():
            print(json.dumps({"symbol": order.symbol, "side": order.side, "quantity": str(order.quantity), "price": str(order.price), "status": order.status, "message": order.message}))


if __name__ == "__main__":
    main()
