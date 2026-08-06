"""Free production-compatible Macro Collectors for DXY, US10Y, News, and Reference Levels.

All collectors enforce timeouts and graceful fallback. Two gaps are honestly
labeled rather than fabricated: no verified free 2-year Treasury yield source
was identified (us02y stays a static placeholder), and no free, reliable
economic-calendar API was identified (news environment stays a static
placeholder) — see the docstrings on `_fetch_yield_environment` and
`_fetch_news_environment` below.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from datetime import datetime

from packages.domain import (
    DollarStrength,
    LiquidityReferenceEvidence,
    LiquidityReferenceLevel,
    MacroAssessment,
    MacroContext,
    NewsEnvironment,
    NewsImpact,
    NewsWindow,
    YieldEnvironment,
    YieldRegime,
)

from .smc_detector import Candle, SwingKind, SwingPoint, detect_sweep_from_swing
from .yahoo_chart import fetch_yahoo_candles

logger = logging.getLogger(__name__)

DXY_TICKER = "DX-Y.NYB"
TNX_TICKER = "%5ETNX"
GOLD_TICKER = "GC=F"

# (level pair, timestamp bucket key) — day/week/month grouping for the
# previous *complete* period's high/low from real daily candle history.
_PERIOD_BUCKETS: tuple[
    tuple[LiquidityReferenceLevel, LiquidityReferenceLevel, Callable[[datetime], object]], ...
] = (
    (
        LiquidityReferenceLevel.PDH,
        LiquidityReferenceLevel.PDL,
        lambda ts: (ts.year, ts.month, ts.day),
    ),
    (LiquidityReferenceLevel.PWH, LiquidityReferenceLevel.PWL, lambda ts: ts.isocalendar()[:2]),
    (LiquidityReferenceLevel.PMH, LiquidityReferenceLevel.PML, lambda ts: (ts.year, ts.month)),
)


class MacroCollector:
    """Collects free macro facts and produces canonical MacroContext and MacroAssessment."""

    def __init__(self, timeout_seconds: int = 5) -> None:
        self.timeout_seconds = timeout_seconds

    def acquire_macro_context(self, now: datetime) -> MacroContext:
        """Fetch free DXY, Yields, News, and Reference Levels with graceful fallback."""
        dollar_strength = self._fetch_dxy_strength()
        yield_env = self._fetch_yield_environment()
        news_env = self._fetch_news_environment()
        liquidity_refs = self._fetch_liquidity_references()

        return MacroContext(
            context_id=f"MACRO-CTX-{now.strftime('%Y%m%d-%H%M')}",
            dollar_strength=dollar_strength,
            yield_environment=yield_env,
            news_environment=news_env,
            liquidity_references=liquidity_refs,
            observed_at=now,
            ttl_seconds=3600,
        )

    def evaluate_macro_assessment(
        self, macro_context: MacroContext, evaluated_at: datetime
    ) -> MacroAssessment:
        """Evaluate MacroContext to produce MacroAssessment score and WAIT signals."""
        force_wait = False
        wait_reason = ""
        evidence_items: list[str] = []

        if macro_context.news_environment.unresolved_high_impact:
            force_wait = True
            event_name = macro_context.news_environment.event_name
            wait_reason = f"High-impact unresolved news active: {event_name}"
            evidence_items.append(f"FORCED WAIT: {wait_reason}")

        score = 0.50
        conf_mod = 0.0

        ds = macro_context.dollar_strength
        if ds in (DollarStrength.BEARISH, DollarStrength.STRONG_BEARISH):
            score += 0.25
            conf_mod += 0.10
            evidence_items.append(f"DXY Dollar Strength is {ds} (Bullish for Gold)")
        elif ds in (DollarStrength.BULLISH, DollarStrength.STRONG_BULLISH):
            score -= 0.20
            conf_mod -= 0.10
            evidence_items.append(f"DXY Dollar Strength is {ds} (Bearish for Gold)")
        else:
            evidence_items.append("DXY Dollar Strength is NEUTRAL")

        if macro_context.yield_environment.yield_direction == "DOWN":
            score += 0.15
            conf_mod += 0.05
            evidence_items.append("US10Y Yield direction is DOWN (Bullish for Gold)")
        elif macro_context.yield_environment.yield_direction == "UP":
            score -= 0.15
            conf_mod -= 0.05
            evidence_items.append("US10Y Yield direction is UP (Bearish for Gold)")

        swept_levels = [lr.level for lr in macro_context.liquidity_references if lr.swept]
        if swept_levels:
            evidence_items.append(f"Swept Liquidity Reference Levels: {', '.join(swept_levels)}")

        final_score = round(max(0.0, min(1.0, score)), 4)
        final_conf_mod = round(max(-0.25, min(0.25, conf_mod)), 4)

        return MacroAssessment(
            assessment_id=f"MACRO-ASM-{evaluated_at.strftime('%Y%m%d-%H%M')}",
            macro_score=final_score,
            confidence_modifier=final_conf_mod,
            force_wait=force_wait,
            wait_reason=wait_reason,
            evidence=tuple(evidence_items),
            evaluated_at=evaluated_at,
        )

    def _fetch_dxy_strength(self) -> DollarStrength:
        """Fetch real DXY chart data from a free endpoint, or return NEUTRAL on failure."""
        try:
            candles = fetch_yahoo_candles(DXY_TICKER, "1d", "5d", self.timeout_seconds)
            if len(candles) >= 2:
                diff = candles[-1].close - candles[0].close
                if diff < -0.5:
                    return DollarStrength.STRONG_BEARISH
                if diff < 0:
                    return DollarStrength.BEARISH
                if diff > 0.5:
                    return DollarStrength.STRONG_BULLISH
                if diff > 0:
                    return DollarStrength.BULLISH
        except Exception as exc:
            logger.warning(f"DXY fetch failed: {exc}")

        return DollarStrength.NEUTRAL

    def _fetch_yield_environment(self) -> YieldEnvironment:
        """Fetch the real US10Y Treasury yield.

        us02y stays a static placeholder: no verified free 2-year Treasury
        yield data source was identified (Yahoo's ^IRX is a 13-week T-bill,
        not the 2-year note — using it would mislabel one instrument as
        another, which is worse than an honestly-static placeholder).
        """
        us10y_val = 4.25
        us02y_val = 4.50  # static placeholder — see docstring above
        direction = "NEUTRAL"

        try:
            candles = fetch_yahoo_candles(TNX_TICKER, "1d", "5d", self.timeout_seconds)
            if candles:
                us10y_val = round(candles[-1].close, 2)
                if len(candles) >= 2:
                    direction = "DOWN" if candles[-1].close < candles[0].close else "UP"
        except Exception as exc:
            logger.warning(f"TNX yield fetch failed: {exc}")

        return YieldEnvironment(
            us10y=us10y_val,
            us02y=us02y_val,
            yield_direction=direction,
            yield_momentum="MODERATE",
            regime=YieldRegime.NEUTRAL,
        )

    def _fetch_news_environment(self) -> NewsEnvironment:
        """Static placeholder: no free, reliable economic-calendar API was
        identified. This always reports CLEAR/no-high-impact-event — that is
        NOT a verified fact about real news conditions, just the absence of
        a wired data source. Treat force_wait derived from this as inactive
        by construction, not as a checked-and-cleared news window.
        """
        return NewsEnvironment(
            impact=NewsImpact.IGNORE,
            window=NewsWindow.CLEAR,
            unresolved_high_impact=False,
            event_name="No news data source wired up (not a verified clear window)",
        )

    def _fetch_liquidity_references(self) -> tuple[LiquidityReferenceEvidence, ...]:
        """Real PDH/PDL/PWH/PWL/PMH/PML from real daily candle history, with
        real sweep detection — not fixed price literals."""
        try:
            daily_candles = fetch_yahoo_candles(GOLD_TICKER, "1d", "6mo", self.timeout_seconds)
        except Exception as exc:
            logger.warning(f"Daily candle fetch for liquidity references failed: {exc}")
            return ()

        if len(daily_candles) < 4:
            return ()

        events: list[LiquidityReferenceEvidence] = []
        for high_level, low_level, key_fn in _PERIOD_BUCKETS:
            period = _previous_complete_period(daily_candles, key_fn)
            if period is None:
                continue
            high, low, last_index = period

            high_swing = SwingPoint(
                index=last_index,
                timestamp=daily_candles[last_index].timestamp,
                price=high,
                kind=SwingKind.HIGH,
            )
            low_swing = SwingPoint(
                index=last_index,
                timestamp=daily_candles[last_index].timestamp,
                price=low,
                kind=SwingKind.LOW,
            )
            high_sweep = detect_sweep_from_swing(daily_candles, high_swing)
            low_sweep = detect_sweep_from_swing(daily_candles, low_swing)

            events.append(
                LiquidityReferenceEvidence(
                    level=high_level,
                    price=round(high, 2),
                    swept=high_sweep.swept,
                    displacement_confirmed=high_sweep.displacement_confirmed,
                )
            )
            events.append(
                LiquidityReferenceEvidence(
                    level=low_level,
                    price=round(low, 2),
                    swept=low_sweep.swept,
                    displacement_confirmed=low_sweep.displacement_confirmed,
                )
            )

        return tuple(events)


def _previous_complete_period(
    candles: Sequence[Candle], key_fn: Callable[[datetime], object]
) -> tuple[float, float, int] | None:
    """The high/low and last candle index of the most recent *complete* period
    (day/week/month), i.e. the second-most-recent bucket — the most recent
    bucket may still be forming and isn't a complete period yet."""
    buckets: dict[object, list[int]] = {}
    for i, candle in enumerate(candles):
        buckets.setdefault(key_fn(candle.timestamp), []).append(i)

    ordered_keys = sorted(buckets.keys(), key=lambda k: buckets[k][0])
    if len(ordered_keys) < 2:
        return None

    indices = buckets[ordered_keys[-2]]
    highs = [candles[i].high for i in indices]
    lows = [candles[i].low for i in indices]
    return max(highs), min(lows), indices[-1]
