from decimal import Decimal

import pytest

from binancetrade.cli import build_parser, run_dashboard
from binancetrade.config import BotConfig
from binancetrade.dashboard import load_dashboard_data, load_trade_rows
from binancetrade.state import PaperState, PaperStateStore


def test_dashboard_loads_state_and_trade_rows(tmp_path):
    state_path = tmp_path / "state.json"
    trade_log = tmp_path / "trades.csv"
    store = PaperStateStore(str(state_path), Decimal("10000"))
    store.save(PaperState(Decimal("9900"), Decimal("5"), "2026-05-31", Decimal("5"), {}))
    trade_log.write_text(
        "timestamp_utc,symbol,side,quantity,price,status\n"
        "2026-05-31T00:00:00+00:00,BTCUSDT,BUY,0.1,100,FILLED\n",
        encoding="utf-8",
    )
    config = BotConfig(state_path=str(state_path), trade_log_path=str(trade_log), kill_switch_path=str(tmp_path / "kill"))

    data = load_dashboard_data(config)

    assert data.state.cash == Decimal("9900")
    assert data.equity == Decimal("9900")
    assert data.kill_switch_active is False
    assert data.trades[0]["symbol"] == "BTCUSDT"


def test_load_trade_rows_returns_empty_for_missing_file(tmp_path):
    assert load_trade_rows(str(tmp_path / "missing.csv")) == []


def test_cli_parser_accepts_dashboard_command():
    args = build_parser().parse_args(["dashboard"])

    assert args.command == "dashboard"


def test_run_dashboard_invokes_streamlit(monkeypatch):
    captured = {}

    def fake_run(command, check):
        captured["command"] = command
        captured["check"] = check

    monkeypatch.setattr("binancetrade.cli.subprocess.run", fake_run)
    monkeypatch.setattr("binancetrade.cli.importlib.util.find_spec", lambda name: object())

    run_dashboard()

    assert captured["check"] is True
    assert captured["command"][1:3] == ["-m", "streamlit"]
    assert captured["command"][3] == "run"


def test_run_dashboard_exits_when_streamlit_missing(monkeypatch):
    monkeypatch.setattr("binancetrade.cli.importlib.util.find_spec", lambda name: None)

    with pytest.raises(SystemExit, match="dashboard"):
        run_dashboard()
