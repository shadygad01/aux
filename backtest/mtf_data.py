"""Aggregate one canonical bid/ask tick stream into aligned closed bars."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime, timedelta

from .mtf_models import BidAskBar, Tick

M5_SECONDS = 300
M15_SECONDS = 900
H1_SECONDS = 3600


def _bucket(timestamp: datetime, seconds: int) -> datetime:
    epoch = int(timestamp.astimezone(UTC).timestamp())
    return datetime.fromtimestamp(epoch - epoch % seconds, tz=UTC)


def ticks_to_bars(
    ticks: Iterable[Tick], seconds: int = M5_SECONDS, *, closed_before: datetime | None = None
) -> list[BidAskBar]:
    if seconds <= 0:
        raise ValueError("seconds must be positive")
    ordered = sorted(ticks, key=lambda tick: tick.timestamp)
    if len({tick.timestamp for tick in ordered}) != len(ordered):
        raise ValueError("duplicate tick timestamps are not allowed")
    groups: dict[datetime, list[Tick]] = {}
    for tick in ordered:
        groups.setdefault(_bucket(tick.timestamp, seconds), []).append(tick)
    bars: list[BidAskBar] = []
    for timestamp, bucket_ticks in sorted(groups.items()):
        if closed_before is not None and timestamp + timedelta(seconds=seconds) > closed_before:
            continue
        spreads = [tick.ask - tick.bid for tick in bucket_ticks]
        bids = [tick.bid for tick in bucket_ticks]
        asks = [tick.ask for tick in bucket_ticks]
        bars.append(
            BidAskBar(
                timestamp=timestamp,
                seconds=seconds,
                bid_open=bids[0],
                bid_high=max(bids),
                bid_low=min(bids),
                bid_close=bids[-1],
                ask_open=asks[0],
                ask_high=max(asks),
                ask_low=min(asks),
                ask_close=asks[-1],
                tick_count=len(bucket_ticks),
                bid_volume=sum(tick.bid_volume for tick in bucket_ticks),
                ask_volume=sum(tick.ask_volume for tick in bucket_ticks),
                mean_spread=sum(spreads) / len(spreads),
            )
        )
    return bars


def aggregate_bars(bars: Sequence[BidAskBar], seconds: int) -> list[BidAskBar]:
    if not bars:
        return []
    source_seconds = bars[0].seconds
    if seconds <= source_seconds or seconds % source_seconds:
        raise ValueError("target duration must be an integer multiple of source duration")
    if any(bar.seconds != source_seconds for bar in bars):
        raise ValueError("source bars must have one duration")
    groups: dict[datetime, list[BidAskBar]] = {}
    for bar in sorted(bars, key=lambda item: item.timestamp):
        groups.setdefault(_bucket(bar.timestamp, seconds), []).append(bar)
    expected = seconds // source_seconds
    result: list[BidAskBar] = []
    for timestamp, children in sorted(groups.items()):
        expected_times = [
            timestamp + timedelta(seconds=index * source_seconds) for index in range(expected)
        ]
        if [child.timestamp for child in children] != expected_times:
            continue
        result.append(
            BidAskBar(
                timestamp=timestamp,
                seconds=seconds,
                bid_open=children[0].bid_open,
                bid_high=max(child.bid_high for child in children),
                bid_low=min(child.bid_low for child in children),
                bid_close=children[-1].bid_close,
                ask_open=children[0].ask_open,
                ask_high=max(child.ask_high for child in children),
                ask_low=min(child.ask_low for child in children),
                ask_close=children[-1].ask_close,
                tick_count=sum(child.tick_count for child in children),
                bid_volume=sum(child.bid_volume for child in children),
                ask_volume=sum(child.ask_volume for child in children),
                mean_spread=sum(child.mean_spread * child.tick_count for child in children)
                / sum(child.tick_count for child in children),
            )
        )
    return result


def validate_bar_lineage(
    m5: Sequence[BidAskBar],
    m15: Sequence[BidAskBar],
    h1: Sequence[BidAskBar],
) -> None:
    rebuilt_m15 = aggregate_bars(m5, M15_SECONDS)
    rebuilt_h1 = aggregate_bars(m5, H1_SECONDS)
    if list(m15) != rebuilt_m15:
        raise ValueError("M15 bars do not exactly match M5 lineage")
    if list(h1) != rebuilt_h1:
        raise ValueError("H1 bars do not exactly match M5 lineage")
