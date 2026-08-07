"""Public infrastructure adapters."""

from .capability_telemetry import InMemoryCapabilityTelemetry
from .comprehension import InMemoryComprehensionAudit
from .decision_memory import SqliteDecisionMemory
from .evidence_adapters import JsonLinesEvidenceDecisionAudit, evidence_decision_to_json
from .governance import InMemoryGovernanceAudit
from .institutional_memory import SqliteInstitutionalMemory
from .json_contracts import decision_to_json, observation_from_json
from .knowledge_adapters import (
    InMemoryKnowledgeRepository,
    JsonLinesKnowledgeRepository,
    event_to_json,
    knowledge_to_json,
    pattern_to_json,
    source_to_json,
)
from .learning_adapters import JsonLinesLearningRepository, learning_record_to_json
from .logging_adapter import JsonDecisionLogger
from .pattern_discovery import InMemoryPatternArchive
from .quality_assurance import InMemoryQualityAudit
from .reasoning_adapters import JsonLinesReasoningAudit, reasoning_decision_to_json
from .research_governance import InMemoryResearchProposalArchive
from .self_critic import InMemoryCritiqueArchive
from .trading_adapters import (
    JsonLinesOpportunityRepository,
    JsonTradingDecisionLogger,
    trading_decision_to_json,
    trading_observation_from_json,
)

__all__ = [
    "JsonDecisionLogger",
    "InMemoryCapabilityTelemetry",
    "SqliteDecisionMemory",
    "JsonLinesOpportunityRepository",
    "JsonLinesEvidenceDecisionAudit",
    "JsonLinesLearningRepository",
    "InMemoryKnowledgeRepository",
    "JsonLinesKnowledgeRepository",
    "JsonLinesReasoningAudit",
    "JsonTradingDecisionLogger",
    "decision_to_json",
    "observation_from_json",
    "trading_decision_to_json",
    "trading_observation_from_json",
    "evidence_decision_to_json",
    "learning_record_to_json",
    "event_to_json",
    "knowledge_to_json",
    "pattern_to_json",
    "source_to_json",
    "reasoning_decision_to_json",
    "InMemoryPatternArchive",
    "InMemoryCritiqueArchive",
    "InMemoryGovernanceAudit",
    "InMemoryResearchProposalArchive",
    "InMemoryQualityAudit",
    "SqliteInstitutionalMemory",
    "InMemoryComprehensionAudit",
]
