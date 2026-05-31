from decimal import Decimal

from binancetrade.config import BotConfig
from binancetrade.models import AccountSnapshot, Candle, SignalAction, TradeSignal
from binancetrade.risk import RiskEngine
from binancetrade.strategy import StrategyEngine


def make_uptrend_candles(count=250):
    candles = []
    price = Decimal("100")
    for index in range(count):
        if index < 180:
            price += Decimal("0.20")
        else:
            price += Decimal("0.06") if index % 14 < 7 else Decimal("-0.04")
        candles.append(
            Candle(
                open_time=index,
                open=price - Decimal("0.05"),
                high=price + Decimal("0.10"),
                low=price - Decimal("0.10"),
                close=price,
                volume=Decimal("10"),
                close_time=index + 1,
            )
        )
    return candles


def test_strategy_generates_buy_for_healthy_uptrend():
    config = BotConfig()
    signal = StrategyEngine(config).analyze("BTCUSDT", make_uptrend_candles())

    assert signal.action == SignalAction.BUY
    assert signal.confidence >= config.min_confidence


def test_risk_engine_caps_position_size_by_max_position_pct():
    config = BotConfig(starting_cash=Decimal("10000"), max_position_pct=Decimal("0.10"))
    risk = RiskEngine(config)
    account = AccountSnapshot(Decimal("10000"), Decimal("10000"), Decimal("0"), ())
    signal = TradeSignal("BTCUSDT", SignalAction.BUY, Decimal("0.9"), Decimal("100"), "test")

    quantity = risk.size_for_signal(signal, account)

    assert quantity == Decimal("10.000000")


def test_daily_loss_limit_blocks_new_positions():
    config = BotConfig(starting_cash=Decimal("10000"), daily_loss_limit_pct=Decimal("0.02"))
    risk = RiskEngine(config)
    account = AccountSnapshot(Decimal("9000"), Decimal("9000"), Decimal("-250"), ())

    approved, reason = risk.can_open_position(account)

    assert approved is False
    assert reason == "daily loss limit reached"
