"""Production CollectionPort adapter wrapping LiveMarketCollector and MacroCollector."""

from datetime import UTC, datetime

from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector

from .capability import CollectionBatch, CollectionPort, CollectionRequest, RawDatum


class LiveMarketCollectionAdapter(CollectionPort):
    """Adapter bridging LiveMarketCollector and MacroCollector to CollectionPort."""

    def __init__(
        self,
        market_collector: LiveMarketCollector | None = None,
        macro_collector: MacroCollector | None = None,
    ) -> None:
        self._market_collector = market_collector or LiveMarketCollector()
        self._macro_collector = macro_collector or MacroCollector()

    def collect(self, request: CollectionRequest) -> CollectionBatch:
        now = datetime.now(UTC)
        records: list[RawDatum] = []

        try:
            obs = self._market_collector.fetch_latest_observation(
                symbol=request.symbol,
                timeframe="H1",
            )
            records.append(
                RawDatum(
                    field="last_close",
                    value=str(obs.candles[-1].close if obs.candles else 0.0),
                    observed_at=obs.observation_time,
                    source=obs.source,
                )
            )
            records.append(
                RawDatum(
                    field="candle_count",
                    value=str(len(obs.candles)),
                    observed_at=obs.observation_time,
                    source=obs.source,
                )
            )
        except Exception:
            records.append(
                RawDatum(
                    field="market_data",
                    value="unavailable",
                    observed_at=now,
                    source="live-api:fallback",
                )
            )

        try:
            macro_assessment = self._macro_collector.collect()
            records.append(
                RawDatum(
                    field="dxy_trend",
                    value=macro_assessment.dxy.trend.name if macro_assessment.dxy else "UNKNOWN",
                    observed_at=now,
                    source="live-api:macro",
                )
            )
        except Exception:
            records.append(
                RawDatum(
                    field="macro_data",
                    value="unavailable",
                    observed_at=now,
                    source="live-api:macro-fallback",
                )
            )

        return CollectionBatch(
            request=request,
            records=tuple(records),
            collected_at=now,
        )
