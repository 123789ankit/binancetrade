"""Paper broker and live broker wrapper."""

from __future__ import annotations

from decimal import Decimal

from .binance_client import BinanceSpotClient
from .config import BotConfig
from .models import AccountSnapshot, OrderResult, Position, Side
from .risk import RiskEngine


class PaperBroker:
    """In-memory broker for safe simulations with live market prices."""

    def __init__(self, config: BotConfig, risk: RiskEngine) -> None:
        self.config = config
        self.risk = risk
        self.cash = config.starting_cash
        self.realized_pnl = Decimal("0")
        self.positions: dict[str, Position] = {}

    def snapshot(self, prices: dict[str, Decimal] | None = None) -> AccountSnapshot:
        prices = prices or {}
        equity = self.cash
        for symbol, position in self.positions.items():
            equity += position.quantity * prices.get(symbol, position.entry_price)
        return AccountSnapshot(self.cash, equity, self.realized_pnl, tuple(self.positions.values()))

    def buy(self, symbol: str, quantity: Decimal, price: Decimal) -> OrderResult:
        notional = quantity * price
        if quantity <= 0:
            return OrderResult(symbol, "BUY", quantity, price, "REJECTED", "quantity is zero")
        if notional > self.cash:
            return OrderResult(symbol, "BUY", quantity, price, "REJECTED", "insufficient paper cash")
        self.cash -= notional
        self.positions[symbol] = self.risk.build_position(symbol, quantity, price)
        return OrderResult(symbol, "BUY", quantity, price, "FILLED", "paper order filled")

    def sell(self, symbol: str, price: Decimal) -> OrderResult:
        position = self.positions.pop(symbol, None)
        if position is None:
            return OrderResult(symbol, "SELL", Decimal("0"), price, "REJECTED", "no open paper position")
        proceeds = position.quantity * price
        self.cash += proceeds
        self.realized_pnl += (price - position.entry_price) * position.quantity
        return OrderResult(symbol, "SELL", position.quantity, price, "FILLED", "paper order filled")

    def update_position(self, position: Position) -> None:
        self.positions[position.symbol] = position


class LiveBroker:
    """Live spot wrapper that defaults to dry-run orders for safety."""

    def __init__(self, client: BinanceSpotClient, config: BotConfig) -> None:
        self.client = client
        self.config = config

    def market_order(self, symbol: str, side: Side, quantity: Decimal) -> OrderResult:
        return self.client.market_order(symbol, side, quantity, dry_run=self.config.dry_run_live_orders)
