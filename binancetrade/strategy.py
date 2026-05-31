"""Conservative spot strategy with AI-ready market regime scoring.

The module deliberately keeps the execution signal rule-based. AI systems can be
plugged in later to enrich the regime score, but they must not bypass risk
limits or force trades.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from .config import BotConfig
from .indicators import atr, ema, rsi
from .models import Candle, SignalAction, TradeSignal


@dataclass(frozen=True)
class MarketRegime:
    label: str
    confidence: Decimal
    reason: str


class StrategyEngine:
    """Build trade signals from EMA, RSI, ATR, and a regime filter."""

    def __init__(self, config: BotConfig) -> None:
        self.config = config

    def analyze(self, symbol: str, candles: Sequence[Candle]) -> TradeSignal:
        if len(candles) < self.config.candle_limit:
            latest = candles[-1].close if candles else Decimal("0")
            return TradeSignal(symbol, SignalAction.HOLD, Decimal("0"), latest, "not enough candles")

        closes = [candle.close for candle in candles]
        latest_price = closes[-1]
        ema_50 = ema(closes, 50)[-1]
        ema_200 = ema(closes, 200)[-1]
        latest_rsi = rsi(closes, 14)
        latest_atr = atr(candles, 14)
        regime = self._classify_regime(latest_price, ema_50, ema_200, latest_rsi, latest_atr)
        atr_pct = latest_atr / latest_price

        if (
            latest_price > ema_200
            and ema_50 > ema_200
            and Decimal("45") <= latest_rsi <= Decimal("65")
            and atr_pct <= Decimal("0.035")
            and regime.label == "uptrend"
            and regime.confidence >= self.config.min_confidence
        ):
            return TradeSignal(symbol, SignalAction.BUY, regime.confidence, latest_price, regime.reason)

        if latest_price < ema_200 or ema_50 < ema_200 or latest_rsi > Decimal("75"):
            return TradeSignal(
                symbol,
                SignalAction.SELL,
                max(regime.confidence, Decimal("0.70")),
                latest_price,
                "trend weak or overextended; exit/protect capital",
            )

        return TradeSignal(symbol, SignalAction.HOLD, regime.confidence, latest_price, regime.reason)

    def _classify_regime(
        self,
        price: Decimal,
        ema_50: Decimal,
        ema_200: Decimal,
        latest_rsi: Decimal,
        latest_atr: Decimal,
    ) -> MarketRegime:
        atr_pct = latest_atr / price
        if atr_pct > Decimal("0.05"):
            return MarketRegime("high_volatility", Decimal("0.80"), "ATR above 5%; avoid new entries")
        if price > ema_50 > ema_200 and Decimal("45") <= latest_rsi <= Decimal("65"):
            return MarketRegime("uptrend", Decimal("0.72"), "price above EMA50/EMA200 with healthy RSI")
        if price < ema_50 < ema_200:
            return MarketRegime("downtrend", Decimal("0.75"), "price below EMA50/EMA200")
        return MarketRegime("range", Decimal("0.55"), "mixed trend conditions")
