"""Chunked historical H1 candle fetch.

Yahoo's `range` preset (used by the live pipeline's fetch_yahoo_candles)
caps intraday history at a server-enforced boundary regardless of what
range is requested -- there is no "next page" via `range` alone. This
walks backward in explicit period1/period2 windows via
fetch_yahoo_candles_between, chunked small enough to stay well inside
every documented Yahoo intraday tier, and stitches the results together.

The true H1 history boundary is not assumed here: `fetch_h1_history` stops
as soon as a chunk request returns nothing, and callers should log/inspect
the earliest timestamp actually returned rather than trust `total_days`
was fully satisfied.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from packages.infrastructure.smc_detector import Candle
from packages.infrastructure.yahoo_chart import fetch_yahoo_candles_between

logger = logging.getLogger(__name__)

DEFAULT_CHUNK_DAYS = 60


def fetch_h1_history(
    ticker: str,
    total_days: int,
    *,
    interval: str = "1h",
    chunk_days: int = DEFAULT_CHUNK_DAYS,
    timeout_seconds: int = 10,
    now: datetime | None = None,
) -> list[Candle]:
    """Fetch up to `total_days` of history by walking backward from `now`
    in `chunk_days`-sized windows, merging and de-duplicating by timestamp.

    Stops early (logging why) the first time a chunk returns no candles --
    that is the empirical signal for the real history boundary, not an
    assumed constant.
    """
    if total_days <= 0:
        raise ValueError("total_days must be positive")
    if chunk_days <= 0:
        raise ValueError("chunk_days must be positive")

    end = now if now is not None else datetime.now(UTC)
    if end.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    start_boundary = end - timedelta(days=total_days)

    by_timestamp: dict[datetime, Candle] = {}
    window_end = end
    while window_end > start_boundary:
        window_start = max(window_end - timedelta(days=chunk_days), start_boundary)
        chunk = fetch_yahoo_candles_between(
            ticker,
            interval,
            int(window_start.timestamp()),
            int(window_end.timestamp()),
            timeout_seconds,
        )
        if not chunk:
            logger.info(
                f"No candles returned for [{window_start.isoformat()}, "
                f"{window_end.isoformat()}) -- stopping; this is likely the real "
                f"Yahoo history boundary for interval={interval}."
            )
            break
        for candle in chunk:
            by_timestamp[candle.timestamp] = candle
        window_end = window_start

    candles = sorted(by_timestamp.values(), key=lambda c: c.timestamp)
    if candles:
        logger.info(
            f"Fetched {len(candles)} candles spanning "
            f"{candles[0].timestamp.isoformat()} to {candles[-1].timestamp.isoformat()}."
        )
    return candles
