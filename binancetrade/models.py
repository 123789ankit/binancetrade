"""Shared domain models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Literal


Side = Literal["BUY", "SELL"]


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Candle:
    open_time: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    close_time: int


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    take_profit: Decimal
    trailing_stop: Decimal
    highest_price: Decimal


@dataclass(frozen=True)
class AccountSnapshot:
    cash: Decimal
    equity: Decimal
    realized_pnl: Decimal
    open_positions: tuple[Position, ...]


@dataclass(frozen=True)
class TradeSignal:
    symbol: str
    action: SignalAction
    confidence: Decimal
    price: Decimal
    reason: str


@dataclass(frozen=True)
class OrderResult:
    symbol: str
    side: Side
    quantity: Decimal
    price: Decimal
    status: str
    message: str
