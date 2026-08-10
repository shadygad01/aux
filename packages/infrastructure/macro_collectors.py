"""Fail-closed collectors for the two retained macro measurements.

Only observed DXY and US10Y series are returned. Network failure or insufficient
history produces an explicit unavailable factor; no neutral classification,
static yield, news-window placeholder, weighted score, or gold forecast is
fabricated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from .yahoo_chart import fetch_yahoo_candles

logger = logging.getLogger(__name__)
DXY_TICKER = "DX-Y.NYB"
TNX_TICKER = "%5ETNX"


@dataclass(frozen=True, slots=True)
class MacroFactor:
    name: str
    available: bool
    value: float | None
    start_value: float | None
    delta: float | None
    direction: str | None
    observed_at: datetime | None
    source: str
    method: str
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "factor": self.name,
            "available": self.available,
            "value": self.value,
            "start_value": self.start_value,
            "delta": self.delta,
            "direction": self.direction,
            "observed_at": self.observed_at.isoformat() if self.observed_at else None,
            "source": self.source,
            "method": self.method,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class MacroMarketSnapshot:
    captured_at: datetime
    factors: tuple[MacroFactor, ...]


class MacroCollector:
    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def acquire_snapshot(self, now: datetime) -> MacroMarketSnapshot:
        return MacroMarketSnapshot(now, (self._fetch_dxy(), self._fetch_us10y()))

    def _fetch_factor(self, name: str, ticker: str, source: str) -> MacroFactor:
        method = "Latest close and net change across the fetched five-day daily series."
        try:
            candles = fetch_yahoo_candles(ticker, "1d", "5d", self.timeout_seconds)
        except Exception as exc:
            logger.warning("%s fetch failed: %s", name, exc)
            return MacroFactor(
                name, False, None, None, None, None, None, source, method, "FETCH_FAILED"
            )
        if len(candles) < 2:
            return MacroFactor(
                name,
                False,
                candles[-1].close if candles else None,
                None,
                None,
                None,
                candles[-1].timestamp if candles else None,
                source,
                method,
                "INSUFFICIENT_HISTORY",
            )
        start, latest = candles[0], candles[-1]
        delta = round(latest.close - start.close, 4)
        direction = "UP" if delta > 0 else "DOWN" if delta < 0 else "FLAT"
        return MacroFactor(
            name=name,
            available=True,
            value=round(latest.close, 4),
            start_value=round(start.close, 4),
            delta=delta,
            direction=direction,
            observed_at=latest.timestamp,
            source=source,
            method=method,
        )

    def _fetch_dxy(self) -> MacroFactor:
        return self._fetch_factor("DXY", DXY_TICKER, "Yahoo Finance DX-Y.NYB")

    def _fetch_us10y(self) -> MacroFactor:
        return self._fetch_factor("US10Y", TNX_TICKER, "Yahoo Finance ^TNX")
