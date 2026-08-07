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
from .yahoo_chart import fetch_yahoo_candles

logger = logging.getLogger(__name__)

SPOT_GOLD_API_URL = "https://api.gold-api.com/price/XAU"
GOLD_TICKER = "GC=F"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


class LiveMarketCollector:
    """Acquires live market observation facts for XAUUSD spot gold without paid services."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_live_observation(
        self,
        fallback_raw: dict[str, object] | None = None,
        *,
        interval: str = "1h",
        chart_range: str = "1mo",
        timeframe: str = "H1",
    ) -> tuple[MarketObservation, str]:
        """Fetch a live candle series and derive real SMC structure from it.

        `interval`/`chart_range` select the Yahoo Finance candle granularity
        (e.g. interval="5m", chart_range="5d" for a genuine M5 observation
        instead of reusing the H1 structure under a different label).

        Falls back to a price-only observation (honest missing structure) if
        only the spot price ticker is reachable, and to a fully-honest empty
        observation if nothing is reachable at all.
        """
        # 1. Primary: real candle history at the requested granularity.
        try:
            candles = fetch_yahoo_candles(GOLD_TICKER, interval, chart_range, self.timeout_seconds)
            if len(candles) >= MIN_CANDLES_FOR_STRUCTURE:
                try:
                    spot_price = self._fetch_spot_price()
                    if spot_price is not None and candles:
                        futures_last = candles[-1].close
                        offset = futures_last - spot_price
                        if abs(offset) > 0.01:
                            candles = [
                                Candle(
                                    timestamp=c.timestamp,
                                    open=round(c.open - offset, 4),
                                    high=round(c.high - offset, 4),
                                    low=round(c.low - offset, 4),
                                    close=round(c.close - offset, 4),
                                )
                                for c in candles
                            ]
                except Exception as spot_exc:
                    logger.warning(f"Spot price alignment skipped: {spot_exc}")

                obs = build_observation_from_candles(
                    candles,
                    symbol="XAUUSD",
                    timeframe=timeframe,
                    source=f"live-api:yahoo-finance-gold-futures-{interval}",
                )
                return obs, f"LIVE:yahoo-finance-gold-futures-smc-{interval}"
        except Exception as exc:
            logger.warning(f"Candle feed unavailable: {exc}")

        # 2. Secondary: spot price ticker only — no candle history means no
        # honest structure classification, so structure/dealing range stay None.
        try:
            price = self._fetch_spot_price()
            if price is not None:
                obs = MarketObservation(
                    symbol="XAUUSD",
                    timeframe=timeframe,
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
            timeframe=timeframe,
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
