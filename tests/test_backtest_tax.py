from decimal import Decimal

from binancetrade.backtest import Backtester
from binancetrade.config import BotConfig
from binancetrade.models import Candle
from binancetrade.tax import export_india_tax_csv


def make_candles(count=280):
    candles = []
    price = Decimal("100")
    for index in range(count):
        if index < 220:
            price += Decimal("0.12")
        else:
            price += Decimal("0.04") if index % 8 < 4 else Decimal("-0.02")
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


def test_backtester_returns_metrics(tmp_path):
    config = BotConfig(state_path=str(tmp_path / "unused.json"), slippage_pct=Decimal("0"), taker_fee_pct=Decimal("0"))
    result = Backtester(config).run("BTCUSDT", make_candles())

    assert result.starting_cash == Decimal("10000")
    assert result.ending_equity > Decimal("0")
    assert result.max_drawdown_pct >= Decimal("0")


def test_india_tax_export(tmp_path):
    trade_log = tmp_path / "trades.csv"
    trade_log.write_text(
        "timestamp_utc,symbol,side,quantity,price,gross_quote_value,fee,net_quote_value,realized_pnl,status,message,order_id,signal_action,signal_confidence,signal_reason\n"
        "2026-05-31T00:00:00+00:00,BTCUSDT,SELL,0.1,100,10,0.01,9.99,1.23,FILLED,test,1,SELL,0.8,test\n",
        encoding="utf-8",
    )
    output = tmp_path / "tax.csv"

    export_india_tax_csv(str(trade_log), str(output), Decimal("83"))

    content = output.read_text(encoding="utf-8")
    assert "FY2026-27" in content
    assert "102.09" in content
