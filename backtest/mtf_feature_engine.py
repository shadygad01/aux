"""Leakage-safe interpretable H1/M15 feature snapshots from closed bars."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from statistics import fmean

from packages.domain import DecisionVerdict, LiquiditySide, RangeLocation, StructureBias
from packages.infrastructure.market_hours import classify_session
from packages.infrastructure.momentum import compute_atr, compute_macd
from packages.infrastructure.smc_detector import Candle, build_observation_from_candles

from .mtf_models import BidAskBar, Direction, ExitPlan, TradeIntent
from .risk_guidance import compute_risk_guidance


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    timestamp: datetime
    direction: Direction
    features: Mapping[str, object]
    stop_distance: float
    atr: float

    def intent(self, pattern_id: str, exit_plan: ExitPlan) -> TradeIntent:
        return TradeIntent(
            pattern_id=pattern_id,
            signal_time=self.timestamp,
            direction=self.direction,
            stop_distance=self.stop_distance,
            atr=self.atr,
            exit_plan=exit_plan,
        )


def _candles(bars: Sequence[BidAskBar]) -> list[Candle]:
    return [
        Candle(
            timestamp=bar.timestamp,
            open=bar.midpoint_open,
            high=bar.midpoint_high,
            low=bar.midpoint_low,
            close=bar.midpoint_close,
        )
        for bar in bars
    ]


def _m15_window(m15: Sequence[BidAskBar], closed_at: object, maximum: int = 720) -> list[BidAskBar]:
    from datetime import datetime

    if not isinstance(closed_at, datetime):
        raise TypeError("closed_at must be datetime")
    closed_times = [bar.closed_at for bar in m15]
    end = bisect_right(closed_times, closed_at)
    window = list(m15[max(0, end - maximum) : end])
    if window and window[-1].closed_at > closed_at:
        raise AssertionError("future M15 candle leaked into feature window")
    return window


def build_feature_snapshots(
    h1: Sequence[BidAskBar], m15: Sequence[BidAskBar], *, window: int = 720
) -> list[FeatureSnapshot]:
    snapshots: list[FeatureSnapshot] = []
    previous_bias: StructureBias | None = None
    bias_age = 0
    for index in range(59, len(h1)):
        h1_bars = list(h1[max(0, index - window + 1) : index + 1])
        h1_candles = _candles(h1_bars)
        observation = build_observation_from_candles(
            h1_candles, symbol="XAUUSD", timeframe="H1", source="dukascopy-ticks-derived"
        )
        if observation.structure is None or observation.structure.bias is StructureBias.NEUTRAL:
            previous_bias = None
            bias_age = 0
            continue
        bias = observation.structure.bias
        bias_age = bias_age + 1 if bias is previous_bias else 1
        previous_bias = bias
        direction = Direction.BUY if bias is StructureBias.BULLISH else Direction.SELL
        verdict = DecisionVerdict.BUY if direction is Direction.BUY else DecisionVerdict.SELL
        m15_bars = _m15_window(m15, h1_bars[-1].closed_at)
        if len(m15_bars) < 35:
            continue
        m15_candles = _candles(m15_bars)
        m15_observation = build_observation_from_candles(
            m15_candles, symbol="XAUUSD", timeframe="M15", source="dukascopy-ticks-derived"
        )
        atr = compute_atr(m15_candles)
        risk = compute_risk_guidance(m15_observation, verdict, atr)
        if atr is None or risk.risk_status != "OK" or risk.stop_distance is None:
            continue
        location = (
            observation.dealing_range.location(0.02)
            if observation.dealing_range is not None
            else None
        )
        required_sweep = (
            LiquiditySide.SELL_SIDE if direction is Direction.BUY else LiquiditySide.BUY_SIDE
        )
        sweep = any(
            event.side is required_sweep and event.swept and event.displacement_confirmed
            for event in observation.liquidity
        )
        m15_bias = m15_observation.structure.bias if m15_observation.structure else None
        expected_m15 = (
            StructureBias.BULLISH if direction is Direction.BUY else StructureBias.BEARISH
        )
        opposite_m15 = (
            StructureBias.BEARISH if direction is Direction.BUY else StructureBias.BULLISH
        )
        relation = (
            "ALIGNED"
            if m15_bias is expected_m15
            else "OPPOSED"
            if m15_bias is opposite_m15
            else "NOT_OPPOSED"
        )
        closes = [candle.close for candle in h1_candles]
        macd = compute_macd(closes)
        previous_macd = compute_macd(closes[:-1])
        macd_slope = (
            macd.macd_line - previous_macd.macd_line
            if macd is not None and previous_macd is not None
            else 0.0
        )
        current = h1_candles[-1]
        candle_range = current.high - current.low
        body_ratio = abs(current.close - current.open) / candle_range if candle_range else 0.0
        recent_ranges = [candle.high - candle.low for candle in h1_candles[-21:-1]]
        range_compression = candle_range / fmean(recent_ranges) if any(recent_ranges) else 1.0
        prior_day = h1_candles[-25:-1]
        prior_week = h1_candles[-121:-1]
        daily_high = max((candle.high for candle in prior_day), default=current.high)
        daily_low = min((candle.low for candle in prior_day), default=current.low)
        weekly_high = max((candle.high for candle in prior_week), default=current.high)
        weekly_low = min((candle.low for candle in prior_week), default=current.low)
        required_location = (
            RangeLocation.DISCOUNT if direction is Direction.BUY else RangeLocation.PREMIUM
        )
        h1_atr = compute_atr(h1_candles) or candle_range or 1.0
        features: dict[str, object] = {
            "h1_bos": observation.structure.break_of_structure,
            "h1_choch": observation.structure.change_of_character,
            "h1_sweep": sweep,
            "h1_location_aligned": location is required_location,
            "h1_location": location.value if location else "MISSING",
            "h1_bias_age": bias_age,
            "m15_relation": relation,
            "m15_bos": bool(
                m15_observation.structure and m15_observation.structure.break_of_structure
            ),
            "body_ratio": round(body_ratio, 4),
            "range_compression": round(range_compression, 4),
            "atr_ratio": round(atr / h1_atr, 4),
            "macd_line": macd.macd_line if macd else 0.0,
            "macd_slope": round(macd_slope, 4),
            "macd_histogram": macd.histogram if macd else 0.0,
            "macd_agrees": bool(
                macd
                and (
                    (direction is Direction.BUY and macd.macd_line > 0)
                    or (direction is Direction.SELL and macd.macd_line < 0)
                )
            ),
            "macd_slope_agrees": (macd_slope > 0 if direction is Direction.BUY else macd_slope < 0),
            "breakout_20": current.close > max(candle.high for candle in h1_candles[-21:-1]),
            "breakdown_20": current.close < min(candle.low for candle in h1_candles[-21:-1]),
            "session": classify_session(h1_bars[-1].closed_at).value,
            "weekday": h1_bars[-1].closed_at.weekday(),
            "daily_high_distance_atr": round((daily_high - current.close) / h1_atr, 4),
            "daily_low_distance_atr": round((current.close - daily_low) / h1_atr, 4),
            "weekly_high_distance_atr": round((weekly_high - current.close) / h1_atr, 4),
            "weekly_low_distance_atr": round((current.close - weekly_low) / h1_atr, 4),
            "mean_spread": round(h1_bars[-1].mean_spread, 6),
            "tick_activity": h1_bars[-1].tick_count,
        }
        snapshots.append(
            FeatureSnapshot(
                timestamp=h1_bars[-1].closed_at,
                direction=direction,
                features=features,
                stop_distance=risk.stop_distance,
                atr=atr,
            )
        )
    return snapshots
