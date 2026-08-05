"""Versioned and named Version 3 evidence policy hypotheses."""

from dataclasses import dataclass

from .evidence_models import EvidenceKind


@dataclass(frozen=True, slots=True)
class EvidencePolicy:
    version: str = "evidence-v1-hypothesis-1"
    contract_version: str = "3.0.0"
    minimum_reliable_weight: float = 0.05
    minimum_directional_weight: float = 0.25
    minimum_directional_confidence: int = 60
    minimum_trade_quality: int = 75
    weight_precision: int = 6
    required_execution_kinds: tuple[EvidenceKind, ...] = (
        EvidenceKind.MACRO,
        EvidenceKind.MARKET_BIAS,
        EvidenceKind.LOCATION,
        EvidenceKind.LIQUIDITY_SWEEP,
        EvidenceKind.MACD,
        EvidenceKind.REVERSAL_CANDLE,
    )

    def __post_init__(self) -> None:
        for name, value in (
            ("minimum_reliable_weight", self.minimum_reliable_weight),
            ("minimum_directional_weight", self.minimum_directional_weight),
        ):
            if not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        for name, value in (
            ("minimum_directional_confidence", self.minimum_directional_confidence),
            ("minimum_trade_quality", self.minimum_trade_quality),
        ):
            if not 0 <= value <= 100:
                raise ValueError(f"{name} must be between 0 and 100")
        if self.weight_precision < 0:
            raise ValueError("weight_precision must be non-negative")
