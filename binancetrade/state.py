"""Local JSON persistence for paper-trading state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

from .models import Position


@dataclass(frozen=True)
class PaperState:
    cash: Decimal
    realized_pnl: Decimal
    daily_pnl_date: str
    daily_realized_pnl: Decimal
    positions: dict[str, Position]


class PaperStateStore:
    """Persist paper account state between CLI runs."""

    def __init__(self, path: str, starting_cash: Decimal) -> None:
        self.path = Path(path)
        self.starting_cash = starting_cash

    def load(self) -> PaperState:
        if not self.path.exists():
            return PaperState(self.starting_cash, Decimal("0"), date.today().isoformat(), Decimal("0"), {})
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        positions = {
            symbol: Position(
                symbol=symbol,
                quantity=Decimal(raw["quantity"]),
                entry_price=Decimal(raw["entry_price"]),
                stop_loss=Decimal(raw["stop_loss"]),
                take_profit=Decimal(raw["take_profit"]),
                trailing_stop=Decimal(raw["trailing_stop"]),
                highest_price=Decimal(raw["highest_price"]),
            )
            for symbol, raw in payload.get("positions", {}).items()
        }
        return PaperState(
            cash=Decimal(payload.get("cash", str(self.starting_cash))),
            realized_pnl=Decimal(payload.get("realized_pnl", "0")),
            daily_pnl_date=payload.get("daily_pnl_date", date.today().isoformat()),
            daily_realized_pnl=Decimal(payload.get("daily_realized_pnl", "0")),
            positions=positions,
        )

    def save(self, state: PaperState) -> None:
        if self.path.parent != Path("."):
            self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "cash": str(state.cash),
            "realized_pnl": str(state.realized_pnl),
            "daily_pnl_date": state.daily_pnl_date,
            "daily_realized_pnl": str(state.daily_realized_pnl),
            "positions": {
                symbol: {
                    "quantity": str(position.quantity),
                    "entry_price": str(position.entry_price),
                    "stop_loss": str(position.stop_loss),
                    "take_profit": str(position.take_profit),
                    "trailing_stop": str(position.trailing_stop),
                    "highest_price": str(position.highest_price),
                }
                for symbol, position in state.positions.items()
            },
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
