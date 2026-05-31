"""Local Streamlit dashboard for paper trading operations.

The dashboard is deliberately local/operator-focused. It reads persisted paper
state and trade logs, shows bot safety status, and exposes only paper-safe
controls such as reset instructions and kill-switch status.
"""

from __future__ import annotations

import csv
import importlib
import importlib.util
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from .config import BotConfig, load_config
from .state import PaperState, PaperStateStore


@dataclass(frozen=True)
class DashboardData:
    """Prepared data for the Streamlit UI and tests."""

    config: BotConfig
    state: PaperState
    kill_switch_active: bool
    equity: Decimal
    positions: list[dict[str, str]]
    trades: list[dict[str, str]]


def load_dashboard_data(config: BotConfig | None = None) -> DashboardData:
    """Load paper account state, positions, and trade history for display."""

    config = config or load_config()
    state = PaperStateStore(config.state_path, config.starting_cash).load()
    prices = {symbol: position.entry_price for symbol, position in state.positions.items()}
    equity = state.cash + sum(position.quantity * prices[symbol] for symbol, position in state.positions.items())
    positions = [
        {
            "symbol": position.symbol,
            "quantity": str(position.quantity),
            "entry_price": str(position.entry_price),
            "stop_loss": str(position.stop_loss),
            "take_profit": str(position.take_profit),
            "trailing_stop": str(position.trailing_stop),
            "highest_price": str(position.highest_price),
        }
        for position in state.positions.values()
    ]
    return DashboardData(
        config=config,
        state=state,
        kill_switch_active=Path(config.kill_switch_path).exists(),
        equity=equity,
        positions=positions,
        trades=load_trade_rows(config.trade_log_path),
    )


def load_trade_rows(path: str, *, limit: int = 100) -> list[dict[str, str]]:
    """Load the newest trade-log rows for the dashboard."""

    trade_log = Path(path)
    if not trade_log.exists():
        return []
    with trade_log.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-limit:]


def run() -> None:
    """Render the Streamlit dashboard."""

    if importlib.util.find_spec("streamlit") is None:
        raise SystemExit("Streamlit is not installed. Run: pip install -e '.[dashboard]'")
    st = importlib.import_module("streamlit")
    data = load_dashboard_data()
    _render(st, data)


def _render(st: Any, data: DashboardData) -> None:
    st.set_page_config(page_title="BinanceTrade Dashboard", page_icon="📈", layout="wide")
    st.title("📈 BinanceTrade Paper Dashboard")
    st.warning(
        "This dashboard is for paper trading and operator review only. "
        "The bot is not ready for unsupervised live trading."
    )

    mode = "Paper" if data.config.paper_mode else "Live gated"
    kill_status = "ACTIVE - orders blocked" if data.kill_switch_active else "Inactive"
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mode", mode)
    col2.metric("Kill switch", kill_status)
    col3.metric("Paper cash", f"{data.state.cash} {data.config.quote_asset}")
    col4.metric("Paper equity", f"{data.equity} {data.config.quote_asset}")

    col5, col6, col7 = st.columns(3)
    col5.metric("Realized PnL", str(data.state.realized_pnl))
    col6.metric("Daily realized PnL", str(data.state.daily_realized_pnl))
    col7.metric("Open positions", str(len(data.positions)))

    st.subheader("Configured symbols")
    st.write(", ".join(data.config.symbols))

    st.subheader("Open paper positions")
    if data.positions:
        st.dataframe(data.positions, use_container_width=True)
    else:
        st.info("No open paper positions.")

    st.subheader("Recent trade log")
    if data.trades:
        st.dataframe(data.trades, use_container_width=True)
    else:
        st.info("No trade log rows yet. Run `binancetrade paper-once` after setup.")

    st.subheader("Safety controls")
    st.code(f"touch {data.config.kill_switch_path}", language="bash")
    st.caption("Create this file to block scans/orders. Remove it to resume paper operation.")
    st.code("binancetrade reset-paper", language="bash")
    st.caption("Reset local paper state. This does not touch Binance or any real funds.")


if __name__ == "__main__":
    run()
