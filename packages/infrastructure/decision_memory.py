"""SQLite decision identity and restart-safe immutable searchable archive."""

import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from typing import TypeAlias

from packages.domain import (
    AttentionBias,
    DecisionChange,
    DecisionGraph,
    DecisionOutcome,
    DecisionSearch,
    DecisionSearchKind,
    DecisionSnapshot,
    DecisionVersion,
    GraphEdge,
    GraphNode,
    HorizonBias,
    MarketState,
    RangeLocation,
    Recommendation,
    TradingHorizon,
)

Json: TypeAlias = None | bool | int | float | str | list["Json"] | dict[str, "Json"]


def _object(value: object, path: str) -> dict[str, Json]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"invalid decision archive object; path={path}")
    return {str(key): item for key, item in value.items()}


def _list(value: Json, path: str) -> list[Json]:
    if not isinstance(value, list):
        raise ValueError(f"invalid decision archive array; path={path}")
    return value


def _text(value: Json, path: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"invalid decision archive string; path={path}")
    return value


def _integer(value: Json, path: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"invalid decision archive integer; path={path}")
    return value


def _number(value: Json, path: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"invalid decision archive number; path={path}")
    return float(value)


def _required(value: dict[str, Json], key: str, path: str) -> Json:
    if key not in value:
        raise ValueError(f"missing decision archive field; path={path}.{key}")
    return value[key]


def _strings(value: Json, path: str) -> tuple[str, ...]:
    return tuple(_text(item, f"{path}[{index}]") for index, item in enumerate(_list(value, path)))


def _graph_to_json(graph: DecisionGraph) -> dict[str, Json]:
    return {
        "nodes": [
            {"node_id": n.node_id, "kind": n.kind, "label": n.label, "reference": n.reference}
            for n in graph.nodes
        ],
        "edges": [
            {
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "relationship": e.relationship,
            }
            for e in graph.edges
        ],
    }


def _graph_from_json(value: Json, path: str) -> DecisionGraph:
    payload = _object(value, path)
    nodes = []
    for index, item in enumerate(_list(_required(payload, "nodes", path), f"{path}.nodes")):
        node = _object(item, f"{path}.nodes[{index}]")
        nodes.append(
            GraphNode(
                _text(_required(node, "node_id", path), f"{path}.nodes[{index}].node_id"),
                _text(_required(node, "kind", path), f"{path}.nodes[{index}].kind"),
                _text(_required(node, "label", path), f"{path}.nodes[{index}].label"),
                _text(_required(node, "reference", path), f"{path}.nodes[{index}].reference"),
            )
        )
    edges = []
    for index, item in enumerate(_list(_required(payload, "edges", path), f"{path}.edges")):
        edge = _object(item, f"{path}.edges[{index}]")
        edges.append(
            GraphEdge(
                _text(_required(edge, "source_node_id", path), f"{path}.edges[{index}].source"),
                _text(_required(edge, "target_node_id", path), f"{path}.edges[{index}].target"),
                _text(_required(edge, "relationship", path), f"{path}.edges[{index}].relation"),
            )
        )
    return DecisionGraph(tuple(nodes), tuple(edges))


def _version_to_json(value: DecisionVersion) -> str:
    market = value.snapshot.market_state
    payload: dict[str, Json] = {
        "contract_version": value.contract_version,
        "decision_id": value.decision_id,
        "version": value.version,
        "timestamp": value.timestamp.isoformat(),
        "outcome": value.outcome.value,
        "change_reason": value.change_reason,
        "previous_version": value.previous_version,
        "changes": [
            {"field": c.field, "previous": c.previous_value, "current": c.current_value}
            for c in value.changes
        ],
        "snapshot": {
            "market_state": {
                "state_id": market.state_id,
                "symbol": market.symbol,
                "captured_at": market.captured_at.isoformat(),
                "ttl_seconds": market.time_to_live.total_seconds(),
                "price": market.price,
                "location": market.location.value,
                "session": market.session,
                "volatility_regime": market.volatility_regime,
                "summary": market.summary,
                "alternative_explanations": list(market.alternative_explanations),
                "source": market.source,
            },
            "macro_snapshot": value.snapshot.macro_snapshot,
            "biases": [
                {"horizon": b.horizon.value, "bias": b.bias.value, "reasoning": b.reasoning}
                for b in value.snapshot.biases
            ],
            "trade_quality": value.snapshot.trade_quality,
            "execution_state": value.snapshot.execution_state.value,
            "evidence_graph": _graph_to_json(value.snapshot.evidence_graph),
            "knowledge_object_ids": list(value.snapshot.knowledge_object_ids),
            "reasoning_graph": _graph_to_json(value.snapshot.reasoning_graph),
            "contradiction_graph": _graph_to_json(value.snapshot.contradiction_graph),
            "confidence": value.snapshot.confidence,
            "uncertainty": value.snapshot.uncertainty,
            "supporting_evidence": list(value.snapshot.supporting_evidence),
            "contradicting_evidence": list(value.snapshot.contradicting_evidence),
            "rejected_alternatives": list(value.snapshot.rejected_alternatives),
        },
    }
    return json.dumps(payload, separators=(",", ":"))


def _version_from_json(raw: str) -> DecisionVersion:
    root = _object(json.loads(raw), "$")
    snapshot = _object(_required(root, "snapshot", "$"), "$.snapshot")
    market = _object(_required(snapshot, "market_state", "$.snapshot"), "$.snapshot.market_state")
    biases = []
    for item in _list(_required(snapshot, "biases", "$.snapshot"), "$.snapshot.biases"):
        bias = _object(item, "$.snapshot.biases[]")
        biases.append(
            HorizonBias(
                TradingHorizon(_text(_required(bias, "horizon", "$"), "$.bias.horizon")),
                AttentionBias(_text(_required(bias, "bias", "$"), "$.bias.bias")),
                _text(_required(bias, "reasoning", "$"), "$.bias.reasoning"),
            )
        )
    changes = []
    for item in _list(_required(root, "changes", "$"), "$.changes"):
        change = _object(item, "$.changes[]")
        changes.append(
            DecisionChange(
                _text(_required(change, "field", "$"), "$.changes[].field"),
                _text(_required(change, "previous", "$"), "$.changes[].previous"),
                _text(_required(change, "current", "$"), "$.changes[].current"),
            )
        )
    previous = _required(root, "previous_version", "$")
    if previous is not None and (isinstance(previous, bool) or not isinstance(previous, int)):
        raise ValueError("invalid previous decision version")
    market_state = MarketState(
        _text(_required(market, "state_id", "$"), "$.market.state_id"),
        _text(_required(market, "symbol", "$"), "$.market.symbol"),
        datetime.fromisoformat(_text(_required(market, "captured_at", "$"), "$.market.captured")),
        timedelta(seconds=_number(_required(market, "ttl_seconds", "$"), "$.market.ttl")),
        _number(_required(market, "price", "$"), "$.market.price"),
        RangeLocation(_text(_required(market, "location", "$"), "$.market.location")),
        _text(_required(market, "session", "$"), "$.market.session"),
        _text(_required(market, "volatility_regime", "$"), "$.market.volatility"),
        _text(_required(market, "summary", "$"), "$.market.summary"),
        _strings(_required(market, "alternative_explanations", "$"), "$.market.alternatives"),
        _text(_required(market, "source", "$"), "$.market.source"),
    )
    decision_snapshot = DecisionSnapshot(
        market_state,
        _text(_required(snapshot, "macro_snapshot", "$"), "$.snapshot.macro"),
        tuple(biases),
        _integer(_required(snapshot, "trade_quality", "$"), "$.snapshot.quality"),
        Recommendation(_text(_required(snapshot, "execution_state", "$"), "$.snapshot.state")),
        _graph_from_json(_required(snapshot, "evidence_graph", "$"), "$.snapshot.evidence_graph"),
        _strings(_required(snapshot, "knowledge_object_ids", "$"), "$.snapshot.knowledge"),
        _graph_from_json(_required(snapshot, "reasoning_graph", "$"), "$.snapshot.reasoning_graph"),
        _graph_from_json(
            _required(snapshot, "contradiction_graph", "$"), "$.snapshot.contradiction_graph"
        ),
        _integer(_required(snapshot, "confidence", "$"), "$.snapshot.confidence"),
        _integer(_required(snapshot, "uncertainty", "$"), "$.snapshot.uncertainty"),
        _strings(_required(snapshot, "supporting_evidence", "$"), "$.snapshot.supporting"),
        _strings(_required(snapshot, "contradicting_evidence", "$"), "$.snapshot.contradicting"),
        _strings(_required(snapshot, "rejected_alternatives", "$"), "$.snapshot.rejected"),
    )
    return DecisionVersion(
        _text(_required(root, "decision_id", "$"), "$.decision_id"),
        _integer(_required(root, "version", "$"), "$.version"),
        datetime.fromisoformat(_text(_required(root, "timestamp", "$"), "$.timestamp")),
        decision_snapshot,
        DecisionOutcome(_text(_required(root, "outcome", "$"), "$.outcome")),
        tuple(changes),
        _text(_required(root, "change_reason", "$"), "$.change_reason"),
        previous,
        _text(_required(root, "contract_version", "$"), "$.contract_version"),
    )


class SqliteDecisionMemory:
    def __init__(self, path: Path) -> None:
        self._path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection, connection:
            connection.executescript("""
            CREATE TABLE IF NOT EXISTS decision_sequences(
                day TEXT PRIMARY KEY, value INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS decision_versions(
                decision_id TEXT NOT NULL, version INTEGER NOT NULL, timestamp TEXT NOT NULL,
                recommendation TEXT NOT NULL, trade_quality INTEGER NOT NULL, outcome TEXT NOT NULL,
                payload TEXT NOT NULL, PRIMARY KEY(decision_id, version));
            CREATE INDEX IF NOT EXISTS decision_search_idx
            ON decision_versions(recommendation, trade_quality, outcome, timestamp);
            """)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def next_id(self, timestamp: datetime) -> str:
        if timestamp.tzinfo is None:
            raise ValueError("decision ID timestamp must be timezone-aware")
        day = timestamp.strftime("%Y%m%d")
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT value FROM decision_sequences WHERE day=?", (day,)
            ).fetchone()
            sequence = 1 if row is None else int(row[0]) + 1
            connection.execute(
                "INSERT INTO decision_sequences VALUES(?,?) "
                "ON CONFLICT(day) DO UPDATE SET value=excluded.value",
                (day, sequence),
            )
        return f"DECISION-{day}-{sequence:06d}"

    def append(self, decision: DecisionVersion) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT MAX(version) FROM decision_versions WHERE decision_id=?",
                (decision.decision_id,),
            ).fetchone()
            latest = None if row is None or row[0] is None else int(row[0])
            expected = 1 if latest is None else latest + 1
            if decision.version != expected:
                raise ValueError(f"non-contiguous decision version; expected={expected}")
            connection.execute(
                "INSERT INTO decision_versions VALUES(?,?,?,?,?,?,?)",
                (
                    decision.decision_id,
                    decision.version,
                    decision.timestamp.isoformat(),
                    decision.snapshot.execution_state.value,
                    decision.snapshot.trade_quality,
                    decision.outcome.value,
                    _version_to_json(decision),
                ),
            )

    def latest(self, decision_id: str) -> DecisionVersion | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload FROM decision_versions WHERE decision_id=? "
                "ORDER BY version DESC LIMIT 1",
                (decision_id,),
            ).fetchone()
        return None if row is None else _version_from_json(str(row[0]))

    def search(self, query: DecisionSearch) -> tuple[DecisionVersion, ...]:
        if query.kind is DecisionSearchKind.BUY_ABOVE_QUALITY:
            sql = (
                "SELECT payload FROM decision_versions WHERE recommendation=? AND trade_quality>=?"
            )
            parameters: tuple[object, ...] = (
                Recommendation.BUY_SETUPS_ONLY.value,
                query.minimum_trade_quality,
            )
        elif query.kind is DecisionSearchKind.FAILED_BUY_ABOVE_QUALITY:
            sql = (
                "SELECT payload FROM decision_versions WHERE recommendation=? AND trade_quality>=? "
                "AND outcome IN (?,?)"
            )
            parameters = (
                Recommendation.BUY_SETUPS_ONLY.value,
                query.minimum_trade_quality,
                DecisionOutcome.LOSING.value,
                DecisionOutcome.FALSE_POSITIVE.value,
            )
        elif query.kind is DecisionSearchKind.WAIT_LATER_BECAME_BUY:
            sql = (
                "SELECT waiting.payload FROM decision_versions waiting "
                "WHERE waiting.recommendation=? AND EXISTS "
                "(SELECT 1 FROM decision_versions later "
                "WHERE later.decision_id=waiting.decision_id "
                "AND later.version>waiting.version AND later.recommendation=?)"
            )
            parameters = (Recommendation.WAIT.value, Recommendation.BUY_SETUPS_ONLY.value)
        else:
            sql = "SELECT payload FROM decision_versions WHERE outcome=?"
            parameters = (DecisionOutcome.REJECTED_WOULD_WIN.value,)
        with closing(self._connect()) as connection:
            rows = connection.execute(f"{sql} ORDER BY timestamp", parameters).fetchall()
        return tuple(_version_from_json(str(row[0])) for row in rows)
