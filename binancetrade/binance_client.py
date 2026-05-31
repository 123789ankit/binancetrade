"""Minimal Binance Spot REST client.

Only spot endpoints needed by this starter bot are implemented. Withdrawal,
margin, futures, and leverage endpoints are intentionally absent.
"""

from __future__ import annotations

from decimal import Decimal
import hashlib
import hmac
import json
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Candle, OrderResult, Side, SymbolFilters


class BinanceAPIError(RuntimeError):
    """Raised when Binance or the network returns a non-success response."""


class BinanceSpotClient:
    """Small stdlib-based client for Binance Spot REST APIs."""

    def __init__(
        self,
        api_key: str | None,
        api_secret: str | None,
        base_url: str,
        *,
        timeout_seconds: int = 15,
        retries: int = 2,
    ) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.retries = retries

    def klines(self, symbol: str, interval: str, limit: int) -> list[Candle]:
        payload = self._public_get("/api/v3/klines", {"symbol": symbol, "interval": interval, "limit": limit})
        candles: list[Candle] = []
        for row in payload:
            candles.append(
                Candle(
                    open_time=int(row[0]),
                    open=Decimal(row[1]),
                    high=Decimal(row[2]),
                    low=Decimal(row[3]),
                    close=Decimal(row[4]),
                    volume=Decimal(row[5]),
                    close_time=int(row[6]),
                )
            )
        return candles

    def exchange_info(self, symbols: tuple[str, ...] | None = None) -> dict[str, Any]:
        params = {"symbols": json.dumps(list(symbols))} if symbols else {}
        return self._public_get("/api/v3/exchangeInfo", params)

    def symbol_filters(self, symbol: str) -> SymbolFilters:
        info = self.exchange_info((symbol,))
        symbols = info.get("symbols", [])
        if not symbols:
            raise BinanceAPIError(f"No exchange filters returned for {symbol}")
        raw_filters = {item["filterType"]: item for item in symbols[0].get("filters", [])}
        lot_size = raw_filters.get("LOT_SIZE", {})
        notional = raw_filters.get("NOTIONAL") or raw_filters.get("MIN_NOTIONAL") or {}
        price_filter = raw_filters.get("PRICE_FILTER", {})
        return SymbolFilters(
            symbol=symbol,
            min_quantity=Decimal(lot_size.get("minQty", "0")),
            max_quantity=Decimal(lot_size.get("maxQty", "999999999")),
            step_size=Decimal(lot_size.get("stepSize", "0.000001")),
            min_notional=Decimal(notional.get("minNotional", "0")),
            tick_size=Decimal(price_filter.get("tickSize", "0.00000001")),
        )

    def account(self) -> dict[str, Any]:
        return self._signed_request("GET", "/api/v3/account", {})

    def market_order(self, symbol: str, side: Side, quantity: Decimal, *, dry_run: bool = True) -> OrderResult:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": format(quantity, "f"),
        }
        if dry_run:
            return OrderResult(symbol, side, quantity, Decimal("0"), "DRY_RUN", "live order dry-run enabled")
        response = self._signed_request("POST", "/api/v3/order", params)
        fills = response.get("fills", [])
        price = Decimal("0")
        if fills:
            total_qty = sum(Decimal(fill["qty"]) for fill in fills)
            total_quote = sum(Decimal(fill["qty"]) * Decimal(fill["price"]) for fill in fills)
            price = total_quote / total_qty if total_qty else Decimal("0")
        return OrderResult(
            symbol,
            side,
            quantity,
            price,
            response.get("status", "UNKNOWN"),
            json.dumps(response),
            order_id=str(response.get("orderId")) if response.get("orderId") is not None else None,
        )

    def _public_get(self, path: str, params: dict[str, Any]) -> Any:
        query = urlencode(params)
        suffix = f"?{query}" if query else ""
        request = Request(f"{self.base_url}{path}{suffix}", headers={"User-Agent": "binancetrade/0.2"})
        return self._send(request)

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> Any:
        if not self.api_key or not self.api_secret:
            raise ValueError("Signed Binance requests require API credentials")
        params = {**params, "timestamp": int(time.time() * 1000), "recvWindow": 5000}
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        body = f"{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key, "User-Agent": "binancetrade/0.2"}
        url = f"{self.base_url}{path}"
        data = body.encode("utf-8") if method != "GET" else None
        if method == "GET":
            url = f"{url}?{body}"
        request = Request(url, data=data, headers=headers, method=method)
        return self._send(request)

    def _send(self, request: Request) -> Any:
        attempts = self.retries + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310 - URL is configured by user/env.
                    return json.loads(response.read().decode("utf-8"))
            except HTTPError as exc:
                payload = exc.read().decode("utf-8")
                if exc.code not in {429, 500, 502, 503, 504} or attempt == attempts - 1:
                    raise BinanceAPIError(f"Binance HTTP {exc.code}: {payload}") from exc
                last_error = exc
            except (TimeoutError, URLError) as exc:
                if attempt == attempts - 1:
                    raise BinanceAPIError(f"Binance request failed: {exc}") from exc
                last_error = exc
            time.sleep(0.25 * (attempt + 1))
        raise BinanceAPIError(f"Binance request failed: {last_error}")
