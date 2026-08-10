"""Streaming storage for derived bars and lazy access to raw tick hours."""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Iterator, Sequence
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .dukascopy_ticks import decode_hour, hour_path, hourly_range
from .mtf_models import BidAskBar, Tick


def write_bars(path: Path, bars: Sequence[BidAskBar]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("w", encoding="utf-8") as handle:
        for bar in bars:
            payload = asdict(bar)
            payload["timestamp"] = bar.timestamp.isoformat()
            handle.write(json.dumps(payload, separators=(",", ":")) + "\n")
    temporary.replace(path)


def read_bars(path: Path) -> list[BidAskBar]:
    bars: list[BidAskBar] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            payload = json.loads(line)
            payload["timestamp"] = datetime.fromisoformat(payload["timestamp"])
            bars.append(BidAskBar(**payload))
    return bars


class TickArchive:
    def __init__(
        self,
        root: Path,
        instrument: str,
        *,
        price_scale: int,
        cache_hours: int = 168,
    ) -> None:
        self._root = root
        self._instrument = instrument
        self._price_scale = price_scale
        self._cache_hours = cache_hours
        self._cache: OrderedDict[datetime, tuple[Tick, ...]] = OrderedDict()

    def _hour(self, hour: datetime) -> tuple[Tick, ...]:
        utc = hour.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
        cached = self._cache.get(utc)
        if cached is not None:
            self._cache.move_to_end(utc)
            return cached
        path = hour_path(self._root, self._instrument, utc)
        ticks = (
            tuple(decode_hour(path, utc, price_scale=self._price_scale)) if path.exists() else ()
        )
        self._cache[utc] = ticks
        if len(self._cache) > self._cache_hours:
            self._cache.popitem(last=False)
        return ticks

    def between(self, start: datetime, end: datetime) -> list[Tick]:
        return [
            tick
            for hour in hourly_range(start, end + timedelta(hours=1))
            for tick in self._hour(hour)
            if start <= tick.timestamp <= end
        ]

    def iter_hours(
        self, start: datetime, end: datetime
    ) -> Iterator[tuple[datetime, tuple[Tick, ...]]]:
        for hour in hourly_range(start, end):
            yield hour, self._hour(hour)
