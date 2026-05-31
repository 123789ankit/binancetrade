"""Informational India-focused trade export helpers.

This module is not tax advice. It formats bot trade logs into a compact CSV that
can help a user or tax professional review crypto activity.
"""

from __future__ import annotations

import csv
from decimal import Decimal
from pathlib import Path


TAX_FIELDNAMES = [
    "timestamp_utc",
    "financial_year",
    "symbol",
    "side",
    "quantity",
    "net_quote_value_usdt",
    "net_value_inr",
    "realized_pnl_usdt",
    "realized_pnl_inr",
]


def export_india_tax_csv(trade_log_path: str, output_path: str, usd_inr_rate: Decimal) -> None:
    source = Path(trade_log_path)
    target = Path(output_path)
    if target.parent != Path("."):
        target.parent.mkdir(parents=True, exist_ok=True)
    with source.open(newline="", encoding="utf-8") as input_handle, target.open("w", newline="", encoding="utf-8") as output_handle:
        reader = csv.DictReader(input_handle)
        writer = csv.DictWriter(output_handle, fieldnames=TAX_FIELDNAMES)
        writer.writeheader()
        for row in reader:
            net = Decimal(row.get("net_quote_value") or "0")
            pnl = Decimal(row.get("realized_pnl") or "0")
            writer.writerow(
                {
                    "timestamp_utc": row["timestamp_utc"],
                    "financial_year": _financial_year(row["timestamp_utc"][:10]),
                    "symbol": row["symbol"],
                    "side": row["side"],
                    "quantity": row["quantity"],
                    "net_quote_value_usdt": str(net),
                    "net_value_inr": str(net * usd_inr_rate),
                    "realized_pnl_usdt": str(pnl),
                    "realized_pnl_inr": str(pnl * usd_inr_rate),
                }
            )


def _financial_year(iso_date: str) -> str:
    year = int(iso_date[:4])
    month = int(iso_date[5:7])
    start = year if month >= 4 else year - 1
    return f"FY{start}-{str(start + 1)[-2:]}"
