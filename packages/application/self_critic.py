"""Challenge every decision and turn every failure into research work."""

from datetime import datetime
from typing import Protocol

from packages.domain import (
    CritiqueAssessment,
    CritiqueStage,
    DecisionCritique,
    DecisionOutcome,
    DecisionVersion,
    ResearchTask,
)


class CritiqueArchive(Protocol):
    def append_critique(self, critique: DecisionCritique) -> None: ...

    def append_task(self, task: ResearchTask) -> None: ...


class SelfCritic:
    def __init__(self, archive: CritiqueArchive, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("self-critic policy version is required")
        self._archive = archive
        self._policy_version = policy_version

    def challenge(
        self,
        decision: DecisionVersion,
        stage: CritiqueStage,
        assessment: CritiqueAssessment,
        challenged_at: datetime,
    ) -> tuple[DecisionCritique, tuple[ResearchTask, ...]]:
        suffix = f"{decision.version:04d}-{stage.value}"
        critique = DecisionCritique(
            f"CRITIQUE-{decision.decision_id}-{suffix}",
            decision.decision_id,
            decision.version,
            stage,
            decision.outcome,
            assessment,
            challenged_at,
            self._policy_version,
        )
        self._archive.append_critique(critique)
        tasks = self._research_tasks(critique)
        for task in tasks:
            self._archive.append_task(task)
        return critique, tasks

    @staticmethod
    def _research_tasks(critique: DecisionCritique) -> tuple[ResearchTask, ...]:
        if critique.outcome not in {DecisionOutcome.LOSING, DecisionOutcome.FALSE_POSITIVE}:
            return ()
        task = ResearchTask(
            f"RESEARCH-{critique.critique_id}",
            critique.decision_id,
            critique.critique_id,
            "Determine why the failed decision passed its evidence and uncertainty gates.",
            critique.assessment.evidence_references,
            critique.challenged_at,
        )
        return (task,)
