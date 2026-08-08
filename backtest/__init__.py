"""Standalone offline backtest tool for the live canonical decision path.

Replays real historical XAUUSD H1 candles through the unmodified
production DecisionEngine/DecisionPolicy to measure real win-rate/R:R
statistics -- the actual evidence the hypotheses in
docs/hypothesis-register.md (H-001, H-002, H-003, H-004, H-005, H-006,
H-007, H-024, H-025) require before they can move past UNVALIDATED.

Deliberately outside packages/ and unwired from publish/ or capabilities/:
this is an offline research tool, not a production consumer. See
backtest/README.md for how to run it and what it does and does not prove.
"""

from __future__ import annotations
