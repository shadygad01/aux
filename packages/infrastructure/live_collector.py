"""Production-compatible free live market data collector for XAUUSD spot gold.

Fetches a real OHLC candle series from free public endpoints and runs actual
Smart Money Concepts structure detection (see `smc_detector.py`) on it — no
paid services, no fabricated evidence. When structure can't be classified
from the available candles, the observation honestly carries None structure
and dealing range: the decision engine already treats missing evidence as a
hard WAIT gate, so an honest gap here is correct behavior, not a bug.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from datetime import UTC, datetime

from packages.domain import MarketObservation

from .smc_detector import MIN_CANDLES_FOR_STRUCTURE, Candle, build_observation_from_candles

logger = logging.getLogger(__name__)

SPOT_GOLD_API_URL = "https://api.gold-api.com/price/XAU"
CANDLE_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1h&range=1mo"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


class LiveMarketCollector:
    """Acquires live market observation facts for XAUUSD spot gold without paid services."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_live_observation(
        self, fallback_raw: dict[str, object] | None = None
    ) -> tuple[MarketObservation, str]:
        """Fetch a live candle series and derive real SMC structure from it.

        Falls back to a price-only observation (honest missing structure) if
        only the spot price ticker is reachable, and to a fully-honest empty
        observation if nothing is reachable at all.
        """
        # 1. Primary: hourly candle history, real fractal SMC structure.
        try:
            candles = self._fetch_candles(CANDLE_CHART_URL)
            if len(candles) >= MIN_CANDLES_FOR_STRUCTURE:
                obs = build_observation_from_candles(
                    candles,
                    symbol="XAUUSD",
                    timeframe="H1",
                    source="live-api:yahoo-finance-gold-futures",
                )
                return obs, "LIVE:yahoo-finance-gold-futures-smc"
        except Exception as exc:
            logger.warning(f"Candle feed unavailable: {exc}")

        # 2. Secondary: spot price ticker only — no candle history means no
        # honest structure classification, so structure/dealing range stay None.
        try:
            price = self._fetch_spot_price()
            if price is not None:
                obs = MarketObservation(
                    symbol="XAUUSD",
                    timeframe="H1",
                    observed_at=datetime.now(UTC),
                    structure=None,
                    dealing_range=None,
                    liquidity=(),
                    source="spot-gold-api-price-only",
                )
                return obs, "LIVE:spot-gold-api-price-only"
        except Exception as exc:
            logger.warning(f"Spot gold API unavailable: {exc}")

        # 3. Nothing reachable — an honest empty observation, not a fabricated one.
        default_obs = MarketObservation(
            symbol="XAUUSD",
            timeframe="H1",
            observed_at=datetime.now(UTC),
            structure=None,
            dealing_range=None,
            liquidity=(),
            source="no-data-source-reachable",
        )
        return default_obs, "FALLBACK:no-data-source-reachable"

    def _fetch_spot_price(self) -> float | None:
        req = urllib.request.Request(SPOT_GOLD_API_URL, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
        price_val = data.get("price") if isinstance(data, dict) else None
        if isinstance(price_val, (int, float)):
            return float(price_val)
        return None

    def _fetch_candles(self, url: str) -> list[Candle]:
        req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                return []
            data = json.loads(response.read().decode("utf-8"))
        if not isinstance(data, dict):
            return []
        return _parse_chart_candles(data)


def _parse_chart_candles(data: dict[str, object]) -> list[Candle]:
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
