"""Historical backtesting utilities."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from statistics import mean
from typing import Sequence

from .broker import PaperBroker
from .config import BotConfig
from .models import Candle, OrderResult, SignalAction, TradeSignal
from .risk import RiskEngine
from .state import PaperStateStore
from .strategy import StrategyEngine


@dataclass(frozen=True)
class BacktestResult:
    starting_cash: Decimal
    ending_equity: Decimal
    total_return_pct: Decimal
    max_drawdown_pct: Decimal
    trades: tuple[OrderResult, ...]
    win_rate: Decimal
    profit_factor: Decimal


class MemoryStateStore(PaperStateStore):
    def __init__(self, starting_cash: Decimal) -> None:
        super().__init__(":memory:", starting_cash)
        self._state = None

    def load(self):
        if self._state is None:
            return super().load()
        return self._state

    def save(self, state):
        self._state = state


class Backtester:
    """Walk-forward backtester using the production strategy and risk engine."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.strategy = StrategyEngine(config)
        self.risk = RiskEngine(config)
        self.paper = PaperBroker(config, self.risk, MemoryStateStore(config.starting_cash))

    def run(self, symbol: str, candles: Sequence[Candle]) -> BacktestResult:
        trades: list[OrderResult] = []
        equity_curve: list[Decimal] = [self.config.starting_cash]
        for index in range(self.config.candle_limit, len(candles) + 1):
            window = candles[index - self.config.candle_limit : index]
            signal = self.strategy.analyze(symbol, window)
            latest_price = signal.price
            existing = self.paper.positions.get(symbol)
            if existing:
                updated = self.risk.update_trailing_stop(existing, latest_price)
                self.paper.update_position(updated)
                should_exit, reason = self.risk.should_exit(updated, latest_price, signal)
                if should_exit:
                    trades.append(self.paper.sell(symbol, latest_price))
                    signal = TradeSignal(symbol, SignalAction.SELL, signal.confidence, latest_price, reason)
            elif signal.action == SignalAction.BUY:
                account = self.paper.snapshot({symbol: latest_price})
                approved, _ = self.risk.can_open_position(account)
                if approved:
                    quantity = self.risk.size_for_signal(signal, account)
                    trades.append(self.paper.buy(symbol, quantity, latest_price))
            equity_curve.append(self.paper.snapshot({symbol: latest_price}).equity)

        ending_equity = equity_curve[-1]
        realized = [trade.realized_pnl for trade in trades if trade.side == "SELL"]
        wins = [value for value in realized if value > 0]
        losses = [abs(value) for value in realized if value < 0]
        win_rate = Decimal(len(wins)) / Decimal(len(realized)) if realized else Decimal("0")
        profit_factor = (sum(wins) / sum(losses)) if losses else (Decimal("0") if not wins else Decimal("999"))
        return BacktestResult(
            starting_cash=self.config.starting_cash,
            ending_equity=ending_equity,
            total_return_pct=(ending_equity - self.config.starting_cash) / self.config.starting_cash,
            max_drawdown_pct=_max_drawdown(equity_curve),
            trades=tuple(trades),
            win_rate=win_rate,
            profit_factor=profit_factor,
        )


def _max_drawdown(values: Sequence[Decimal]) -> Decimal:
    peak = values[0]
    worst = Decimal("0")
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak)
    return abs(worst)
