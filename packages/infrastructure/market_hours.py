"""Deterministic trading-session and weekend-closure classification from wall-clock time.

Session boundaries are the conventional UTC forex/gold session hours. This is a
clock-only classifier — it has no knowledge of exchange holidays.
"""

from __future__ import annotations

from datetime import datetime

from packages.domain import TradingSession

_ASIAN_OPEN_HOUR = 0
_ASIAN_CLOSE_HOUR = 8
_LONDON_OPEN_HOUR = 8
_LONDON_CLOSE_HOUR = 17
_NEW_YORK_OPEN_HOUR = 13
_NEW_YORK_CLOSE_HOUR = 22

_SATURDAY = 5
_SUNDAY = 6
_FRIDAY = 4
_WEEKEND_CLOSE_HOUR = 22
_WEEKEND_REOPEN_HOUR = 22


def is_weekend_closed(moment: datetime) -> bool:
    """XAUUSD/forex trading is closed roughly Friday 22:00 UTC to Sunday 22:00 UTC."""
    weekday = moment.weekday()
    if weekday == _SATURDAY:
        return True
    if weekday == _SUNDAY and moment.hour < _WEEKEND_REOPEN_HOUR:
        return True
    return weekday == _FRIDAY and moment.hour >= _WEEKEND_CLOSE_HOUR


def classify_session(moment: datetime) -> TradingSession:
    """Classify a UTC moment into a trading session, or CLOSED outside all sessions."""
    if is_weekend_closed(moment):
        return TradingSession.CLOSED

    hour = moment.hour
    in_london = _LONDON_OPEN_HOUR <= hour < _LONDON_CLOSE_HOUR
    in_new_york = _NEW_YORK_OPEN_HOUR <= hour < _NEW_YORK_CLOSE_HOUR
    in_asia = _ASIAN_OPEN_HOUR <= hour < _ASIAN_CLOSE_HOUR

    if in_london and in_new_york:
        return TradingSession.OVERLAP
    if in_london:
        return TradingSession.LONDON
    if in_new_york:
        return TradingSession.NEW_YORK
    if in_asia:
        return TradingSession.ASIAN
    return TradingSession.CLOSED
