"""Main orchestration loop for scan and paper trading."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from .binance_client import BinanceSpotClient
from .broker import LiveBroker, PaperBroker
from .config import BotConfig
from .logger import TradeLogger
from .models import OrderResult, SignalAction, SymbolFilters, TradeSignal
from .risk import RiskEngine
from .strategy import StrategyEngine


class TradingEngine:
    def __init__(self, config: BotConfig) -> None:
        self.config = config
        self.client = BinanceSpotClient(
            config.api_key,
            config.api_secret,
            config.base_url,
            timeout_seconds=config.request_timeout_seconds,
            retries=config.request_retries,
        )
        self.strategy = StrategyEngine(config)
        self.risk = RiskEngine(config)
        self.paper = PaperBroker(config, self.risk)
        self.live = LiveBroker(self.client, config)
        self.logger = TradeLogger(config.trade_log_path)
        self._filters: dict[str, SymbolFilters] = {}

    def scan_once(self) -> list[TradeSignal]:
        if self.kill_switch_active():
            return [TradeSignal(symbol, SignalAction.HOLD, Decimal("0"), Decimal("0"), "kill switch active") for symbol in self.config.symbols]
        signals: list[TradeSignal] = []
        for symbol in self.config.symbols:
            candles = self.client.klines(symbol, self.config.candle_interval, self.config.candle_limit)
            signals.append(self.strategy.analyze(symbol, candles))
        return signals

    def run_paper_once(self) -> list[OrderResult]:
        if self.kill_switch_active():
            return [OrderResult(symbol, "BUY", Decimal("0"), Decimal("0"), "REJECTED", "kill switch active") for symbol in self.config.symbols]
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
            quantity = self.risk.size_for_signal(signal, account, self._symbol_filters(signal.symbol))
            order = self.paper.buy(signal.symbol, quantity, signal.price)
            self.logger.record(order, signal)
            orders.append(order)
            account = self.paper.snapshot(prices)
        return orders

    def run_live_once(self) -> list[OrderResult]:
        if self.config.paper_mode:
            raise RuntimeError("Live loop cannot run while paper_mode is enabled")
        if not self.config.enable_live_trading:
            raise RuntimeError("Live loop requires BT_ENABLE_LIVE_TRADING=true")
        if self.kill_switch_active():
            return [OrderResult(symbol, "BUY", Decimal("0"), Decimal("0"), "REJECTED", "kill switch active") for symbol in self.config.symbols]
        raise RuntimeError(
            "Live execution remains blocked until account reconciliation, open-order management, and manual operator review are implemented"
        )

    def kill_switch_active(self) -> bool:
        return Path(self.config.kill_switch_path).exists()

    def _symbol_filters(self, symbol: str) -> SymbolFilters | None:
        if symbol in self._filters:
            return self._filters[symbol]
        try:
            self._filters[symbol] = self.client.symbol_filters(symbol)
        except Exception:
            return None
        return self._filters[symbol]
