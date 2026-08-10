"""Resumable Dukascopy XAUUSD tick acquisition and auditable manifests."""

from __future__ import annotations

import hashlib
import json
import logging
import lzma
import struct
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .mtf_models import Tick

DATAFEED_ROOT = "https://datafeed.dukascopy.com/datafeed"
TICK_STRUCT = struct.Struct(">IIIff")
USER_AGENT = "Gold-Brain-Research/1.0"


def expected_market_hour(hour: datetime) -> bool:
    utc = hour.astimezone(UTC)
    if utc.weekday() == 5:
        return False
    if utc.weekday() == 6 and utc.hour < 22:
        return False
    return not (utc.weekday() == 4 and utc.hour >= 22)


@dataclass(frozen=True, slots=True)
class HourFile:
    hour: datetime
    path: str
    sha256: str
    compressed_bytes: int
    tick_count: int


@dataclass(frozen=True, slots=True)
class TickManifest:
    schema_version: str
    instrument: str
    source: str
    requested_start: str
    requested_end: str
    first_tick: str | None
    last_tick: str | None
    tick_count: int
    missing_hours: tuple[str, ...]
    gap_count_over_60s: int
    files: tuple[HourFile, ...]


def hourly_range(start: datetime, end: datetime) -> Iterator[datetime]:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("download boundaries must be timezone-aware")
    current = start.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    while current < end.astimezone(UTC):
        yield current
        current += timedelta(hours=1)


def hour_url(instrument: str, hour: datetime) -> str:
    utc = hour.astimezone(UTC)
    return (
        f"{DATAFEED_ROOT}/{instrument}/{utc.year:04d}/{utc.month - 1:02d}/"
        f"{utc.day:02d}/{utc.hour:02d}h_ticks.bi5"
    )


def hour_path(root: Path, instrument: str, hour: datetime) -> Path:
    utc = hour.astimezone(UTC)
    return (
        root
        / instrument
        / f"{utc.year:04d}"
        / f"{utc.month:02d}"
        / f"{utc.day:02d}"
        / f"{utc.hour:02d}h_ticks.bi5"
    )


def download_hour(
    instrument: str,
    hour: datetime,
    root: Path,
    *,
    timeout_seconds: int = 30,
    retries: int = 7,
) -> Path | None:
    target = hour_path(root, instrument, hour)
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(hour_url(instrument, hour), headers={"User-Agent": USER_AGENT})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                payload = response.read()
            if not payload:
                return None
            temporary = target.with_suffix(target.suffix + ".part")
            temporary.write_bytes(payload)
            temporary.replace(target)
            return target
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if error.code not in {429, 500, 502, 503, 504}:
                raise
            if attempt + 1 == retries:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt + 1 == retries:
                raise
        time.sleep(min(60, 2**attempt))
    return None


def decode_hour(path: Path, hour: datetime, *, price_scale: int) -> list[Tick]:
    if price_scale <= 0:
        raise ValueError("price_scale must be positive")
    raw = lzma.decompress(path.read_bytes())
    if len(raw) % TICK_STRUCT.size:
        raise ValueError(f"invalid BI5 tick payload length: {path}")
    ticks: list[Tick] = []
    for offset in range(0, len(raw), TICK_STRUCT.size):
        millis, ask_raw, bid_raw, ask_volume, bid_volume = TICK_STRUCT.unpack_from(raw, offset)
        ticks.append(
            Tick(
                timestamp=hour.astimezone(UTC) + timedelta(milliseconds=millis),
                bid=bid_raw / price_scale,
                ask=ask_raw / price_scale,
                bid_volume=float(bid_volume),
                ask_volume=float(ask_volume),
            )
        )
    pairs = zip(ticks, ticks[1:], strict=False)
    if any(right.timestamp <= left.timestamp for left, right in pairs):
        raise ValueError(f"ticks must be strictly ordered within {path}")
    return ticks


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    instrument: str,
    start: datetime,
    end: datetime,
    root: Path,
    *,
    price_scale: int,
) -> TickManifest:
    files: list[HourFile] = []
    missing: list[str] = []
    first_tick: datetime | None = None
    last_tick: datetime | None = None
    tick_count = 0
    gap_count = 0
    previous: datetime | None = None
    for hour in hourly_range(start, end):
        if not expected_market_hour(hour):
            continue
        path = hour_path(root, instrument, hour)
        if not path.exists():
            missing.append(hour.isoformat())
            continue
        ticks = decode_hour(path, hour, price_scale=price_scale)
        for tick in ticks:
            if previous is not None and tick.timestamp - previous > timedelta(seconds=60):
                gap_count += 1
            previous = tick.timestamp
        if ticks:
            first_tick = first_tick or ticks[0].timestamp
            last_tick = ticks[-1].timestamp
        tick_count += len(ticks)
        files.append(
            HourFile(
                hour=hour,
                path=str(path.relative_to(root)),
                sha256=_sha256(path),
                compressed_bytes=path.stat().st_size,
                tick_count=len(ticks),
            )
        )
    return TickManifest(
        schema_version="1.0.0",
        instrument=instrument,
        source=DATAFEED_ROOT,
        requested_start=start.astimezone(UTC).isoformat(),
        requested_end=end.astimezone(UTC).isoformat(),
        first_tick=first_tick.isoformat() if first_tick else None,
        last_tick=last_tick.isoformat() if last_tick else None,
        tick_count=tick_count,
        missing_hours=tuple(missing),
        gap_count_over_60s=gap_count,
        files=tuple(files),
    )


def write_manifest(manifest: TickManifest, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(
            asdict(manifest),
            indent=2,
            default=lambda value: value.isoformat() if isinstance(value, datetime) else str(value),
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def download_range(
    instrument: str,
    start: datetime,
    end: datetime,
    root: Path,
    *,
    timeout_seconds: int = 30,
    workers: int = 8,
) -> tuple[int, int]:
    if workers <= 0:
        raise ValueError("workers must be positive")
    hours = [hour for hour in hourly_range(start, end) if expected_market_hour(hour)]

    def acquire(hour: datetime) -> tuple[bool, bool]:
        existed = hour_path(root, instrument, hour).exists()
        try:
            result = download_hour(instrument, hour, root, timeout_seconds=timeout_seconds)
        except (TimeoutError, urllib.error.HTTPError, urllib.error.URLError) as error:
            logging.getLogger(__name__).warning(
                "hour download failed hour=%s error=%s", hour, error
            )
            return False, True
        return result is not None and not existed, result is None

    with ThreadPoolExecutor(max_workers=workers) as executor:
        outcomes = list(executor.map(acquire, hours))
    return sum(item[0] for item in outcomes), sum(item[1] for item in outcomes)
