"""Append-only in-memory pattern archive for composition and tests."""

from packages.domain import DiscoveredPattern


class InMemoryPatternArchive:
    def __init__(self) -> None:
        self._patterns: list[DiscoveredPattern] = []

    def append(self, pattern: DiscoveredPattern) -> None:
        current = self.latest(pattern.pattern_id)
        expected = 1 if current is None else current.revision + 1
        if pattern.revision != expected:
            raise ValueError(f"non-contiguous pattern revision; expected={expected}")
        self._patterns.append(pattern)

    def latest(self, pattern_id: str) -> DiscoveredPattern | None:
        matches = [item for item in self._patterns if item.pattern_id == pattern_id]
        return max(matches, key=lambda item: item.revision) if matches else None

    def history(self, pattern_id: str) -> tuple[DiscoveredPattern, ...]:
        return tuple(item for item in self._patterns if item.pattern_id == pattern_id)
