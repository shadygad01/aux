"""Discover and govern patterns without granting research direct production access."""

from dataclasses import replace
from datetime import datetime
from typing import Protocol

from packages.domain import DiscoveredPattern, PatternStatus, PatternValidation


class PatternArchive(Protocol):
    def append(self, pattern: DiscoveredPattern) -> None: ...

    def latest(self, pattern_id: str) -> DiscoveredPattern | None: ...


class PatternDiscovery:
    def __init__(self, archive: PatternArchive) -> None:
        self._archive = archive

    def discover(self, pattern: DiscoveredPattern) -> DiscoveredPattern:
        if pattern.status is not PatternStatus.EXPERIMENTAL or pattern.revision != 1:
            raise ValueError("newly discovered patterns must begin as experimental revision one")
        if self._archive.latest(pattern.pattern_id) is not None:
            raise ValueError(f"pattern already exists; pattern_id={pattern.pattern_id}")
        self._archive.append(pattern)
        return pattern

    def promote(
        self,
        pattern_id: str,
        target: PatternStatus,
        validation: PatternValidation,
        reviewed_at: datetime,
        reason: str,
    ) -> DiscoveredPattern:
        current = self._archive.latest(pattern_id)
        if current is None:
            raise ValueError(f"unknown pattern; pattern_id={pattern_id}")
        allowed = {
            PatternStatus.EXPERIMENTAL: PatternStatus.OBSERVED,
            PatternStatus.OBSERVED: PatternStatus.VALIDATED,
            PatternStatus.VALIDATED: PatternStatus.INSTITUTIONAL_PATTERN,
        }
        if target is PatternStatus.DEPRECATED:
            pass
        elif allowed.get(current.status) is not target:
            raise ValueError(f"invalid pattern transition; {current.status.value}->{target.value}")
        self._validate_gate(target, validation)
        revised = replace(
            current,
            revision=current.revision + 1,
            status=target,
            validation=validation,
            reviewed_at=reviewed_at,
            change_reason=reason,
        )
        self._archive.append(revised)
        return revised

    @staticmethod
    def _validate_gate(target: PatternStatus, validation: PatternValidation) -> None:
        if target in {
            PatternStatus.OBSERVED,
            PatternStatus.VALIDATED,
            PatternStatus.INSTITUTIONAL_PATTERN,
        } and not (validation.statistically_significant and validation.repeatability_runs >= 2):
            raise ValueError("observed patterns require significance and repeatability")
        if target in {PatternStatus.VALIDATED, PatternStatus.INSTITUTIONAL_PATTERN} and not (
            validation.backtested
        ):
            raise ValueError("validated patterns require backtesting")
        if target is PatternStatus.INSTITUTIONAL_PATTERN and not (
            validation.forward_tested and validation.documented
        ):
            raise ValueError("institutional patterns require forward testing and documentation")
