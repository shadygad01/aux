"""Append-only comprehension audit for composition and tests."""

from packages.domain import ReasoningComprehensionReview


class InMemoryComprehensionAudit:
    def __init__(self) -> None:
        self.reviews: list[ReasoningComprehensionReview] = []

    def append(self, review: ReasoningComprehensionReview) -> None:
        if any(item.review_id == review.review_id for item in self.reviews):
            raise ValueError(f"reasoning already reviewed; reasoning_id={review.reasoning_id}")
        self.reviews.append(review)
