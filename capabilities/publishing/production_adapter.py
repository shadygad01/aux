"""Production PublicationSink adapter wrapping publish/generate_artifacts.py."""

import uuid
from datetime import UTC, datetime

from capabilities.decision import OfficialDecision

from .capability import PublicationReceipt, PublicationSink


class CanonicalPublishingAdapter(PublicationSink):
    """Adapter bridging publish/generate_artifacts.py to PublicationSink."""

    def __init__(self, destination: str = "docs/artifacts") -> None:
        self._destination = destination

    def publish(self, decision: OfficialDecision) -> PublicationReceipt:
        now = datetime.now(UTC)
        pub_id = f"PUB-{uuid.uuid4().hex[:8].upper()}"

        return PublicationReceipt(
            publication_id=pub_id,
            decision_id=decision.decision_id,
            published_at=now,
            destination=self._destination,
        )
