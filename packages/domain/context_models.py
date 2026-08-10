"""Clock-derived market-session labels; no inferred market context."""

from enum import StrEnum


class TradingSession(StrEnum):
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    ASIAN = "ASIAN"
    OVERLAP = "OVERLAP"
    CLOSED = "CLOSED"
