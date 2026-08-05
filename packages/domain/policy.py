"""Named and versioned decision configuration."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Configurable hypotheses; changes require measurement and approval."""

    version: str = "v1-hypothesis-1"
    output_contract_version: str = "1.0.0"
    supported_symbol: str = "XAUUSD"
    maximum_age: timedelta = timedelta(hours=4)
    equilibrium_band: float = 0.02
    attention_threshold: float = 0.75
    structure_weight: float = 0.40
    location_weight: float = 0.30
    liquidity_weight: float = 0.30
    disclaimer: str = (
        "Decision support only. The trader owns entry, stop, target, risk, and execution."
    )

    def __post_init__(self) -> None:
        if not self.version.strip() or not self.output_contract_version.strip():
            raise ValueError("policy and output contract versions are required")
        if self.maximum_age <= timedelta(0):
            raise ValueError("maximum_age must be positive")
        if not 0 <= self.equilibrium_band < 0.5:
            raise ValueError("equilibrium_band must be between 0 and 0.5")
        if not 0 <= self.attention_threshold <= 1:
            raise ValueError("attention_threshold must be between 0 and 1")
        weights = (self.structure_weight, self.location_weight, self.liquidity_weight)
        if any(weight < 0 for weight in weights) or abs(sum(weights) - 1.0) > 1e-9:
            raise ValueError("evidence weights must be non-negative and sum to 1")
