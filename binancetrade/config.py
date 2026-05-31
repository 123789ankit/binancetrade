"""Runtime configuration for the trading bot.

The defaults intentionally keep the bot in paper mode with conservative risk.
Live trading requires explicit opt-in flags and valid Binance API credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import os

TRUTHY = {"1", "true", "yes", "on"}
FALSY = {"0", "false", "no", "off"}


@dataclass(frozen=True)
class BotConfig:
    """Configuration loaded from environment variables."""

    paper_mode: bool = True
    enable_live_trading: bool = False
    api_key: str | None = None
    api_secret: str | None = None
    base_url: str = "https://api.binance.com"
    symbols: tuple[str, ...] = ("BTCUSDT", "ETHUSDT")
    quote_asset: str = "USDT"
    candle_interval: str = "1h"
    candle_limit: int = 250
    poll_seconds: int = 60
    starting_cash: Decimal = Decimal("10000")
    risk_per_trade_pct: Decimal = Decimal("0.005")
    max_position_pct: Decimal = Decimal("0.10")
    daily_loss_limit_pct: Decimal = Decimal("0.02")
    stop_loss_pct: Decimal = Decimal("0.01")
    take_profit_pct: Decimal = Decimal("0.02")
    trailing_stop_pct: Decimal = Decimal("0.008")
    max_open_positions: int = 3
    min_confidence: Decimal = Decimal("0.60")
    taker_fee_pct: Decimal = Decimal("0.001")
    slippage_pct: Decimal = Decimal("0.0005")
    trade_log_path: str = "trade_log.csv"
    state_path: str = ".binancetrade_state.json"
    kill_switch_path: str = ".binancetrade_kill"
    dry_run_live_orders: bool = True
    request_timeout_seconds: int = 15
    request_retries: int = 2

    def validate(self) -> None:
        if not self.symbols:
            raise ValueError("At least one trading symbol must be configured")
        if self.candle_limit < 220:
            raise ValueError("BT_CANDLE_LIMIT must be at least 220 for EMA-200 strategy")
        decimal_fields = {
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "max_position_pct": self.max_position_pct,
            "daily_loss_limit_pct": self.daily_loss_limit_pct,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "trailing_stop_pct": self.trailing_stop_pct,
            "min_confidence": self.min_confidence,
            "taker_fee_pct": self.taker_fee_pct,
            "slippage_pct": self.slippage_pct,
        }
        for name, value in decimal_fields.items():
            if value < 0:
                raise ValueError(f"{name} must be zero or greater")
        if self.risk_per_trade_pct <= 0 or self.risk_per_trade_pct > Decimal("0.02"):
            raise ValueError("risk_per_trade_pct should remain > 0 and <= 2% for capital protection")
        if self.max_position_pct <= 0 or self.max_position_pct > Decimal("0.25"):
            raise ValueError("max_position_pct should remain > 0 and <= 25% for this starter bot")
        if self.daily_loss_limit_pct <= 0:
            raise ValueError("daily_loss_limit_pct must be greater than zero")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be at least 1")
        if self.request_timeout_seconds < 1:
            raise ValueError("request_timeout_seconds must be at least 1")
        if self.request_retries < 0:
            raise ValueError("request_retries cannot be negative")
        if not self.paper_mode and (not self.api_key or not self.api_secret):
            raise ValueError("Live mode requires BT_BINANCE_API_KEY and BT_BINANCE_API_SECRET")
        if not self.paper_mode and not self.enable_live_trading:
            raise ValueError("Live mode requires BT_ENABLE_LIVE_TRADING=true")


def load_config(env: dict[str, str] | None = None) -> BotConfig:
    """Load and validate config from environment variables."""

    source = os.environ if env is None else env
    config = BotConfig(
        paper_mode=_bool(source.get("BT_PAPER_MODE"), default=True),
        enable_live_trading=_bool(source.get("BT_ENABLE_LIVE_TRADING"), default=False),
        api_key=_optional(source.get("BT_BINANCE_API_KEY")),
        api_secret=_optional(source.get("BT_BINANCE_API_SECRET")),
        base_url=source.get("BT_BINANCE_BASE_URL", BotConfig.base_url),
        symbols=_symbols(source.get("BT_SYMBOLS", ",".join(BotConfig.symbols))),
        quote_asset=source.get("BT_QUOTE_ASSET", BotConfig.quote_asset),
        candle_interval=source.get("BT_CANDLE_INTERVAL", BotConfig.candle_interval),
        candle_limit=_int(source.get("BT_CANDLE_LIMIT"), BotConfig.candle_limit),
        poll_seconds=_int(source.get("BT_POLL_SECONDS"), BotConfig.poll_seconds),
        starting_cash=_decimal(source.get("BT_STARTING_CASH"), BotConfig.starting_cash),
        risk_per_trade_pct=_decimal(source.get("BT_RISK_PER_TRADE_PCT"), BotConfig.risk_per_trade_pct),
        max_position_pct=_decimal(source.get("BT_MAX_POSITION_PCT"), BotConfig.max_position_pct),
        daily_loss_limit_pct=_decimal(source.get("BT_DAILY_LOSS_LIMIT_PCT"), BotConfig.daily_loss_limit_pct),
        stop_loss_pct=_decimal(source.get("BT_STOP_LOSS_PCT"), BotConfig.stop_loss_pct),
        take_profit_pct=_decimal(source.get("BT_TAKE_PROFIT_PCT"), BotConfig.take_profit_pct),
        trailing_stop_pct=_decimal(source.get("BT_TRAILING_STOP_PCT"), BotConfig.trailing_stop_pct),
        max_open_positions=_int(source.get("BT_MAX_OPEN_POSITIONS"), BotConfig.max_open_positions),
        min_confidence=_decimal(source.get("BT_MIN_CONFIDENCE"), BotConfig.min_confidence),
        taker_fee_pct=_decimal(source.get("BT_TAKER_FEE_PCT"), BotConfig.taker_fee_pct),
        slippage_pct=_decimal(source.get("BT_SLIPPAGE_PCT"), BotConfig.slippage_pct),
        trade_log_path=source.get("BT_TRADE_LOG_PATH", BotConfig.trade_log_path),
        state_path=source.get("BT_STATE_PATH", BotConfig.state_path),
        kill_switch_path=source.get("BT_KILL_SWITCH_PATH", BotConfig.kill_switch_path),
        dry_run_live_orders=_bool(source.get("BT_DRY_RUN_LIVE_ORDERS"), default=True),
        request_timeout_seconds=_int(source.get("BT_REQUEST_TIMEOUT_SECONDS"), BotConfig.request_timeout_seconds),
        request_retries=_int(source.get("BT_REQUEST_RETRIES"), BotConfig.request_retries),
    )
    config.validate()
    return config


def _optional(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _symbols(value: str) -> tuple[str, ...]:
    return tuple(symbol.strip().upper() for symbol in value.split(",") if symbol.strip())


def _bool(value: str | None, *, default: bool) -> bool:
    if value is None or value == "":
        return default
    lowered = value.strip().lower()
    if lowered in TRUTHY:
        return True
    if lowered in FALSY:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _decimal(value: str | None, default: Decimal) -> Decimal:
    if value is None or value == "":
        return default
    return Decimal(value)


def _int(value: str | None, default: int) -> int:
    if value is None or value == "":
        return default
    return int(value)
