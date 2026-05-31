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
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .models import Candle, OrderResult, Side


class BinanceSpotClient:
    """Small stdlib-based client for Binance Spot REST APIs."""

    def __init__(self, api_key: str | None, api_secret: str | None, base_url: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")

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
        return OrderResult(symbol, side, quantity, price, response.get("status", "UNKNOWN"), json.dumps(response))

    def _public_get(self, path: str, params: dict[str, Any]) -> Any:
        query = urlencode(params)
        request = Request(f"{self.base_url}{path}?{query}", headers={"User-Agent": "binancetrade/0.1"})
        with urlopen(request, timeout=15) as response:  # noqa: S310 - URL is configured by user/env.
            return json.loads(response.read().decode("utf-8"))

    def _signed_request(self, method: str, path: str, params: dict[str, Any]) -> Any:
        if not self.api_key or not self.api_secret:
            raise ValueError("Signed Binance requests require API credentials")
        params = {**params, "timestamp": int(time.time() * 1000), "recvWindow": 5000}
        query = urlencode(params)
        signature = hmac.new(self.api_secret.encode(), query.encode(), hashlib.sha256).hexdigest()
        body = f"{query}&signature={signature}"
        headers = {"X-MBX-APIKEY": self.api_key, "User-Agent": "binancetrade/0.1"}
        url = f"{self.base_url}{path}"
        data = body.encode("utf-8") if method != "GET" else None
        if method == "GET":
            url = f"{url}?{body}"
        request = Request(url, data=data, headers=headers, method=method)
        with urlopen(request, timeout=15) as response:  # noqa: S310 - URL is configured by user/env.
            return json.loads(response.read().decode("utf-8"))
