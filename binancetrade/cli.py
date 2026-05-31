"""Command-line interface for BinanceTrade."""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from .config import load_config
from .engine import TradingEngine
from .state import PaperStateStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Paper-first Binance spot trading bot")
    parser.add_argument(
        "command",
        choices=["scan", "paper-once", "config", "reset-paper", "dashboard"],
        help="Action to run",
    )
    return parser


def run_dashboard() -> None:
    """Launch the local Streamlit dashboard."""

    if importlib.util.find_spec("streamlit") is None:
        raise SystemExit("Streamlit is not installed. Run: pip install -e '.[dashboard]'")
    dashboard_path = Path(__file__).with_name("dashboard.py")
    command = [sys.executable, "-m", "streamlit", "run", str(dashboard_path)]
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode) from exc


def main() -> None:
    args = build_parser().parse_args()
    config = load_config()
    if args.command == "config":
        safe_config = {key: str(value) for key, value in config.__dict__.items() if "secret" not in key and "api_key" not in key}
        print(json.dumps(safe_config, indent=2))
        return
    if args.command == "reset-paper":
        PaperStateStore(config.state_path, config.starting_cash).reset()
        print(json.dumps({"status": "reset", "state_path": config.state_path}))
        return
    if args.command == "dashboard":
        run_dashboard()
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
