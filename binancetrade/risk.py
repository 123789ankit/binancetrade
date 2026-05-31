"""Risk controls that cannot be bypassed by strategy or AI signals."""

from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

from .config import BotConfig
from .models import AccountSnapshot, Position, SignalAction, SymbolFilters, TradeSignal


class RiskEngine:
    """Approve or reject trades and calculate conservative position sizes."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def can_open_position(self, account: AccountSnapshot) -> tuple[bool, str]:
        daily_loss_limit = self.config.starting_cash * self.config.daily_loss_limit_pct
        if account.daily_realized_pnl <= -daily_loss_limit:
            return False, "daily loss limit reached"
        if len(account.open_positions) >= self.config.max_open_positions:
            return False, "maximum open positions reached"
        return True, "risk checks passed"

    def size_for_signal(
        self,
        signal: TradeSignal,
        account: AccountSnapshot,
        symbol_filters: SymbolFilters | None = None,
    ) -> Decimal:
        if signal.action != SignalAction.BUY or signal.price <= 0:
            return Decimal("0")
        risk_budget = account.equity * self.config.risk_per_trade_pct
        stop_distance = signal.price * self.config.stop_loss_pct
        risk_based_quantity = risk_budget / stop_distance
        max_notional = account.equity * self.config.max_position_pct
        cash_based_quantity = min(account.cash, max_notional) / signal.price
        quantity = min(risk_based_quantity, cash_based_quantity)
        if symbol_filters is None:
            return quantity.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        quantity = round_step_size(quantity, symbol_filters.step_size)
        notional = quantity * signal.price
        if quantity < symbol_filters.min_quantity or notional < symbol_filters.min_notional:
            return Decimal("0")
        return min(quantity, symbol_filters.max_quantity)

    def build_position(self, symbol: str, quantity: Decimal, entry_price: Decimal) -> Position:
        return Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=entry_price,
            stop_loss=entry_price * (Decimal("1") - self.config.stop_loss_pct),
            take_profit=entry_price * (Decimal("1") + self.config.take_profit_pct),
            trailing_stop=entry_price * (Decimal("1") - self.config.trailing_stop_pct),
            highest_price=entry_price,
        )

    def update_trailing_stop(self, position: Position, latest_price: Decimal) -> Position:
        if latest_price <= position.highest_price:
            return position
        trailing_stop = latest_price * (Decimal("1") - self.config.trailing_stop_pct)
        return Position(
            symbol=position.symbol,
            quantity=position.quantity,
            entry_price=position.entry_price,
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            trailing_stop=max(position.trailing_stop, trailing_stop),
            highest_price=latest_price,
        )

    @staticmethod
    def should_exit(position: Position, latest_price: Decimal, signal: TradeSignal) -> tuple[bool, str]:
        if latest_price <= position.stop_loss:
            return True, "stop loss hit"
        if latest_price <= position.trailing_stop:
            return True, "trailing stop hit"
        if latest_price >= position.take_profit:
            return True, "take profit hit"
        if signal.action == SignalAction.SELL:
            return True, signal.reason
        return False, "hold position"


def round_step_size(quantity: Decimal, step_size: Decimal) -> Decimal:
    """Round ``quantity`` down to Binance's step size."""

    if step_size <= 0:
        return quantity
    return (quantity // step_size) * step_size
