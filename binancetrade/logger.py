"""CSV trade logging for audit and tax records."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from .models import OrderResult, TradeSignal


FIELDNAMES = [
    "timestamp_utc",
    "symbol",
    "side",
    "quantity",
    "price",
    "status",
    "message",
    "signal_action",
    "signal_confidence",
    "signal_reason",
]


class TradeLogger:
    def __init__(self, path: str) -> None:
        self.path = Path(path)

    def record(self, order: OrderResult, signal: TradeSignal) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True) if self.path.parent != Path(".") else None
        exists = self.path.exists()
        with self.path.open("a", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
            if not exists:
                writer.writeheader()
            writer.writerow(
                {
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": str(order.quantity),
                    "price": str(order.price),
                    "status": order.status,
                    "message": order.message,
                    "signal_action": signal.action.value,
                    "signal_confidence": str(signal.confidence),
                    "signal_reason": signal.reason,
                }
            )
