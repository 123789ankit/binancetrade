from decimal import Decimal

import pytest

from binancetrade.config import BotConfig, load_config
from binancetrade.engine import TradingEngine
from binancetrade.models import AccountSnapshot, SignalAction, SymbolFilters, TradeSignal
from binancetrade.risk import RiskEngine


def test_live_mode_requires_explicit_enable_flag():
    with pytest.raises(ValueError, match="BT_ENABLE_LIVE_TRADING"):
        load_config(
            {
                "BT_PAPER_MODE": "false",
                "BT_BINANCE_API_KEY": "key",
                "BT_BINANCE_API_SECRET": "secret",
            }
        )


def test_live_engine_still_blocks_execution_without_reconciliation():
    config = BotConfig(paper_mode=False, enable_live_trading=True, api_key="key", api_secret="secret")
    engine = TradingEngine(config)

    with pytest.raises(RuntimeError, match="Live execution remains blocked"):
        engine.run_live_once()


def test_kill_switch_blocks_paper_orders(tmp_path):
    kill = tmp_path / "kill"
    kill.write_text("stop", encoding="utf-8")
    config = BotConfig(kill_switch_path=str(kill), state_path=str(tmp_path / "state.json"))
    engine = TradingEngine(config)

    orders = engine.run_paper_once()

    assert orders
    assert all(order.status == "REJECTED" for order in orders)
    assert all(order.message == "kill switch active" for order in orders)


def test_symbol_filters_round_and_reject_small_notional():
    config = BotConfig()
    risk = RiskEngine(config)
    filters = SymbolFilters("TESTUSDT", Decimal("0.01"), Decimal("1000"), Decimal("0.01"), Decimal("10"), Decimal("0.01"))
    account = AccountSnapshot(Decimal("100"), Decimal("100"), Decimal("0"), ())
    signal = TradeSignal("TESTUSDT", SignalAction.BUY, Decimal("0.9"), Decimal("100"), "test")

    assert risk.size_for_signal(signal, account, filters) == Decimal("0.10")

    small_account = AccountSnapshot(Decimal("5"), Decimal("5"), Decimal("0"), ())
    assert risk.size_for_signal(signal, small_account, filters) == Decimal("0")
