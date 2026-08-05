"""Identify a reviewed market regime before any public analysis begins."""

from datetime import datetime, timedelta
from hashlib import sha256

from packages.domain import MarketRegime, MarketRegimeContext


class MarketRegimeIdentification:
    def __init__(self, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("market-regime policy version is required")
        self._policy_version = policy_version

    def identify(
        self,
        primary_regime: MarketRegime,
        active_regimes: tuple[MarketRegime, ...],
        identified_at: datetime,
        time_to_live: timedelta,
        confidence: int,
        rationale: str,
        evidence_references: tuple[str, ...],
        source: str,
    ) -> MarketRegimeContext:
        identity = "|".join(
            (
                identified_at.isoformat(),
                primary_regime.value,
                *(regime.value for regime in active_regimes),
                *evidence_references,
            )
        )
        return MarketRegimeContext(
            f"REGIME-{sha256(identity.encode('utf-8')).hexdigest()[:20]}",
            primary_regime,
            active_regimes,
            identified_at,
            time_to_live,
            confidence,
            rationale,
            evidence_references,
            source,
            self._policy_version,
        )
