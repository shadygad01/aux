"""Named trading-constitution configuration hypotheses."""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class TradingPolicy:
    version: str = "trading-v1-hypothesis-1"
    contract_version: str = "2.0.0"
    supported_symbol: str = "XAUUSD"
    maximum_age: timedelta = timedelta(hours=4)
    equilibrium_band: float = 0.02
    minimum_trade_quality: int = 75
    macro_points: int = 15
    execution_bias_points: int = 15
    cross_horizon_alignment_points: int = 5
    location_points: int = 15
    liquidity_sweep_points: int = 10
    nearby_liquidity_points: int = 5
    macd_points: int = 10
    reversal_candle_points: int = 15
    optional_smc_points: int = 10
    macro_contradiction_penalty_points: int = 5
    news_confidence_penalty_points: int = 10
    buy_liquidity_levels: tuple[str, ...] = ("PDL", "PWL", "PML")
    sell_liquidity_levels: tuple[str, ...] = ("PDH", "PWH", "PMH")

    def __post_init__(self) -> None:
        points = (
            self.macro_points,
            self.execution_bias_points,
            self.cross_horizon_alignment_points,
            self.location_points,
            self.liquidity_sweep_points,
            self.nearby_liquidity_points,
            self.macd_points,
            self.reversal_candle_points,
            self.optional_smc_points,
        )
        if sum(points) != 100 or any(point < 0 for point in points):
            raise ValueError("trade-quality points must be non-negative and total 100")
        if not 0 <= self.minimum_trade_quality <= 100:
            raise ValueError("minimum_trade_quality must be between 0 and 100")
        if not 0 <= self.equilibrium_band < 0.5:
            raise ValueError("equilibrium_band must be between 0 and 0.5")
        if self.macro_contradiction_penalty_points < 0 or self.news_confidence_penalty_points < 0:
            raise ValueError("contradiction penalties must be non-negative")
