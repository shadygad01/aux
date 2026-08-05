# Canonical Concept Ownership

Status: **GOVERNING MAP**. “Target” entries are blockers, not permission to create parallel models.

## Concept ownership matrix

| Concept | Capability owner | Canonical domain object | Current disposition |
|---|---|---|---|
| Market Context | Context | `MarketContext` | Canonical environmental wrapper (session, news, macro, volatility, liquidity, flags) |
| Market Thesis | Decision | `MarketThesis` target | `OfficialDecision` is precursor; rename/move required |
| Evidence | Evidence | `Evidence` | Canonical |
| Knowledge Object | Knowledge | `KnowledgeObject` | Canonical |
| Research Finding | Research | `ResearchFinding` target | `ResearchArtifact` and `ResearchProposal` need separation/migration |
| Learning Recommendation | Learning | `LearningRecommendation` | Canonical, non-production |
| Trade Quality | Decision | `TradeQuality` target value object | Raw integers and three calculation paths are P0 debt |
| Bias | Reasoning | `AttentionBias` | Canonical attention vocabulary; `HorizonBias` is projection |
| Market State | Reasoning | `CurrentMarketState` | Canonical |
| Market Regime | Reasoning | `MarketRegimeContext` | Canonical part of Market State |
| Decision Memory | Decision | `DecisionVersion` audit record | Canonical immutable audit representation |
| Lineage | Evidence | `LineageGraph` target | Existing graphs/traces/reference tuples require migration |
| Decision Presentation | Publishing | `DecisionPresentation` target | Current sink receives thesis precursor directly |
| Dashboard View | Publishing | `DashboardView` target | Not implemented; must derive from presentation |
| Institutional Health | Monitoring | `InstitutionalHealth` target | Current `SystemHealth` covers capability availability only |

## Projection map

| Existing representation | Classification | Derives from | Action |
|---|---|---|---|
| `WeightedEvidence` | Projection | `Evidence` + policy + evaluation time | Keep; rename documentation to Evidence Weight Projection |
| `EvidenceDecision` | Projection | Evidence set + Current Market State | Rename to Evidence Assessment |
| `ReasoningDecision` | Projection | Evidence Assessment + Knowledge + Market State | Rename to Reasoning Projection |
| `HorizonBias` | Projection | `AttentionBias` at a trading horizon | Keep |
| `DecisionSnapshot` | Snapshot | Market Thesis inputs and lineage | Keep as Decision Audit Snapshot |
| `DecisionVersion` | Audit record | Market Thesis evolution | Keep |
| `KnowledgeAnswer` | View | Knowledge Objects and Patterns | Keep |
| `RankedSource` | View | Source Profile + evaluation time | Keep |
| `RegimeInterpretation` | Projection | Evidence + Market Regime | Keep |
| `RecommendationTrust` | Audit projection | Market Thesis + lineage + canonical input | Keep |
| `ReasoningComprehensionReview` | Review record | Reasoning Projection | Keep |
| `PublicationReceipt` | Audit record | Decision Presentation delivery | Keep |

## Adapter map

| Adapter | Canonical target | Status | Removal criterion |
|---|---|---|---|
| `gold_brain` facade | Capability composition | Compatibility Adapter | All consumers migrated and equivalence proven |
| v1 decision CLI | Decision Presentation | Compatibility Adapter | New CLI consumes Market Thesis projection |
| `packages.application.DecisionEngine` | Decision Capability | Compatibility Adapter candidate | No direct consumers; parity suite passes |
| `TradingOpportunityEngine` | Evidence → Reasoning → Decision path | Compatibility Adapter candidate | Trading gates represented once in canonical path |
| `EvidenceDecisionEngine` | Evidence Capability implementation | Retain implementation, remove “Engine” public ownership | Capability composition established |
| `InstitutionalReasoningEngine` | Reasoning Capability implementation | Retain implementation, remove parallel output ownership | Market Thesis migration complete |
| Official Decision schemas v1–v4 | Market Thesis schema | Contract Compatibility Adapters | Consumer migration and retention period complete |
| Observation/decision v1 schemas | Current contracts | Contract Compatibility Adapters | Consumer migration evidence complete |

## Canonical domain map

```text
Fact -> Evidence -> KnowledgeObject -> MarketStory projection
     -> Reasoning projection -> MarketThesis
     -> DecisionPresentation -> DashboardView
```

Market State and its Market Regime provide context across the chain. Trade Quality and Bias are
value objects referenced by the thesis; they never form an independent decision.
