"""Shared coercion helpers for domain model from_dict methods.

These operate on already-serialized internal data (round-tripped through
to_dict, typically reloaded from SQLite/JSON storage) — not external input,
so no elaborate path-tracking validation like json_contracts.py's boundary
adapters. Just type-safe coercion that satisfies strict mypy without
silently accepting the wrong type.
"""

from __future__ import annotations


def to_float(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError(f"cannot convert {value!r} to float")
    return float(value)


def to_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        raise TypeError(f"cannot convert {value!r} to int")
    return int(value)
