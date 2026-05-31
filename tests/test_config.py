from decimal import Decimal

import pytest

from binancetrade.config import load_config


def test_load_config_defaults_to_paper_mode():
    config = load_config({})

    assert config.paper_mode is True
    assert config.symbols == ("BTCUSDT", "ETHUSDT")
    assert config.risk_per_trade_pct == Decimal("0.005")


def test_live_mode_requires_credentials():
    with pytest.raises(ValueError, match="Live mode requires"):
        load_config({"BT_PAPER_MODE": "false"})


def test_rejects_overly_large_risk_per_trade():
    with pytest.raises(ValueError, match="risk_per_trade_pct"):
        load_config({"BT_RISK_PER_TRADE_PCT": "0.05"})
