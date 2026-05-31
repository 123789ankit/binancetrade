"""Main orchestration loop for scan and paper trading."""

from __future__ import annotations

from decimal import Decimal

from .binance_client import BinanceSpotClient
from .broker import LiveBroker, PaperBroker
from .config import BotConfig
from .logger import TradeLogger
from .models import OrderResult, SignalAction, TradeSignal
from .risk import RiskEngine
from .strategy import StrategyEngine


class TradingEngine:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.client = BinanceSpotClient(config.api_key, config.api_secret, config.base_url)
        self.strategy = StrategyEngine(config)
        self.risk = RiskEngine(config)
        self.paper = PaperBroker(config, self.risk)
        self.live = LiveBroker(self.client, config)
        self.logger = TradeLogger(config.trade_log_path)

    def scan_once(self) -> list[TradeSignal]:
        signals: list[TradeSignal] = []
        for symbol in self.config.symbols:
            candles = self.client.klines(symbol, self.config.candle_interval, self.config.candle_limit)
            signals.append(self.strategy.analyze(symbol, candles))
        return signals

    def run_paper_once(self) -> list[OrderResult]:
        signals = self.scan_once()
        prices = {signal.symbol: signal.price for signal in signals}
        account = self.paper.snapshot(prices)
        orders: list[OrderResult] = []

        for signal in signals:
            existing = self.paper.positions.get(signal.symbol)
            if existing:
                updated = self.risk.update_trailing_stop(existing, signal.price)
                self.paper.update_position(updated)
                should_exit, reason = self.risk.should_exit(updated, signal.price, signal)
                if should_exit:
                    exit_signal = TradeSignal(signal.symbol, SignalAction.SELL, signal.confidence, signal.price, reason)
                    order = self.paper.sell(signal.symbol, signal.price)
                    self.logger.record(order, exit_signal)
                    orders.append(order)
                continue

            if signal.action != SignalAction.BUY:
                continue
            approved, reason = self.risk.can_open_position(account)
            if not approved:
                orders.append(OrderResult(signal.symbol, "BUY", Decimal("0"), signal.price, "REJECTED", reason))
                continue
            quantity = self.risk.size_for_signal(signal, account)
            order = self.paper.buy(signal.symbol, quantity, signal.price)
            self.logger.record(order, signal)
            orders.append(order)
            account = self.paper.snapshot(prices)
        return orders

    def run_live_once(self) -> list[OrderResult]:
        if self.config.paper_mode:
            raise RuntimeError("Live loop cannot run while paper_mode is enabled")
        orders: list[OrderResult] = []
        for signal in self.scan_once():
            if signal.action != SignalAction.BUY:
                continue
            raise RuntimeError(
                "Live execution is scaffolded but intentionally blocked until account balance and exchange filters are implemented"
            )
        return orders
