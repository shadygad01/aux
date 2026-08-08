"""Production Normalization capability adapter with default domain unit mappings."""

from capabilities.collection import CollectionBatch

from .capability import NormalizationCapability, NormalizedDatum


class CanonicalNormalizationAdapter:
    """Production wrapper for NormalizationCapability with pre-configured domain units."""

    DEFAULT_FIELD_UNITS = {
        "last_close": "USD_PER_OUNCE",
        "candle_count": "COUNT",
        "dxy_trend": "INDEX_TREND",
        "price": "USD_PER_OUNCE",
        "dxy": "INDEX",
        "yields": "PERCENT",
    }

    def __init__(self, capability: NormalizationCapability) -> None:
        self._capability = capability

    def normalize(self, batch: CollectionBatch) -> tuple[NormalizedDatum, ...]:
        return self._capability.normalize(batch)
