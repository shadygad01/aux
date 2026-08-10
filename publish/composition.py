"""Composition root for the decision-free market-data publisher."""

from __future__ import annotations

from packages.infrastructure.live_collector import LiveMarketCollector
from packages.infrastructure.macro_collectors import MacroCollector

MACRO_COLLECTOR_TIMEOUT_SECONDS = 2
_LIVE_MARKET_COLLECTOR = LiveMarketCollector()


def build_live_market_collector() -> LiveMarketCollector:
    """Return the run-scoped collector with one synchronized snapshot cache."""
    return _LIVE_MARKET_COLLECTOR


def build_macro_collector() -> MacroCollector:
    """Return the fail-closed DXY/US10Y collector."""
    return MacroCollector(timeout_seconds=MACRO_COLLECTOR_TIMEOUT_SECONDS)
