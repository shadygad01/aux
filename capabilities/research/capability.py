"""Research capability: calculate cohorts and propose non-deploying improvements."""

from datetime import datetime
from typing import Protocol

from capabilities.contracts import (
    CapabilityHealth,
    CapabilityLog,
    CapabilityMetric,
    CapabilityTelemetry,
    HealthState,
    LogLevel,
)
from packages.domain import (
    DiscoveredPattern,
    EdgeStatistics,
    LearningRecord,
    PatternStatus,
    PatternValidation,
    ResearchProposal,
)


class ResearchPort(Protocol):
    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        evidence_combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics: ...


class ResearchProposalPort(Protocol):
    def propose(
        self,
        proposal_id: str,
        question: str,
        hypothesis: str,
        method: str,
        evidence_references: tuple[str, ...],
        statistics: EdgeStatistics,
        risk: str,
        expected_gain: str,
        migration_impact: str,
        proposed_at: datetime,
    ) -> ResearchProposal: ...


class PatternDiscoveryPort(Protocol):
    def discover(self, pattern: DiscoveredPattern) -> DiscoveredPattern: ...

    def promote(
        self,
        pattern_id: str,
        target: PatternStatus,
        validation: PatternValidation,
        reviewed_at: datetime,
        reason: str,
    ) -> DiscoveredPattern: ...


class ResearchCapability:
    name = "research"

    def __init__(
        self,
        research_service: ResearchPort,
        telemetry: CapabilityTelemetry,
        pattern_discovery: PatternDiscoveryPort | None = None,
        proposal_service: ResearchProposalPort | None = None,
    ) -> None:
        self._research_service = research_service
        self._telemetry = telemetry
        self._pattern_discovery = pattern_discovery
        self._proposal_service = proposal_service

    def discover_pattern(self, pattern: DiscoveredPattern) -> DiscoveredPattern:
        if self._pattern_discovery is None:
            raise RuntimeError("pattern discovery is not configured")
        discovered = self._pattern_discovery.discover(pattern)
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "pattern_discovered",
                (("pattern_id", pattern.pattern_id),),
            )
        )
        return discovered

    def promote_pattern(
        self,
        pattern_id: str,
        target: PatternStatus,
        validation: PatternValidation,
        reviewed_at: datetime,
        reason: str,
    ) -> DiscoveredPattern:
        if self._pattern_discovery is None:
            raise RuntimeError("pattern discovery is not configured")
        promoted = self._pattern_discovery.promote(
            pattern_id, target, validation, reviewed_at, reason
        )
        self._telemetry.metric(CapabilityMetric(self.name, "pattern_promotions", 1, "patterns"))
        return promoted

    def evaluate_edge(
        self,
        records: tuple[LearningRecord, ...],
        combination: tuple[str, ...],
        evidence_quality: float,
        data_quality: float,
    ) -> EdgeStatistics:
        statistics = self._research_service.evaluate_edge(
            records, combination, evidence_quality, data_quality
        )
        self._telemetry.metric(
            CapabilityMetric(self.name, "edge_sample_size", statistics.sample_size, "records")
        )
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "edge_evaluated",
                (("sample_size", str(statistics.sample_size)),),
            )
        )
        return statistics

    def propose(
        self,
        proposal_id: str,
        question: str,
        hypothesis: str,
        method: str,
        statistics: EdgeStatistics,
        evidence_references: tuple[str, ...],
        risk: str,
        expected_gain: str,
        migration_impact: str,
        proposed_at: datetime,
    ) -> ResearchProposal:
        if self._proposal_service is None:
            raise RuntimeError("research proposal governance is not configured")
        proposal = self._proposal_service.propose(
            proposal_id,
            question,
            hypothesis,
            method,
            evidence_references,
            statistics,
            risk,
            expected_gain,
            migration_impact,
            proposed_at,
        )
        self._telemetry.log(
            CapabilityLog(
                self.name,
                LogLevel.INFO,
                "research_proposed",
                (("proposal_id", proposal_id),),
            )
        )
        return proposal

    def health(self, checked_at: datetime) -> CapabilityHealth:
        return CapabilityHealth(
            self.name, HealthState.HEALTHY, checked_at, "research service configured"
        )
