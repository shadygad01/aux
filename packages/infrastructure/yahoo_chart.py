"""Shared Yahoo Finance chart-endpoint fetching and parsing.

Used by both live_collector.py (intraday XAUUSD structure) and
macro_collectors.py (daily candles for PDH/PDL/PWH/PWL/PMH/PML liquidity
reference levels) so the same defensive JSON parsing isn't duplicated.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime

from .smc_detector import Candle

CHART_URL_TEMPLATE = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval={interval}&range={chart_range}"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


def fetch_yahoo_candles(
    ticker: str, interval: str, chart_range: str, timeout_seconds: int
) -> list[Candle]:
    """Fetch and parse a Yahoo Finance chart response into an OHLC candle series."""
    url = CHART_URL_TEMPLATE.format(ticker=ticker, interval=interval, chart_range=chart_range)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
        if response.status != 200:
            return []
        data = json.loads(response.read().decode("utf-8"))
    if not isinstance(data, dict):
        return []
    return parse_yahoo_chart_candles(data)


def parse_yahoo_chart_candles(data: dict[str, object]) -> list[Candle]:
    """Parse a Yahoo Finance chart API response into a full OHLC candle series."""
    chart = data.get("chart")
    if not isinstance(chart, dict):
        return []
    results = chart.get("result")
    if not isinstance(results, list) or not results:
        return []
    result = results[0]
    if not isinstance(result, dict):
        return []

    timestamps = result.get("timestamp")
    indicators = result.get("indicators")
    if not isinstance(timestamps, list) or not isinstance(indicators, dict):
        return []

    quotes = indicators.get("quote")
    if not isinstance(quotes, list) or not quotes:
        return []
    quote = quotes[0]
    if not isinstance(quote, dict):
        return []

    opens = quote.get("open")
    highs = quote.get("high")
    lows = quote.get("low")
    closes = quote.get("close")
    if (
        not isinstance(opens, list)
        or not isinstance(highs, list)
        or not isinstance(lows, list)
        or not isinstance(closes, list)
    ):
        return []

    candles: list[Candle] = []
    for ts, o, h, low, c in zip(timestamps, opens, highs, lows, closes, strict=False):
        if not all(isinstance(v, (int, float)) for v in (ts, o, h, low, c)):
            continue
        candles.append(
            Candle(
                timestamp=datetime.fromtimestamp(int(ts), tz=UTC),
                open=float(o),
                high=float(h),
                low=float(low),
                close=float(c),
            )
        )
    return candles
