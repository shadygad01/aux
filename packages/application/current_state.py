"""Assemble one deterministic Current Market State at each reviewed update."""

from datetime import datetime, timedelta
from hashlib import sha256

from packages.domain import CurrentMarketState, HorizonBias, MarketRegimeContext


class CurrentMarketStateAssembly:
    def __init__(self, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("current-state policy version is required")
        self._policy_version = policy_version

    def assemble(
        self,
        symbol: str,
        captured_at: datetime,
        time_to_live: timedelta,
        regime: MarketRegimeContext,
        macro_state: str,
        biases: tuple[HorizonBias, ...],
        volatility_state: str,
        liquidity_state: str,
        momentum_state: str,
        news_state: str,
        confidence: int,
        uncertainty: int,
        evidence_references: tuple[str, ...],
        source: str,
    ) -> CurrentMarketState:
        identity = "|".join(
            (
                symbol.upper(),
                captured_at.isoformat(),
                regime.regime_id,
                macro_state,
                *(repr(bias) for bias in biases),
                volatility_state,
                liquidity_state,
                momentum_state,
                news_state,
                *evidence_references,
            )
        )
        return CurrentMarketState(
            f"STATE-{sha256(identity.encode('utf-8')).hexdigest()[:20]}",
            symbol.upper(),
            captured_at,
            time_to_live,
            regime,
            macro_state,
            biases,
            volatility_state,
            liquidity_state,
            momentum_state,
            news_state,
            confidence,
            uncertainty,
            evidence_references,
            source,
            self._policy_version,
        )
