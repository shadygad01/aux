"""Append-only sprint quality audit for composition and tests."""

from packages.domain import InstitutionalQualityCompletion


class InMemoryQualityAudit:
    def __init__(self) -> None:
        self.completions: list[InstitutionalQualityCompletion] = []

    def append(self, completion: InstitutionalQualityCompletion) -> None:
        if any(item.sprint_id == completion.sprint_id for item in self.completions):
            raise ValueError(f"sprint already completed; sprint_id={completion.sprint_id}")
        self.completions.append(completion)
