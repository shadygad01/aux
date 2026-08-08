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
            obs, status = self._market_collector.fetch_live_observation()
            last_close = obs.dealing_range.current_price if obs.dealing_range is not None else None
            records.append(
                RawDatum(
                    field="last_close",
                    value=str(last_close) if last_close is not None else "unavailable",
                    observed_at=obs.observed_at,
                    source=obs.source,
                )
            )
            records.append(
                RawDatum(
                    field="collection_status",
                    value=status,
                    observed_at=obs.observed_at,
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
            macro_context = self._macro_collector.acquire_macro_context(now)
            records.append(
                RawDatum(
                    field="dxy_trend",
                    value=macro_context.dollar_strength.value,
                    observed_at=macro_context.observed_at,
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
