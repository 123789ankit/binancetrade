"""Paper broker and live broker wrapper."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .binance_client import BinanceSpotClient
from .config import BotConfig
from .models import AccountSnapshot, OrderResult, Position, Side
from .risk import RiskEngine
from .state import PaperState, PaperStateStore


class PaperBroker:
    """Persistent local broker for safe simulations with live market prices."""

    def __init__(self, config: BotConfig, risk: RiskEngine, state_store: PaperStateStore | None = None) -> None:
        self.config = config
        self.risk = risk
        self.state_store = state_store or PaperStateStore(config.state_path, config.starting_cash)
        state = self.state_store.load()
        today = date.today().isoformat()
        self.cash = state.cash
        self.realized_pnl = state.realized_pnl
        self.daily_pnl_date = state.daily_pnl_date
        self.daily_realized_pnl = state.daily_realized_pnl if state.daily_pnl_date == today else Decimal("0")
        self.daily_pnl_date = today
        self.positions: dict[str, Position] = dict(state.positions)
        self._save()

    def snapshot(self, prices: dict[str, Decimal] | None = None) -> AccountSnapshot:
        prices = prices or {}
        equity = self.cash
        for symbol, position in self.positions.items():
            equity += position.quantity * prices.get(symbol, position.entry_price)
        return AccountSnapshot(self.cash, equity, self.realized_pnl, tuple(self.positions.values()), self.daily_realized_pnl)

    def buy(self, symbol: str, quantity: Decimal, price: Decimal) -> OrderResult:
        fill_price = price * (Decimal("1") + self.config.slippage_pct)
        gross = quantity * fill_price
        fee = gross * self.config.taker_fee_pct
        total_cost = gross + fee
        if quantity <= 0:
            return OrderResult(symbol, "BUY", quantity, fill_price, "REJECTED", "quantity is zero")
        if total_cost > self.cash:
            return OrderResult(symbol, "BUY", quantity, fill_price, "REJECTED", "insufficient paper cash")
        self.cash -= total_cost
        self.positions[symbol] = self.risk.build_position(symbol, quantity, fill_price)
        self._save()
        return OrderResult(symbol, "BUY", quantity, fill_price, "FILLED", "paper order filled", fee, gross, total_cost)

    def sell(self, symbol: str, price: Decimal) -> OrderResult:
        position = self.positions.pop(symbol, None)
        fill_price = price * (Decimal("1") - self.config.slippage_pct)
        if position is None:
            return OrderResult(symbol, "SELL", Decimal("0"), fill_price, "REJECTED", "no open paper position")
        gross = position.quantity * fill_price
        fee = gross * self.config.taker_fee_pct
        net = gross - fee
        realized = net - (position.quantity * position.entry_price)
        self.cash += net
        self.realized_pnl += realized
        self.daily_realized_pnl += realized
        self._save()
        return OrderResult(symbol, "SELL", position.quantity, fill_price, "FILLED", "paper order filled", fee, gross, net, realized)

    def update_position(self, position: Position) -> None:
        self.positions[position.symbol] = position
        self._save()

    def _save(self) -> None:
        self.state_store.save(
            PaperState(
                cash=self.cash,
                realized_pnl=self.realized_pnl,
                daily_pnl_date=self.daily_pnl_date,
                daily_realized_pnl=self.daily_realized_pnl,
                positions=self.positions,
            )
        )


class LiveBroker:
    """Live spot wrapper that defaults to dry-run orders for safety."""

    def __init__(self, client: BinanceSpotClient, config: BotConfig) -> None:
        self.client = client
        self.config = config

    def market_order(self, symbol: str, side: Side, quantity: Decimal) -> OrderResult:
        if not self.config.enable_live_trading:
            return OrderResult(symbol, side, quantity, Decimal("0"), "REJECTED", "live trading flag is disabled")
        return self.client.market_order(symbol, side, quantity, dry_run=self.config.dry_run_live_orders)
