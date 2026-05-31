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
    "gross_quote_value",
    "fee",
    "net_quote_value",
    "realized_pnl",
    "status",
    "message",
    "order_id",
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
                    "gross_quote_value": str(order.gross_quote_value),
                    "fee": str(order.fee),
                    "net_quote_value": str(order.net_quote_value),
                    "realized_pnl": str(order.realized_pnl),
                    "status": order.status,
                    "message": order.message,
                    "order_id": order.order_id or "",
                    "signal_action": signal.action.value,
                    "signal_confidence": str(signal.confidence),
                    "signal_reason": signal.reason,
                }
            )
