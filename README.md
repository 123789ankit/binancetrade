# BinanceTrade

BinanceTrade is a **paper-first Binance Spot automation starter** for learning,
backtesting, and carefully simulating crypto trades before any real-money use.
It is intentionally conservative: there is no futures support, no leverage, no
margin support, and no withdrawal code.

> Financial risk notice: no trading bot, AI model, or strategy can guarantee
> profit. Crypto trading can lose money quickly. Start with paper mode, keep
> position sizes small, and consult qualified tax/financial professionals for
> India-specific obligations.

## What this tool does

- Fetches Binance Spot candles for configured symbols.
- Produces rule-based signals using EMA-50, EMA-200, RSI, and ATR.
- Adds a market-regime score that can later be enriched with AI, while keeping
  risk controls mandatory.
- Runs a local paper broker with stop-loss, take-profit, trailing-stop,
  position sizing, daily loss limit, and max open position controls.
- Writes a CSV trade log for audit and tax recordkeeping.
- Scaffolds live Binance Spot order calls, but live execution remains blocked
  until account-balance syncing and exchange filter handling are implemented.

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

The bot defaults to paper mode and starts with simulated `10000` USDT.

## Configuration

Set environment variables to customize behavior:

| Variable | Default | Purpose |
| --- | --- | --- |
| `BT_PAPER_MODE` | `true` | Keep the bot in paper mode. |
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
| `BT_MAX_OPEN_POSITIONS` | `3` | Maximum simultaneous paper positions. |
| `BT_TRADE_LOG_PATH` | `trade_log.csv` | CSV output path. |
| `BT_DRY_RUN_LIVE_ORDERS` | `true` | Keeps live spot orders in dry-run if live code is extended. |

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

## Live trading status

Live order plumbing is present only as a scaffold. `TradingEngine.run_live_once`
currently raises an error before placing any real order. This is deliberate:
real-money trading should not be enabled until exchange filters, min notional,
step size, balance syncing, reconciliation, tax exports, and kill-switch testing
are complete.
