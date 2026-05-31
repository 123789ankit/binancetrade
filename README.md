# BinanceTrade

BinanceTrade is a **paper-first Binance Spot automation starter** for learning,
backtesting, and carefully simulating crypto trades before any real-money use.
It is intentionally conservative: there is no futures support, no leverage, no
margin support, and no withdrawal code.

> Financial risk notice: no trading bot, AI model, or strategy can guarantee
> profit. Crypto trading can lose money quickly. Start with paper mode, keep
> position sizes small, and consult qualified tax/financial professionals for
> India-specific obligations.

## Current live-trading status

This project is **not ready to place unsupervised live trades**. The code now has
more live-safety gates, exchange-filter parsing, persistent paper state,
fee/slippage modeling, a kill switch, and backtesting utilities, but
`TradingEngine.run_live_once` still blocks real execution until live account
reconciliation, open-order management, and manual operator review are completed.

## What this tool does

- Fetches Binance Spot candles for configured symbols.
- Produces rule-based signals using EMA-50, EMA-200, RSI, and ATR.
- Adds a market-regime score that can later be enriched with AI, while keeping
  risk controls mandatory.
- Runs a persistent local paper broker with stop-loss, take-profit,
  trailing-stop, position sizing, daily loss limit, max open position controls,
  fees, and slippage.
- Parses Binance symbol filters so order quantities can respect step size and
  minimum notional rules.
- Writes a CSV trade log and can export an informational India-focused tax CSV.
- Provides a walk-forward backtester that reuses the production strategy and
  risk engine.

## Security rules

Never share your Binance secret key with another person or paste it into chat.
If you later enable live trading, create a dedicated Binance API key with:

1. **Spot trading only**.
2. **Withdrawals disabled**.
3. **IP whitelist enabled** for your server/VPS.
4. Small capital while testing.
5. Regular key rotation.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . pytest
binancetrade config
binancetrade scan
binancetrade paper-once
```

The bot defaults to paper mode and starts with simulated `10000` USDT. Paper
state is saved to `.binancetrade_state.json`; reset it with:

```bash
binancetrade reset-paper
```

## Local dashboard

Option 1 is now implemented as a **local Streamlit dashboard** for paper trading
review. Install the optional dashboard dependency and launch it with:

```bash
pip install -e '.[dashboard]'
binancetrade dashboard
```

The dashboard displays paper cash/equity, realized and daily PnL, open paper
positions, recent trade-log rows, configured symbols, and kill-switch status. It
does not place live orders, expose withdrawal functionality, or make the bot live
trading ready.

## Emergency kill switch

Create the kill-switch file to stop scans/orders:

```bash
touch .binancetrade_kill
```

Remove it to allow paper operation again:

```bash
rm .binancetrade_kill
```

## Configuration

Set environment variables to customize behavior:

| Variable | Default | Purpose |
| --- | --- | --- |
| `BT_PAPER_MODE` | `true` | Keep the bot in paper mode. |
| `BT_ENABLE_LIVE_TRADING` | `false` | Additional required flag before any future live mode. |
| `BT_BINANCE_API_KEY` | empty | Binance key for signed endpoints. Not needed for public candle scans. |
| `BT_BINANCE_API_SECRET` | empty | Binance secret. Never commit it. |
| `BT_SYMBOLS` | `BTCUSDT,ETHUSDT` | Comma-separated spot symbols. |
| `BT_CANDLE_INTERVAL` | `1h` | Binance kline interval. |
| `BT_CANDLE_LIMIT` | `250` | Candles fetched per symbol; must be at least 220. |
| `BT_STARTING_CASH` | `10000` | Paper account starting quote balance. |
| `BT_RISK_PER_TRADE_PCT` | `0.005` | 0.5% account-equity risk budget per trade. |
| `BT_MAX_POSITION_PCT` | `0.10` | Max 10% of equity in one position. |
| `BT_DAILY_LOSS_LIMIT_PCT` | `0.02` | Stop opening positions after 2% realized daily loss. |
| `BT_STOP_LOSS_PCT` | `0.01` | 1% stop loss. |
| `BT_TAKE_PROFIT_PCT` | `0.02` | 2% take profit. |
| `BT_TRAILING_STOP_PCT` | `0.008` | 0.8% trailing stop. |
| `BT_TAKER_FEE_PCT` | `0.001` | Paper taker fee model. |
| `BT_SLIPPAGE_PCT` | `0.0005` | Paper slippage model. |
| `BT_MAX_OPEN_POSITIONS` | `3` | Maximum simultaneous paper positions. |
| `BT_TRADE_LOG_PATH` | `trade_log.csv` | CSV output path. |
| `BT_STATE_PATH` | `.binancetrade_state.json` | Persistent paper account state. |
| `BT_KILL_SWITCH_PATH` | `.binancetrade_kill` | File that blocks scans/orders when present. |
| `BT_DRY_RUN_LIVE_ORDERS` | `true` | Keeps future live spot orders in dry-run if live code is extended. |

## Strategy logic

A buy signal requires all of the following:

- Price is above EMA-200.
- EMA-50 is above EMA-200.
- RSI is between 45 and 65.
- ATR is not more than 3.5% of current price.
- Market regime is classified as an uptrend.
- Regime confidence is at least the configured minimum.

A sell/protective signal is produced when the trend weakens, the price drops
below EMA-200, EMA-50 drops below EMA-200, or RSI becomes overextended. Open
paper positions can also exit through stop-loss, take-profit, or trailing-stop.

## India tax export

`binancetrade.tax.export_india_tax_csv` converts the trade log into an
informational CSV with financial-year, USDT, and INR values using a user-provided
USDINR rate. This is only a helper for your records and is **not tax advice**.

## Remaining work before real live trading

- Live account balance syncing.
- Live position and open-order reconciliation.
- Cancel/replace handling for live orders.
- More exchange-filter coverage and integration tests against Binance testnet.
- Manual approval workflow for any future live order placement.
- At least 30-90 days of successful paper trading and backtesting review.
