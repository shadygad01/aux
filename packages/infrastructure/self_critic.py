"""Append-only self-critic repository for composition and tests."""

from packages.domain import DecisionCritique, ResearchTask


class InMemoryCritiqueArchive:
    def __init__(self) -> None:
        self.critiques: list[DecisionCritique] = []
        self.tasks: list[ResearchTask] = []

    def append_critique(self, critique: DecisionCritique) -> None:
        if any(item.critique_id == critique.critique_id for item in self.critiques):
            raise ValueError(f"critique already exists; critique_id={critique.critique_id}")
        self.critiques.append(critique)

    def append_task(self, task: ResearchTask) -> None:
        if any(item.task_id == task.task_id for item in self.tasks):
            raise ValueError(f"research task already exists; task_id={task.task_id}")
        self.tasks.append(task)
