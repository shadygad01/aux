# Architecture Entropy Report

## Baseline

The repository has strong inward dependency tests and typed contracts, but conceptual entropy is
high: 109 domain classes, 39 application classes, 23 schemas, 6 engine classes, several transient
stores, and multiple objects named as decisions, states, knowledge, or research.

## Audit findings and dispositions

| Issue | Evidence | Recommendation | Explanation |
|---|---|---|---|
| Parallel decision paths | `DecisionEngine`, `TradingOpportunityEngine`, `EvidenceDecisionEngine`, `InstitutionalReasoningEngine` | Merge/Delete | One canonical path must produce Market Thesis |
| Multiple decision models | Six decision-named domain/capability records | Convert to Projection/Audit/Adapter | Only Market Thesis is a business decision |
| Multiple market states | `MarketState`, `MarketSnapshot`, `CurrentMarketState` | Keep canonical; convert/delete others | Current Market State owns live context; snapshots are audit projections |
| Multiple recommendation vocabularies | `DecisionVerdict`, `Recommendation`, `ExecutionStatus`, `AttentionBias` | Merge/rename | `Recommendation` is thesis output; Bias and execution state need distinct names |
| Parallel trade-quality logic | Compatibility, trading, and evidence calculations | Merge | Raw integer copies must derive from one governed Trade Quality |
| Pattern overlap | `PatternKnowledge`, `DiscoveredPattern` | Keep with lifecycle boundary | Discovery candidate becomes Knowledge projection only after governance |
| Research overlap | `ResearchArtifact`, `ResearchProposal`, `LearningRecommendation` | Separate canonical meanings | Finding, proposal, and learning recommendation are distinct but currently unclear |
| Lineage fragmentation | Graphs, traces, tuples, source strings | Merge | One typed Lineage Graph with projections |
| Quality processes | Six/eight/ten-area review lists | Merge | Institutional Quality Gate now owns ten areas |
| Health models | Capability health only; institutional metrics in prose | Extend canonical Monitoring output | Availability is not institutional health |
| In-memory audit stores | Governance, quality, critique, patterns, research | Keep for tests; replace in production | Restart loses authority records |
| Five Official Decision schemas | v1–v5 | Convert to Contract Adapters/Delete later | Consolidate on Market Thesis v1 after migration |
| Compatibility facade | `gold_brain` and v1 CLI | Keep as Compatibility Adapter | Required until consumer migration evidence exists |
| Encoding corruption | Mojibake in several Markdown files | Repair | Damages professional trust |

## Duplicate responsibility verdict

Decision construction is the highest-risk duplication. Governance helpers are policies, not new
capabilities, but their ownership must follow ADR-0001. No new business capability is justified.

## Complexity-value judgment

Recent governance contracts improved auditability but did not yet improve measured decision
quality. Additional feature code would increase entropy without measurable benefit and is rejected.
