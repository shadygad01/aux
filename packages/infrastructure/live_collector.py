"""Fail-closed live XAUUSD collector with one authoritative spot anchor.

The only authoritative price is the XAU spot quote. Yahoo ``GC=F`` candles
may supply the shape of history only after every candle is anchored by the
current spot/futures basis. Unanchored futures candles are never published as
XAUUSD evidence. True historical spot candles will replace this proxy when
the owner-supplied dataset is ingested.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import UTC, datetime

from packages.domain import MarketObservation

from .momentum import MacdResult, compute_macd
from .smc_detector import MIN_CANDLES_FOR_STRUCTURE, Candle, build_observation_from_candles
from .yahoo_chart import fetch_yahoo_candles

logger = logging.getLogger(__name__)

SPOT_GOLD_API_URL = "https://api.gold-api.com/price/XAU"
GOLD_TICKER = "GC=F"
_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"


@dataclass(frozen=True, slots=True)
class LiveMarketSnapshot:
    observation: MarketObservation
    source: str
    momentum: MacdResult | None
    spot_price: float | None
    candles: tuple[Candle, ...] = ()


class LiveMarketCollector:
    """Acquire one canonical spot-anchored snapshot for an artifact evaluation."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds
        self._snapshot_cache: dict[tuple[str, str, str], LiveMarketSnapshot] = {}

    def fetch_live_observation(
        self,
        fallback_raw: dict[str, object] | None = None,
        *,
        interval: str = "1h",
        chart_range: str = "1mo",
        timeframe: str = "H1",
    ) -> tuple[MarketObservation, str]:
        snapshot = self.fetch_live_snapshot(
            fallback_raw,
            interval=interval,
            chart_range=chart_range,
            timeframe=timeframe,
        )
        return snapshot.observation, snapshot.source

    def fetch_live_snapshot(
        self,
        fallback_raw: dict[str, object] | None = None,
        *,
        interval: str = "1h",
        chart_range: str = "1mo",
        timeframe: str = "H1",
    ) -> LiveMarketSnapshot:
        """Fetch spot once, then build technical evidence only when it can anchor history."""
        del fallback_raw  # compatibility only; fabricated fallback observations are forbidden
        cache_key = (interval, chart_range, timeframe)
        cached = self._snapshot_cache.get(cache_key)
        if cached is not None:
            return cached

        candles: list[Candle] = []
        try:
            candles = fetch_yahoo_candles(GOLD_TICKER, interval, chart_range, self.timeout_seconds)
        except Exception as exc:
            logger.warning("Candle proxy unavailable: %s", exc)

        spot_price: float | None = None
        try:
            spot_price = self._fetch_spot_price()
        except Exception as exc:
            logger.warning("Spot gold API unavailable: %s", exc)

        if spot_price is not None and len(candles) >= MIN_CANDLES_FOR_STRUCTURE:
            offset = candles[-1].close - spot_price
            anchored = [
                Candle(
                    timestamp=candle.timestamp,
                    open=round(candle.open - offset, 4),
                    high=round(candle.high - offset, 4),
                    low=round(candle.low - offset, 4),
                    close=round(candle.close - offset, 4),
                )
                for candle in candles
            ]
            momentum = compute_macd([candle.close for candle in anchored])
            observation = build_observation_from_candles(
                anchored,
                symbol="XAUUSD",
                timeframe=timeframe,
                source=f"spot-anchored-gc-f-proxy-{interval}",
                macd_value=momentum.macd_line if momentum is not None else None,
            )
            snapshot = LiveMarketSnapshot(
                observation=observation,
                source=f"LIVE:xauusd-spot-anchored-gc-f-proxy-{interval}",
                momentum=momentum,
                spot_price=spot_price,
                candles=tuple(anchored),
            )
            self._snapshot_cache[cache_key] = snapshot
            return snapshot

        if spot_price is not None:
            observation = MarketObservation(
                symbol="XAUUSD",
                timeframe=timeframe,
                observed_at=datetime.now(UTC),
                structure=None,
                dealing_range=None,
                liquidity=(),
                source="spot-gold-api-price-only",
                execution_timeframe=timeframe,
            )
            snapshot = LiveMarketSnapshot(
                observation=observation,
                source="LIVE:spot-gold-api-price-only",
                momentum=None,
                spot_price=spot_price,
            )
            self._snapshot_cache[cache_key] = snapshot
            return snapshot

        observation = MarketObservation(
            symbol="XAUUSD",
            timeframe=timeframe,
            observed_at=datetime.now(UTC),
            structure=None,
            dealing_range=None,
            liquidity=(),
            source="no-authoritative-spot-source",
            execution_timeframe=timeframe,
        )
        snapshot = LiveMarketSnapshot(
            observation=observation,
            source="FALLBACK:no-authoritative-spot-source",
            momentum=None,
            spot_price=None,
        )
        self._snapshot_cache[cache_key] = snapshot
        return snapshot

    def _fetch_spot_price(self) -> float | None:
        request = urllib.request.Request(SPOT_GOLD_API_URL, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
        price = data.get("price") if isinstance(data, dict) else None
        return float(price) if isinstance(price, int | float) else None
