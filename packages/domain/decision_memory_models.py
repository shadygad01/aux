"""Immutable decision identity, graph, version, outcome, and search contracts."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from .evidence_models import Recommendation
from .reasoning_models import MarketState
from .trading_models import HorizonBias


class DecisionOutcome(StrEnum):
    PENDING = "PENDING"
    WINNING = "WINNING"
    LOSING = "LOSING"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    REJECTED_WOULD_WIN = "REJECTED_WOULD_WIN"


class DecisionSearchKind(StrEnum):
    BUY_ABOVE_QUALITY = "BUY_ABOVE_QUALITY"
    FAILED_BUY_ABOVE_QUALITY = "FAILED_BUY_ABOVE_QUALITY"
    WAIT_LATER_BECAME_BUY = "WAIT_LATER_BECAME_BUY"
    REJECTED_WOULD_HAVE_WON = "REJECTED_WOULD_HAVE_WON"


@dataclass(frozen=True, slots=True)
class GraphNode:
    node_id: str
    kind: str
    label: str
    reference: str

    def __post_init__(self) -> None:
        if any(
            not value.strip() for value in (self.node_id, self.kind, self.label, self.reference)
        ):
            raise ValueError("graph nodes require identity, kind, label, and reference")


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source_node_id: str
    target_node_id: str
    relationship: str

    def __post_init__(self) -> None:
        if any(
            not value.strip()
            for value in (self.source_node_id, self.target_node_id, self.relationship)
        ):
            raise ValueError("graph edges require endpoints and relationship")


@dataclass(frozen=True, slots=True)
class DecisionGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]

    def __post_init__(self) -> None:
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("decision graph node IDs must be unique")
        for edge in self.edges:
            if edge.source_node_id not in node_ids or edge.target_node_id not in node_ids:
                raise ValueError("decision graph edges must reference existing nodes")


@dataclass(frozen=True, slots=True)
class DecisionSnapshot:
    market_state: MarketState
    macro_snapshot: str
    biases: tuple[HorizonBias, ...]
    trade_quality: int
    execution_state: Recommendation
    evidence_graph: DecisionGraph
    knowledge_object_ids: tuple[str, ...]
    reasoning_graph: DecisionGraph
    contradiction_graph: DecisionGraph
    confidence: int
    uncertainty: int
    supporting_evidence: tuple[str, ...]
    contradicting_evidence: tuple[str, ...]
    rejected_alternatives: tuple[str, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.trade_quality <= 100:
            raise ValueError("decision trade_quality must be between 0 and 100")
        if not 0 <= self.confidence <= 100 or not 0 <= self.uncertainty <= 100:
            raise ValueError("decision confidence and uncertainty must be between 0 and 100")
        if not self.macro_snapshot.strip() or not self.knowledge_object_ids:
            raise ValueError("decision requires macro snapshot and knowledge references")


@dataclass(frozen=True, slots=True)
class DecisionChange:
    field: str
    previous_value: str
    current_value: str


@dataclass(frozen=True, slots=True)
class DecisionVersion:
    decision_id: str
    version: int
    timestamp: datetime
    snapshot: DecisionSnapshot
    outcome: DecisionOutcome
    changes: tuple[DecisionChange, ...]
    change_reason: str
    previous_version: int | None
    contract_version: str = "1.0.0"

    def __post_init__(self) -> None:
        if self.timestamp.tzinfo is None:
            raise ValueError("decision version timestamp must be timezone-aware")
        if self.version <= 0 or not self.decision_id.strip() or not self.change_reason.strip():
            raise ValueError("decision version requires identity, positive version, and reason")
        if self.version == 1 and self.previous_version is not None:
            raise ValueError("initial decision version cannot have a previous version")
        if self.version > 1 and self.previous_version != self.version - 1:
            raise ValueError("decision versions must form a contiguous chain")


@dataclass(frozen=True, slots=True)
class DecisionSearch:
    kind: DecisionSearchKind
    minimum_trade_quality: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.minimum_trade_quality <= 100:
            raise ValueError("search minimum_trade_quality must be between 0 and 100")


@dataclass(frozen=True, slots=True)
class DecisionSearchResult:
    query: DecisionSearch
    decisions: tuple[DecisionVersion, ...]
    total: int
