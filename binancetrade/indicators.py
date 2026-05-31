"""Technical indicators used by the strategy engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from .models import Candle


def ema(values: Sequence[Decimal], period: int) -> list[Decimal]:
    """Return the exponential moving average series for ``values``."""

    if period <= 0:
        raise ValueError("period must be positive")
    if len(values) < period:
        raise ValueError("not enough values for EMA")
    multiplier = Decimal(2) / Decimal(period + 1)
    seed = sum(values[:period]) / Decimal(period)
    result = [seed]
    previous = seed
    for value in values[period:]:
        current = (value - previous) * multiplier + previous
        result.append(current)
        previous = current
    return result


def rsi(values: Sequence[Decimal], period: int = 14) -> Decimal:
    """Return the latest relative strength index."""

    if len(values) <= period:
        raise ValueError("not enough values for RSI")
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for previous, current in zip(values[-period - 1 : -1], values[-period:]):
        change = current - previous
        gains.append(max(change, Decimal("0")))
        losses.append(abs(min(change, Decimal("0"))))
    average_gain = sum(gains) / Decimal(period)
    average_loss = sum(losses) / Decimal(period)
    if average_loss == 0:
        return Decimal("100")
    relative_strength = average_gain / average_loss
    return Decimal("100") - (Decimal("100") / (Decimal("1") + relative_strength))


def atr(candles: Sequence[Candle], period: int = 14) -> Decimal:
    """Return the latest average true range."""

    if len(candles) <= period:
        raise ValueError("not enough candles for ATR")
    ranges: list[Decimal] = []
    relevant = candles[-period - 1 :]
    for previous, current in zip(relevant[:-1], relevant[1:]):
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return sum(ranges) / Decimal(period)
