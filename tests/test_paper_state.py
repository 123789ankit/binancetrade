from decimal import Decimal

from binancetrade.broker import PaperBroker
from binancetrade.config import BotConfig
from binancetrade.risk import RiskEngine


def test_paper_state_persists_between_brokers(tmp_path):
    state_path = tmp_path / "state.json"
    config = BotConfig(state_path=str(state_path), slippage_pct=Decimal("0"), taker_fee_pct=Decimal("0"))
    risk = RiskEngine(config)

    first = PaperBroker(config, risk)
    order = first.buy("BTCUSDT", Decimal("0.1"), Decimal("100"))

    second = PaperBroker(config, risk)

    assert order.status == "FILLED"
    assert second.cash == Decimal("9990.0")
    assert "BTCUSDT" in second.positions


def test_paper_broker_applies_fee_and_slippage(tmp_path):
    config = BotConfig(state_path=str(tmp_path / "state.json"), slippage_pct=Decimal("0.01"), taker_fee_pct=Decimal("0.001"))
    broker = PaperBroker(config, RiskEngine(config))

    order = broker.buy("BTCUSDT", Decimal("1"), Decimal("100"))

    assert order.price == Decimal("101.00")
    assert order.fee == Decimal("0.10100")
    assert broker.cash == Decimal("9898.89900")
