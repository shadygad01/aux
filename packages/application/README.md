# Application Package

## Responsibility

Own independent decision-engine use cases and their external-effect ports. It coordinates domain objects but does not parse JSON, use files, or select logging technology.

## Architecture notes

The engine receives policy and logger dependencies through constructor injection. It communicates with infrastructure only through `DecisionLogger`.

## Public interfaces

- `DecisionEngine.evaluate(MarketObservation, datetime) -> Decision` is a Version 1 Compatibility Adapter path.
- `TradingOpportunityEngine.evaluate(TradingObservation, datetime) -> TradingDecision` is a Compatibility Adapter candidate pending canonical Market Thesis migration.
- `EvidenceDecisionEngine.evaluate(tuple[Evidence, ...], datetime) -> EvidenceDecision` for expiring evidence and the four-output constitution.
- `LearningEngine` stores evaluations, produces research artifacts, calculates cohorts, and emits approval-only recommendations. It exposes no production deployment method.
- `InstitutionalKnowledgeBase` governs sources, append-only knowledge revisions, review expiry, historical events, patterns, and structured evidence-backed questions.
- `InstitutionalReasoningEngine` composes the evidence engine with current knowledge, market state, historical similarities, research, and learning proposals through the mandatory nine-stage chain.
- Logger and append-only repository protocols in `ports.py`.

## Dependencies

Domain package and Python standard library only. No third-party dependency is justified. Owner: decision intelligence team.
