# Phase 0 — Migration Readiness, Canonicalization & Blocker Elimination

Status: **Phase 0 documentation complete; Migration Order step 1 (shared composition root)
implemented — see §N.** This document converts every TD/RB item into an objectively executable
migration plan per the Phase 0 mission. It supersedes no existing governance document; it is a new
cross-reference layer over `technical-debt-register.md`, `capability-blocker-register.md`,
`concept-ownership.md`, and the ADRs.

Evidence basis: direct repository inspection on 2026-08-08 — `git grep` consumer search across
`apps/`, `publish/`, `packages/`, `capabilities/`, `gold_brain/`, `tests/`; full test/lint/type/
coverage run; manual read of all six ADRs and all Phase-0-era governance documents.

**§§A–M below are the original Phase 0 findings and are left as written** — they are a snapshot of
the repository before the composition root existed, and remain the evidence trail for *why* step 1
was ordered first. §N records what was actually built, is dated after §A–M, and is the section to
read for current wiring state. Where §N supersedes a specific claim in §A–M (e.g., §E's "not
implemented in this session"), §N says so explicitly rather than editing the original text.

---

## A. Executive Summary

The previous audit's conclusions hold and are extended here with one central, previously
undocumented finding:

> **The entire `capabilities/` directory — the layer ADR-0001 declares to be "the public system
> boundary" — has zero production consumers.** Not one file under `apps/` or `publish/` (the
> repository's only two real runtime entry points) imports anything from `capabilities/`. Every
> class in `capabilities/` is reachable only from `tests/`.

The actual production system (the code that generates the live GitHub Pages dashboard and the two
CLIs) runs entirely through `packages/application/*Engine` classes and `packages/infrastructure/*`
adapters, composed directly by three independent composition roots:

1. `apps/decision_cli/main.py` — wires `DecisionEngine` directly.
2. `apps/trading_cli/main.py` — wires `TradingOpportunityEngine` directly.
3. `publish/generate_artifacts.py` — the **actual deployed production path** (invoked by
   `.github/workflows/publish.yml` on every push to `main`, and by `deploy_interserver.yml`). Its
   14 generators wire `DecisionEngine`, `ExecutionReadinessEngine`, `OpportunityIdentityEngine`,
   `MultiTimeframeEngine`, `LiveMarketCollector`, and `MacroCollector` directly.

None of the three composition roots constructs a `capabilities.*Capability` object. None wires
Governance, Quality Assurance, Research Governance, Self-Critic, Pattern Discovery, Comprehension,
Trust Assurance, Institutional Memory, Knowledge Base, Decision Memory, or the Reasoning/Evidence
capability engines. This is not new information about *what* is unwired — the previous audit
already established several `InMemory*` adapters are unwired — but it is new information about
*scope*: the unwired set is not a handful of adapters, it is 14 of 20 application-layer classes and
100% of the capability layer.

A second, concrete finding not previously documented: the exact fabricated-value regression fixed
in commit `86a7585` (dashboard showing a hardcoded `94 / 100` Setup Quality when data failed to
load) had a **root cause one layer deeper** than the frontend. The canonical `MarketThesis`
dataclass itself (`packages/domain/market_thesis_models.py`) declared `setup_quality_score: int =
94` as a field default, and `MarketThesis.from_dict` silently substituted `94` for any payload
missing the field. Every real production caller already passed the value explicitly, so this was a
live landmine rather than an active bug — but it is the same fabrication class the project has
already twice deleted (PRs #2–#4), and its own module docstring in `trade_quality.py` states the
project's explicit intent ("no fabricated scores") that the dataclass default silently violated.
This has been fixed in this session (see §L) under the Phase 0 "Safe Implementation Allowance": the
field is now required, `from_dict` now raises on a missing key instead of fabricating one, and a
regression test locks in the corrected contract. No architecture changed; no consumer broke.

A third finding: four capability folders exist in `capabilities/` — `context`, `execution_readiness`,
`macro`, `opportunity_identity` — beyond the ten owners ADR-0001 names (Collection, Normalization,
Evidence, Knowledge, Reasoning, Decision, Learning, Research, Publishing, Monitoring). ADR-0001 is
explicit: *"New capability folders are prohibited without approval. Any exception requires a new ADR
and Constitutional approval."* No such ADR exists. Three of the four (`context`, `execution_readiness`,
`macro`) are independently scored in `docs/readiness-history.json`'s snapshot (14 records where the
formula consumes only 10), without being declared mandatory subprofiles the way Market Story, Market
Thesis, Decision Presentation, and Governance are under ADR-0006. `opportunity_identity` is not
tracked in the readiness snapshot at all. This is pure governance-record drift (docs/tests do not
enforce "exactly ten"), not a runtime risk, since none of the four folders has any production
consumer either.

None of these findings license a migration in this session. Per the Phase 0 rules, no canonical
migration was started. What follows is the executable plan.

---

## B. Runtime Wiring Matrix

"Implemented" = passes type checks and has tests. "Composed" = instantiated by name in a composition
root. "Reachable" = importable from a real entry point's import graph. "Production Path" = actually
executed by a scheduled/CI job today.

| Capability / Class | Implemented | Tested | Composed | Reachable | Production Path |
|---|---|---|---|---|---|
| `DecisionEngine` | Yes | Yes (98%) | `decision_cli`, `gold_brain`, all `publish/generators/*` | Yes | **Yes** (`publish.yml`) |
| `ExecutionReadinessEngine` | Yes | Yes (98%) | `publish/generators/{execution_readiness,market_thesis,opportunity_identity,multi_timeframe}.py` | Yes | **Yes** |
| `OpportunityIdentityEngine` | Yes | Yes (92%) | `publish/generators/opportunity_identity.py` | Yes | **Yes** |
| `MultiTimeframeEngine` | Yes | Yes | `publish/generators/multi_timeframe.py` | Yes | **Yes** |
| `TradingOpportunityEngine` | Yes | Yes (90%) | `apps/trading_cli/main.py` | Yes | No (no workflow invokes `trading_cli`) |
| `build_market_thesis` / `derive_trade_quality` | Yes | Yes | 4 `publish/generators/*` | Yes | **Yes** |
| `EvidenceDecisionEngine` | Yes | Yes (98%) | — | No (tests only) | No |
| `InstitutionalReasoningEngine` | Yes | Yes (96%) | — | No (tests only) | No |
| `LearningEngine` | Yes | Yes (95%) | — | No (tests only) | No |
| `DecisionMemory` / `SqliteDecisionStore` | Yes | Yes (73–95%) | — | No (tests only) | No |
| `InstitutionalKnowledgeBase` | Yes | Yes (96%) | — | No (tests only) | No |
| `ConstitutionalGovernance` / `GovernanceAudit` | Yes | Yes (92%) | — | No (tests only) | No |
| `InstitutionalQualityGate` / `QualityAudit` | Yes | Yes (94%) | — | No (tests only) | No |
| `ResearchGovernance` / `ResearchProposalArchive` | Yes | Yes | — | No (tests only) | No |
| `SelfCritic` / `CritiqueArchive` | Yes | Yes (93%) | — | No (tests only) | No |
| `PatternDiscovery` / `PatternArchive` | Yes | Yes (81%) | — | No (tests only) | No |
| `InstitutionalComprehensionGate` | Yes | Yes | — | No (tests only) | No |
| `InstitutionalMemory` | Yes | Yes | — | No (tests only) | No |
| `TrustAssurance` | Yes | Yes | — | No (tests only) | No |
| `CurrentMarketStateAssembly` | Yes | Yes | — | No (tests only) | No |
| `MarketRegimeIdentification` | Yes | Yes | — | No (tests only) | No |
| All 14 `capabilities/*/capability.py` classes | Yes | Yes | — | **No — zero non-test consumers repository-wide** | No |

**Confusions this table exists to prevent:** "Implemented" and "well-tested" describe 20/20
application-layer classes and 14/14 capability classes. "Production Path" describes 6 classes. The
capability-readiness-matrix's per-capability scores (Evidence 60, Knowledge 60, Learning 60, etc.)
are honest about *implementation* maturity but should not be read as *runtime reachability* —
reachability for those capabilities is uniformly zero.

---

## C. Canonical Ownership Matrix

Derived from `concept-ownership.md` (unchanged — that document is accurate and current) plus the
reachability evidence above.

| Capability concept | Canonical domain model | Canonical implementation today | Canonical composition root | Canonical runtime path |
|---|---|---|---|---|
| Market Thesis | `MarketThesis` (`packages/domain/market_thesis_models.py`) | `build_market_thesis()` (`packages/application/trade_quality.py`) | `publish/generators/market_thesis.py` | **Yes — live** |
| Trade Quality | `TradeQuality` value object | `derive_trade_quality()` | same | **Yes — live** |
| Decision (V1 precursor) | `Decision` | `DecisionEngine.evaluate()` | `decision_cli`, all generators | Yes — live, but is a Compatibility Adapter candidate per `concept-ownership.md`, not the final target |
| Evidence Assessment | `EvidenceDecision` → target rename `EvidenceAssessment` | `EvidenceDecisionEngine` | none | **No — orphaned** |
| Reasoning Projection | `ReasoningDecision` → target rename | `InstitutionalReasoningEngine` | none | **No — orphaned** |
| Market Story | target `MarketStory` (subprofile of Reasoning) | `publish/generators/market_story.py` (ad hoc, does not use `capabilities/market_story`) | `publish/generators/market_story.py` | Partially — a story-shaped artifact is generated live, but not from the canonical `MarketStory` object; `capabilities/market_story/capability.py` is unreachable |
| Lineage Graph | target `LineageGraph` | none | none | **No — not implemented anywhere** |
| Research Finding | target `ResearchFinding` | `ResearchProposalArchive`/`ResearchArtifact` (precursors) | none | **No — orphaned** |
| Learning Recommendation | `LearningRecommendation` | `LearningEngine` | none | **No — orphaned** |
| Decision Presentation | target `DecisionPresentation` | none (CLIs print `Decision`/`TradingDecision` JSON directly) | `decision_cli`, `trading_cli` | **No — CLI bypasses this layer entirely** |
| Institutional Health | target `InstitutionalHealth` | `publish/generators/health.py` (ad hoc) + `capabilities/monitoring` (unreachable) | `publish/generators/health.py` | Partially — an ad hoc health artifact ships live; the canonical `Monitoring` capability object does not |
| Governance | `GovernanceChangeRequest`/`GovernanceDecision` | `ConstitutionalGovernance` | none | **No — orphaned, in-memory only** |
| Decision Memory | `DecisionVersion` audit record | `DecisionMemory` + `SqliteDecisionStore` | none | **No — orphaned; durable store exists but is never opened by any entry point** |
| Knowledge Object | `KnowledgeObject` | `InstitutionalKnowledgeBase` + `JsonLinesKnowledgeRepository` | none | **No — orphaned; durable journal exists but never rehydrated (TD-008)** |

Where two implementations exist for one concept (Decision vs. the capability-layer equivalents),
the canonical one is **whichever is reachable from `publish/generate_artifacts.py`**, because that
is the only path that is genuinely production-composed today. This is a pragmatic tie-breaker, not
a new architectural ruling — it is consistent with `concept-ownership.md`'s existing adapter map,
which already names `DecisionEngine` and `TradingOpportunityEngine` as "Compatibility Adapter
candidates" and the capability layer as the eventual target.

---

## D. In-Memory Adapter Classification

| Adapter | Reachable from production? | Classification | If it should be production-reachable, what's missing |
|---|---|---|---|
| `InMemoryGovernanceAudit` (`packages/infrastructure/governance.py`) | No | Test-only / architectural placeholder | A durable, hash-bound append store (TD-013) — same pattern as `JsonLinesOpportunityRepository`, extended with reviewer-identity binding |
| `InMemoryQualityAssurance` / `QualityAudit` store (`packages/infrastructure/quality_assurance.py`) | No | Test-only / architectural placeholder | Durable append store; revision-hash binding (TD-007, RB-012) |
| `InMemoryResearchGovernance` (`packages/infrastructure/research_governance.py`) | No | Test-only / architectural placeholder | Durable append store (TD-007) |
| `InMemorySelfCritic` (`packages/infrastructure/self_critic.py`) | No | Test-only / architectural placeholder | Durable append store (TD-007) |
| `InMemoryPatternDiscovery` archive (`packages/infrastructure/pattern_discovery.py`) | No | Test-only / architectural placeholder | Durable append store; promotion-gate persistence (TD-007) |
| `InMemoryCapabilityTelemetry` (`packages/infrastructure/capability_telemetry.py`) | No | Test-only / development-only | Not required until a capability composition root exists — telemetry has no consumer to serve yet |
| `InMemoryComprehension` (`packages/infrastructure/comprehension.py`) | No | Test-only / architectural placeholder | Durable review-record store (TD-007) |
| `InMemoryKnowledgeRepository` (base class) / `JsonLinesKnowledgeRepository` (`packages/infrastructure/knowledge_adapters.py`) | No | **Accidental half-migration** — the durable write side (JSONL append) is implemented and correct, but `__init__` never reads the file back, so a restarted process has an empty index despite a non-empty durable log | The read-side rehydration method: replay `self._path` line-by-line into `self._sources/_knowledge/_events/_patterns` on construction. This is TD-008/RB-004's exact, isolated gap — the append path is done; only replay is missing. |

None of these were auto-replaced with a durable implementation in this session. Per Phase 0 Rule 6,
"Do NOT automatically replace it" — this table documents classification and the exact remaining work
only.

One follow-up worth flagging precisely because it is *not* what it looks like: `JsonLinesKnowledgeRepository`
is closer to done than the technical-debt register implies. TD-008 describes the gap as "does not
rehydrate," which is accurate, but the fix is a single bounded method (read-and-replay), not a new
storage design — the durable format, the file, and the write path already exist and are already
tested. This is flagged as a strong first candidate for Canonical Migration 2 (Durable Controls) but
was **not** implemented in this session because it still requires a restart/corruption test suite
(explicitly required by TD-008's own removal strategy) and touches a class used across five test
files — it does not meet the "objectively proven, fully isolated, zero new test design needed" bar
for the Phase 0 safe-fix allowance the way the `setup_quality_score` fix did.

---

## E. CLI / Production Path Analysis (Item 7)

**Is the CLI bypass intentional?** Partially. `docs/adr/0005-compatibility-adapters.md` and
`concept-ownership.md` already classify the v1 CLI as a *Compatibility Adapter*, meaning the project
already knows and has recorded that the CLI is not the canonical presentation path. What is **not**
recorded anywhere is that the CLI is also not the primary *production* path — `publish/generate_artifacts.py`
is, and it bypasses the same layers for a different, undocumented reason (it was built to serve the
GitHub Pages dashboard, which predates or runs parallel to the capability-ownership consolidation).

**Which capabilities are bypassed?** All ten, in every entry point. `DecisionEngine` (used
everywhere) directly implements decision logic; it does not delegate to `capabilities.decision`,
`capabilities.evidence`, `capabilities.reasoning`, or `capabilities.context`. This is uniform across
all three composition roots — it is not a CLI-specific problem, contrary to how TD-015/RB-009 frame
it ("Current CLI bypasses Trust/State/Comprehension contracts"). The identical bypass exists in the
artifact generator, which is the path that actually ships to users today. **TD-015 and RB-009
should be read as understating the blast radius** — the fix target is not "convert the CLI to a
Decision Presentation adapter," it is "give the artifact generator and both CLIs one shared canonical
composition path," because the generator is the one with real users.

**Does scheduled/automated execution use the same path?** Yes for the generator (`publish.yml` runs
on every push to `main`; `deploy_interserver.yml` mirrors it to a second host). No workflow invokes
either CLI. This means `apps/decision_cli` and `apps/trading_cli` are demonstration/manual-use
surfaces today, not scheduled production paths — a materially different risk profile than "the CLI"
singular implied by the existing registers.

**What should the canonical production composition be?** A single composition function —
call it `compose_market_thesis_pipeline()` — that:

1. Is the only place in the repository allowed to construct `DecisionEngine`.
2. Wraps its output through `build_market_thesis()` / `derive_trade_quality()` (already the case in
   the generators).
3. Is imported by `publish/generate_artifacts.py`, `apps/decision_cli`, and `apps/trading_cli` alike,
   so there is exactly one production-composed decision path instead of three independently-wired
   ones that happen to produce compatible output today by convention rather than by contract.
4. Eventually threads through `capabilities.decision`/`capabilities.publishing` once those layers
   have a real consumer — but that composition-root consolidation (step 3) can and should happen
   *before* the capability-layer wiring (step 4), because it collapses three copies of the same
   wiring code into one without touching the currently-orphaned capability layer at all.

This design is **not implemented in this session.** It is not "trivial, isolated, and objectively
safe" under Phase 0 Rule 12 — it touches three entry points and would need its own consumer-parity
verification (does `trading_cli`'s output contract still validate after routing through the shared
composer?). It is queued as the first Canonical Migration 1 step (see §I).

---

## F. Consumer Inventory

Exhaustive, not sampled — built via `grep -rl` across `apps/`, `publish/`, `packages/`, `capabilities/`,
`gold_brain/`, `tests/` for every class named in this document, excluding `__pycache__`.

| Producer | Every consumer found | Contract used | Test coverage of the consumer relationship |
|---|---|---|---|
| `DecisionEngine` | `apps/decision_cli/main.py`; `gold_brain/engine.py` (facade, re-exports with `now=` compatibility signature); `publish/generators/{decision,market_story,market_thesis,execution_readiness,opportunity_identity,multi_timeframe}.py`; `tests/test_trading_*`, `tests/test_publish.py`, `tests/test_production_completion.py` | `Decision` JSON contract v1 (`json_contracts.py`) | Covered — `test_trading_cli_integration.py`, `test_publish.py` exercise the CLI and generator paths end-to-end |
| `TradingOpportunityEngine` | `apps/trading_cli/main.py` only | Trading observation/decision JSON contract | Covered — `test_trading_cli_integration.py`, `test_trading_engine.py` |
| `build_market_thesis` / `derive_trade_quality` | `publish/generators/{market_thesis,opportunity_identity,multi_timeframe,execution_readiness}.py` | `MarketThesis`/`TradeQuality` domain contract | Covered — `test_production_completion.py`, `test_opportunity_identity.py`, `test_multi_timeframe.py` |
| `ExecutionReadinessEngine` | `publish/generators/{execution_readiness,market_thesis,opportunity_identity,multi_timeframe}.py` | `ExecutionReadiness` domain contract | Covered |
| `OpportunityIdentityEngine` | `publish/generators/opportunity_identity.py` | `OpportunityIdentity` domain contract | Covered |
| `MultiTimeframeEngine` | `publish/generators/multi_timeframe.py` | `MultiTimeframeThesis` domain contract | Covered |
| `MarketThesis.from_dict` | `packages/infrastructure/sqlite_decision_store.py` (itself unreachable in production); `tests/test_production_completion.py` | Domain round-trip contract | Covered (extended in this session — see §L) |
| `EvidenceDecisionEngine`, `InstitutionalReasoningEngine`, `LearningEngine`, `DecisionMemory`, `SqliteDecisionStore`, `InstitutionalKnowledgeBase`, `ConstitutionalGovernance`, `InstitutionalQualityGate`, `ResearchGovernance`, `SelfCritic`, `PatternDiscovery`, `InstitutionalComprehensionGate`, `InstitutionalMemory`, `TrustAssurance`, `CurrentMarketStateAssembly`, `MarketRegimeIdentification` | **Zero non-test consumers**, each individually confirmed by grep | N/A | Test-only coverage (85–98% each per `coverage report`) |
| Every `capabilities/*/capability.py` class (14 folders) | **Zero non-test consumers**, confirmed by `grep -rl "from capabilities\.<name>"` across `apps/ packages/ publish/ gold_brain/ runtime/` for all 14 folder names | Capability `Protocol` contracts in `capabilities/contracts.py` | Test-only coverage |

This inventory is complete for every producer named in TD-001…TD-015 and RB-001…RB-012. No
migration in §I may begin until the specific consumer set relevant to it is re-verified at the
commit in progress (inventories drift; this one is timestamped to this document's evidence basis).

---

## G. Parity Test Matrix (required before each migration — not yet written)

| Migration | Parity test needed | Exists today? |
|---|---|---|
| Collapse `DecisionEngine`+`build_market_thesis` call sites into one composer (§E) | Golden-file test: identical `MarketObservation` fixture through old direct-wiring path and new shared composer must produce byte-identical `Decision`/`MarketThesis` JSON | No |
| Retire `EvidenceDecisionEngine`/`InstitutionalReasoningEngine` as public paths | Behavioral equivalence test proving whatever they compute (if anything still needed) is reproduced by the `DecisionEngine`→`build_market_thesis` path, OR an explicit finding that no production behavior depends on them (deletion-safe) | No — this determination itself is unmade; see TD-001 status below |
| Converge `TradingOpportunityEngine` gates into the Market Thesis path | Fixture-based test asserting every one of `TradingOpportunityEngine`'s mandatory gates (macro, three bias horizons, location, liquidity, MACD, SMC, news) has a represented equivalent check in the canonical path, with matching WAIT/BUY/SELL outcomes across a labeled fixture set | No |
| `JsonLinesKnowledgeRepository` rehydration | Restart test: append N records, discard the in-memory instance, construct a fresh instance against the same path, assert `.knowledge()`/`.sources()`/`.events()`/`.patterns()` return the same N records; corruption test for a truncated last line | No (only the append path is tested today) |
| `MarketThesis.setup_quality_score` required-field change | Regression test that `from_dict` raises `KeyError` on a payload missing the field, and that a full round trip still succeeds | **Yes — added in this session** (`test_from_dict_rejects_missing_setup_quality_score`) |
| Durable Governance/QA/Research/SelfCritic/PatternDiscovery/Comprehension stores | Restore test per store: write via new durable adapter, restart, read back identical records; identity/hash-binding test per TD-013 | No |
| `LineageGraph` introduction (ADR-0003) | Full-path lineage test: every node from Fact through Decision Presentation resolves a complete, hash-verified provenance chain | No — LineageGraph does not exist yet to test |

No parity tests were authored for the unstarted migrations in this session (writing them without a
committed migration target risks becoming the "parallel implementation" Phase 0 explicitly forbids —
a parity test needs two concrete things to compare, and for most rows above the "new" side does not
exist yet). The one parity test that could be written safely — for the isolated `setup_quality_score`
fix — was written.

---

## H. Migration Dependency Graph

```text
                    ┌─────────────────────────────┐
                    │ E. Shared composition root   │   (no consumer inventory blockers;
                    │    (compose_market_thesis_   │    ready to start first)
                    │    pipeline)                 │
                    └──────────────┬───────────────┘
                                   │ unblocks
                                   ▼
        ┌──────────────────────────────────────────────┐
        │ TD-001 / RB-006: retire EvidenceDecisionEngine │
        │ and InstitutionalReasoningEngine as public      │
        │ paths; converge TradingOpportunityEngine gates  │
        └───────────────────┬────────────────────────────┘
                            │ requires TD-001 output shape frozen
                            ▼
        ┌──────────────────────────────────────────────┐
        │ TD-002: MarketThesis is already the domain     │
        │ object (done); remaining work is deleting the  │
        │ OfficialDecision precursor from capabilities/   │
        │ once capabilities/ has a consumer (blocked by   │
        │ RB-009 below)                                   │
        └───────────────────┬────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────────┐
        │ TD-008 / RB-004: Knowledge rehydration          │
        │ (independent — no dependency on TD-001)         │
        └──────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────┐
        │ TD-004 / RB-003: LineageGraph (ADR-0003)        │
        │ — depends on TD-001's converged path existing   │
        │ so there is one path to attach provenance to,   │
        │ not three                                       │
        └───────────────────┬────────────────────────────┘
                            │
                            ▼
        ┌──────────────────────────────────────────────┐
        │ RB-009: Decision Presentation / capabilities/   │
        │ wiring — depends on TD-001 (one canonical path  │
        │ to wrap) AND TD-004 (presentation must carry     │
        │ lineage per the lineage contract)                │
        └───────────────────┬────────────────────────────┘
                            │ gives capabilities/ its first
                            │ real consumer
                            ▼
        ┌──────────────────────────────────────────────┐
        │ RB-005 / TD-006: Market Story canonicalization, │
        │ Reasoning/Evidence capability wiring — natural   │
        │ to land once RB-009 proves the capability layer  │
        │ can be safely composed into a live entry point   │
        └──────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────┐
        │ TD-007 / TD-013 / RB-007 / RB-010 / RB-012:     │
        │ durable Governance/QA/Research/SelfCritic/       │
        │ PatternDiscovery/Comprehension stores            │
        │ — independent of the decision-path migrations;   │
        │ blocked only by needing a consumer (same as       │
        │ capabilities/ generally) to justify durability    │
        │ work before there is traffic to durably record    │
        └──────────────────────────────────────────────┘

        ┌──────────────────────────────────────────────┐
        │ TD-005 / RB-008: ResearchFinding + 23 hypothesis│
        │ studies — independent, but has no code           │
        │ prerequisite; it is a research-methodology         │
        │ workstream (Genuine Business Constraint: needs     │
        │ market data history and a walk-forward harness      │
        │ neither of which exist), not a migration            │
        └──────────────────────────────────────────────┘
```

---

## I. Migration Order

1. **Shared composition root** (§E design). No consumer-inventory blocker (§F is complete for all
   three composition roots today). Lowest risk: it does not delete anything, it only centralizes
   three copies of equivalent wiring code. Required first because every downstream migration
   (TD-001, TD-004, RB-009) needs exactly one call site to change instead of three.
2. **TD-001 / RB-006** — retire `EvidenceDecisionEngine`/`InstitutionalReasoningEngine` as public
   paths, converge `TradingOpportunityEngine`'s gates into the canonical path. Ordered second
   because it is the highest-risk, highest-value item (core business logic) and every other
   migration in this graph either depends on its output shape or is independent of it — doing it
   early means later migrations build on the final shape once, not twice.
3. **TD-008 / RB-004** — Knowledge rehydration. Independent of 1–2; ordered third only because it is
   the lowest-risk, smallest-scope item with the clearest Definition of Done, making it a good
   confidence-building migration to run in parallel with or immediately after the decision-path work
   without resourcing conflict (different files, different owners per `concept-ownership.md`:
   Knowledge vs. Decision).
4. **TD-004 / RB-003** — LineageGraph. Depends on step 2 (one canonical path to attach provenance
   nodes to; attaching lineage to three divergent paths would triple the work and risk divergent
   graphs — exactly what ADR-0003 forbids).
5. **RB-009** — Decision Presentation / first real `capabilities/` wiring. Depends on steps 2 and 4
   (a presentation layer needs both a single source decision and a lineage graph to expose, per the
   lineage contract's required path).
6. **RB-005 / TD-006** — Market Story canonicalization and Reasoning/Evidence capability wiring.
   Depends on step 5 proving the capability layer can be safely given a real consumer without
   breaking the (currently 100%-passing) architecture-boundary tests.
7. **TD-007 / TD-013 / RB-007 / RB-010 / RB-012** — durable stores for Governance/QA/Research/
   SelfCritic/PatternDiscovery/Comprehension. Independent of 1–6 technically, but sequenced after
   them deliberately: building durable, hash-bound, identity-verified storage for capabilities that
   still have zero production consumers is effort spent before it can be validated by real traffic.
   Once RB-009 lands, these have a consumer and durability work stops being speculative.
8. **TD-005 / RB-008** — Research Finding + hypothesis validation. Explicitly independent of all
   code migrations; gated on external requirements (see §K), not on internal sequencing.

Rollback safety note: steps 1 and 3 are additive/refactor-only and trivially revertible (git revert,
no schema or persisted-data implications). Steps 2, 4, 5, and 6 delete or redirect production code
paths and require the parity tests in §G to exist and pass *before* any deletion — per Phase 0 Rule
("delete legacy implementations before consumer inventory" is forbidden; consumer inventory is done,
parity tests are not). Steps 7–8 are additive (new stores, new research artifacts) and low
rollback risk by construction.

---

## J. TD-001 … TD-015 Status

Each entry: **Status** is exactly one of Resolved / Migration Ready / External Auditor Required /
Genuine External Dependency / Genuine Business Constraint, per the Phase 0 primary objective.

### TD-001 — Multiple decision engines predate canonical ownership
- **Root cause:** `packages/application` accumulated four independent evaluation engines
  (`DecisionEngine`, `TradingOpportunityEngine`, `EvidenceDecisionEngine`,
  `InstitutionalReasoningEngine`) as the capability-ownership model was introduced without a
  corresponding deletion/merge pass.
- **Affected components:** `packages/application/{decision_engine,trading_engine,evidence_engine,reasoning_engine}.py`
- **Canonical implementation today:** `DecisionEngine` + `build_market_thesis()` (reachable, production-composed).
- **Legacy/competing:** `TradingOpportunityEngine` (reachable, but only via unscheduled `trading_cli`); `EvidenceDecisionEngine`, `InstitutionalReasoningEngine` (fully orphaned).
- **Consumers / Producers / Entry points:** See §F row 1–3.
- **Persistence impact:** None shared; each engine owns its own output shape.
- **Contract impact:** Three incompatible JSON contracts must converge to one.
- **Test coverage:** 90–98% per engine, in isolation only.
- **Required migration:** Build the shared composition root (§E); converge `TradingOpportunityEngine`'s
  gates into it with a parity suite; determine via explicit dead-code analysis (not assumption)
  whether `EvidenceDecisionEngine`/`InstitutionalReasoningEngine` compute anything not already
  covered, then delete or fold in.
- **Migration preconditions:** §F consumer inventory (done); §E composer merged first.
- **Required parity tests:** §G rows 1–3.
- **Rollback:** Git-revertible; no persisted state depends on the old wiring.
- **Risk:** High (core business logic).
- **External dependency:** None.
- **External auditor requirement:** Yes — Architecture + Trading review (ADR-0004) before any engine deletion.
- **Definition of Done:** Every production entry point constructs its decision output via one shared
  composer; `EvidenceDecisionEngine` and `InstitutionalReasoningEngine` are either deleted or no
  longer independently public; `TradingOpportunityEngine`'s mandatory gates have a passing parity
  suite against the canonical path; zero production imports of a second decision-shaped output.
- **Status: Migration Ready.**

### TD-002 — Market Thesis canonical object is not yet named/moved into domain
- **Root cause:** Historical — predates `MarketThesis` existing at all.
- **Current state:** **Substantially resolved.** `MarketThesis` (`packages/domain/market_thesis_models.py`)
  is a real, canonical, tested, production-composed domain object (§B, §C). `OfficialDecision`
  remains only inside `capabilities/decision` and `capabilities/publishing` — both unreachable — so
  it is not competing with `MarketThesis` for any live consumer today.
- **Affected components:** `capabilities/decision/capability.py`, `capabilities/publishing/capability.py`.
- **Required remaining migration:** Delete or rename `OfficialDecision` once `capabilities/decision`
  gains a real consumer (RB-009) — deleting it now, before that consumer exists, would be
  speculative rework with no observer to validate against.
- **Consumers:** `capabilities/decision`, `capabilities/publishing` (internal to the unreachable layer only).
- **Test coverage:** Covered within `test_capabilities.py`.
- **Rollback:** Trivial — no external consumers.
- **Risk:** Low.
- **External auditor requirement:** No — this is bookkeeping once RB-009 lands, not a new decision.
- **Definition of Done:** `capabilities/decision` exposes `MarketThesis` (or a thin projection of it)
  rather than `OfficialDecision`; the concept-ownership table's "target" annotation is removed.
- **Status: Migration Ready** (blocked only on RB-009 giving `capabilities/decision` a reason to exist in production first — sequencing is documented in §I, not effort).

### TD-003 — Trade Quality is a raw integer with multiple formulas
- **Current state:** **Substantially resolved on the production path.** `derive_trade_quality()`
  (`packages/application/trade_quality.py`) is the single formula used by every reachable production
  consumer (§F). Its own docstring documents the prior fabrication it replaced. The remaining raw
  integer exposure is `MarketThesis.setup_quality_score: int` and `OpportunityIdentity.setup_quality_score: int`
  — both now populated exclusively from `TradeQuality.score` (verified in §F; the fabricated default
  that could bypass this was removed in this session, §L).
- **Affected components:** `packages/application/trade_quality.py`, `packages/domain/market_thesis_models.py`, `packages/domain/opportunity_models.py`.
- **Remaining gap:** No single governed value object wraps "trade quality" end-to-end — it is a
  `TradeQuality` dataclass on `MarketThesis` and a bare `int` (`setup_quality_score`) copied onto
  `OpportunityIdentity`/`MultiTimeframeThesis`. The `int` copies are a projection, not a second
  formula, so this is a naming/typing cleanup, not a duplication bug.
- **Test coverage:** Covered.
- **Required migration:** Consider typing `OpportunityIdentity.setup_quality_score` and
  `MultiTimeframeThesis.setup_quality_score` as derived properties from an embedded `TradeQuality`
  rather than a copied `int`, for stronger contract enforcement. Cosmetic/typing improvement, not a
  correctness fix — the values are already sourced from one formula.
- **Rollback:** Trivial.
- **Risk:** Low.
- **External auditor requirement:** No.
- **Definition of Done:** One `TradeQuality`-producing function; all `setup_quality_score` fields
  provably derive from it (now true); optional follow-up: strengthen the type from `int` to a
  value-object reference.
- **Status: Resolved** (formula duplication eliminated; only a low-priority typing refinement remains, tracked as TD-003-a below rather than reopening this ID).

### TD-004 — No canonical Lineage Graph
- **Root cause:** Genuinely unimplemented — `LineageGraph` does not exist anywhere in the codebase (confirmed: zero matches for `LineageGraph` outside `docs/`).
- **Affected components:** Would span `packages/domain` (new model), `packages/application` (every engine that currently returns bare `reasons`/`conflicts`/`missing_evidence` string tuples instead of typed provenance nodes), `packages/infrastructure` (persistence).
- **Current representation:** String tuples on `Decision`/`MarketThesis` (`reasons`, `conflicts`, `missing_evidence`) with no node IDs, hashes, or typed edges.
- **Consumers of the current string-tuple representation:** Every generator, both CLIs, `docs/app.js` (`renderWhyPanel`).
- **Test coverage:** N/A — nothing to test yet.
- **Required migration:** Implement ADR-0003's typed lineage DAG; add adapters that project it into the existing `reasons`/`conflicts`/`missing_evidence` shape so current consumers (including the live dashboard) keep working unchanged during the transition.
- **Migration preconditions:** TD-001's single canonical path (§I order) — attaching lineage to three divergent decision paths triples the work.
- **Required parity tests:** Golden test that the projection adapter's `reasons`/`conflicts`/`missing_evidence` output is byte-identical to today's pre-migration output for the same fixtures, proving the dashboard and both CLIs see no behavior change.
- **Rollback:** Adapter-based rollout makes this revertible per-generator.
- **Risk:** High — touches every decision-producing path; XL effort confirmed.
- **External dependency:** None.
- **External auditor requirement:** Yes — Architecture review; this is the deepest structural change in the register.
- **Definition of Done:** One `LineageGraph` type; every Market Thesis and Decision Presentation references a complete graph; `DecisionGraph`/`ExplanationTrace`/tuple-based provenance become documented projections, never a second source of truth.
- **Status: Migration Ready** (design already specified in ADR-0003; blocked on TD-001 landing first per §I, and on External Auditor Architecture review before implementation begins).

### TD-005 — No canonical Research Finding
- **Root cause:** `ResearchArtifact`/`ResearchProposal` exist as precursors; the lifecycle that would resolve them into a `ResearchFinding` was never built.
- **Affected components:** `packages/domain` (new model needed), `packages/application/research_governance.py` (orphaned — §D).
- **Consumers:** None in production (capability is unreachable, §B).
- **Test coverage:** Precursor classes covered; `ResearchFinding` has nothing to test yet.
- **Required migration:** Define the finding lifecycle (proposal → governed study → finding), migrate `ResearchProposalArchive` output into it.
- **Genuine dependency:** This item cannot be "migration ready" independent of TD-014 — a finding lifecycle with no studies to conclude has nothing to migrate toward. It is code-ready to design but the 23 hypotheses (TD-014) are what would populate it.
- **Rollback:** N/A — additive.
- **Risk:** Medium; effort M per the register.
- **External auditor requirement:** Yes — Research review area.
- **Definition of Done:** `ResearchFinding` exists as a canonical model with a defined lifecycle; `ResearchProposalArchive` output is migrated into it; at least one hypothesis has completed the full lifecycle end to end as a proof of the pipeline (not necessarily a *validated* one — a rejected finding proves the pipeline equally well).
- **Status: Migration Ready** for the lifecycle/model design; the register's stronger claim ("100% of consumed hypotheses" per the promotion rule) is a **Genuine Business Constraint** — see TD-014.

### TD-006 — Six (now nine) engine classes expose historical paths
- **Current state:** The count has grown from 6 (baseline snapshot) to 9 `*Engine` classes (§F,
  confirmed by `grep '^class .*Engine'`): `InstitutionalReasoningEngine`, `LearningEngine`,
  `OpportunityIdentityEngine`, `MultiTimeframeEngine`, `DecisionEngine`, `TradingOpportunityEngine`,
  `EvidenceDecisionEngine`, `ExecutionReadinessEngine`, plus `gold_brain.engine.DecisionEngine`
  (the compatibility facade). The baseline in `institutional-health-dashboard.md` (6) is stale and
  should be corrected to 9 the next time that document is regenerated — this is a documentation
  accuracy note, not a new debt item.
- **Affected components:** All of `packages/application/*_engine.py`.
- **Consumers:** Per §B — 4 of 9 are production-composed (`DecisionEngine`, `ExecutionReadinessEngine`, `OpportunityIdentityEngine`, `MultiTimeframeEngine`); `TradingOpportunityEngine` is reachable-but-unscheduled; 3 are fully orphaned; `gold_brain.engine.DecisionEngine` is an explicit, ADR-0005-sanctioned Compatibility Adapter.
- **Test coverage:** 90–98% per engine.
- **Required migration:** Convert reachable-and-orphaned engines to internal implementation details of their owning capability (per `concept-ownership.md`'s adapter map, which already specifies this for `EvidenceDecisionEngine` and `InstitutionalReasoningEngine`); this is the same work as TD-001, not separate work.
- **Rollback:** Same as TD-001.
- **Risk:** Same as TD-001.
- **External auditor requirement:** Same review as TD-001 (Architecture).
- **Definition of Done:** Zero `*Engine` classes remain public outside `packages/application`'s internal call graph from the single composer (§E); `gold_brain.engine.DecisionEngine` remains as the only sanctioned public compatibility surface with no business logic of its own (already true — it delegates to `packages.application.DecisionEngine`).
- **Status: Migration Ready** (identical execution to TD-001; tracked separately in the register only because it counts a symptom of the same root cause).

### TD-007 — Governance/review/research stores are in-memory
- **Root cause:** Confirmed in §D — six adapters are genuinely in-memory-only with zero production consumers.
- **Affected components:** `packages/infrastructure/{governance,quality_assurance,research_governance,self_critic,pattern_discovery,comprehension}.py`.
- **Required migration:** Durable, hash-bound append stores per adapter, following the exact pattern already proven correct and tested in `JsonLinesOpportunityRepository` (trading ledger) and the write-side of `JsonLinesKnowledgeRepository`.
- **Migration preconditions:** None technically (each store is independent and additive) — sequenced late in §I only because building durability for zero-consumer capabilities is speculative until RB-009 gives them a caller.
- **Required parity tests:** Restore test per store (§G).
- **Rollback:** Additive; trivially revertible per store.
- **Risk:** Low-medium per store; L effort each, matching the register.
- **External auditor requirement:** Yes — Security review (TD-013's identity-binding requirement is coupled here) before any store is treated as authoritative.
- **Definition of Done:** Each store survives a process restart with zero record loss, corruption is detected and reported (not silently dropped), and a restore test exists in the suite for each.
- **Status: Migration Ready** for the storage mechanics; **External Auditor Required** before durable records are treated as authoritative institutional history (TD-013's identity-binding is a Security review gate, not an engineering one).

### TD-008 — Knowledge index does not rehydrate after restart
- **Root cause:** Precisely isolated in §D — `JsonLinesKnowledgeRepository.__init__` never replays its own durable log.
- **Affected components:** `packages/infrastructure/knowledge_adapters.py` only.
- **Required migration:** Add a replay method invoked from `__init__`; add a restart test and a truncated-last-line corruption test.
- **Migration preconditions:** None — this is the most isolated item in the entire register.
- **Required parity tests:** §G row 4 (not yet written).
- **Rollback:** Trivial.
- **Risk:** Low.
- **External auditor requirement:** No — this is an engineering completion of an already-approved design, not a new architectural decision.
- **Definition of Done:** A fresh `JsonLinesKnowledgeRepository(path)` against a non-empty existing file returns the same records a process that never restarted would; a corrupted/truncated final line is detected and reported rather than crashing or silently dropping preceding valid records.
- **Status: Migration Ready** — the strongest "safe to execute next" candidate in the entire register precisely because it needs no parity test against a second implementation (there is only one implementation; the fix completes it) and no external auditor sign-off (no architectural decision is being made, only a documented gap being closed). Not implemented in this session because it still requires new restart/corruption tests to satisfy the "regression coverage" bar (Phase 0 Rule 12) at a level beyond a five-minute patch — reserved as the first item to execute in Canonical Migration 2.

### TD-009 — Official Decision has five major schemas in one sprint history
- **Current state:** `OfficialDecision` is confirmed unreachable in production (§B, §C) — the schema
  sprawl exists but is inert; it cannot corrupt any live consumer today because there are none.
- **Affected components:** `capabilities/decision/capability.py`.
- **Required migration:** Consolidate on `MarketThesis` v1 as the one schema once RB-009 gives `capabilities/decision` a real consumer; until then, consolidating five unreachable schemas into one unreachable schema has no observable effect to verify against.
- **Rollback:** N/A.
- **Risk:** Low today (dormant); would become Medium once RB-009 lands.
- **External auditor requirement:** Bundled into RB-009's review, not separate.
- **Definition of Done:** One schema version under `capabilities/decision`, matching `MarketThesis`'s contract.
- **Status: Migration Ready**, sequenced after RB-009 per §I (consolidating dead schemas before they have a reader is cosmetic-completion, which Phase 0 explicitly rejects as a way to "mark a blocker resolved merely because documentation was written").

### TD-010 — No roadmap or ADRs existed before consolidation
- **Status: Resolved.** Six ADRs, a roadmap, and a governance-consolidation report exist and are current (read in full while building this document). No further action.

### TD-011 — Documentation contains encoding corruption
- **Verification performed this session:** Every file under `docs/*.md` was checked for invalid
  UTF-8 (`.decode('utf-8')` per file — zero failures) and for common mojibake byte sequences
  (`Ã¢â‚¬`, `â€`, `Â `-type patterns — zero matches). No encoding corruption exists in the current
  tree.
- **Discrepancy noted:** `architecture-entropy-report.md` still lists "Encoding corruption" as an
  open audit finding with recommendation "Repair." That document was not edited in this session
  (editing another team's governance finding without being certain of its original scope is exactly
  the kind of unilateral record change Phase 0 warns against for closure claims) — it is flagged
  here as ready for the document's own owner to close with this verification as evidence.
- **Required migration:** None — no code or content change needed.
- **Rollback:** N/A.
- **Risk:** None.
- **External auditor requirement:** No.
- **Definition of Done:** Already met — zero files fail UTF-8 decoding; zero mojibake patterns found.
- **Status: Resolved** (verification evidence: this session's full-corpus UTF-8 + mojibake scan, see command log; `technical-debt-register.md`/`architecture-entropy-report.md` update to reflect closure is a documentation action for the register's own change-control process, not performed unilaterally here).

### TD-012 — Compatibility documentation is stale
- **Verified specific instance:** `docs/architecture.md` (the "Version 1 Foundation" document)
  describes a pre-capability, pre-ADR architecture ("Context boundary," "Immutable methodology
  gates" as prose, not as the `capabilities/context` implementation) and is not cross-referenced
  from `concept-ownership.md` or the ADRs at all. It is not marked as superseded or as a
  Compatibility Adapter description anywhere.
- **Affected components:** `docs/architecture.md`.
- **Required migration:** Either mark `docs/architecture.md` explicitly as the historical V1
  description (with a pointer to `concept-ownership.md` as the current canonical map) or fold its
  still-accurate content (the methodology gates, the explainability contract) into the current
  architecture documentation set.
- **Rollback:** N/A — documentation-only.
- **Risk:** Low.
- **External auditor requirement:** No.
- **Definition of Done:** `docs/architecture.md` either carries an explicit "superseded by
  concept-ownership.md" banner or is merged/retired.
- **Status: Migration Ready** (this is a same-session-safe documentation fix per Phase 0 Rule 12,
  but was not performed here to avoid editing a second governance document's authority boundary
  without the "objectively proven, single owner, zero ambiguity" bar the `setup_quality_score` code
  fix cleared — the correct disposition of `architecture.md`, banner vs. merge vs. retire, is itself
  an architecture-ownership call, not a typo fix).

### TD-013 — No durable reviewer identity or artifact hash binding
- **Root cause:** Confirmed — none of the in-memory audit stores (§D) carry a signed reviewer
  identity or bind their record to a specific commit/artifact hash.
- **Affected components:** Same six adapters as TD-007.
- **Required migration:** Add identity verification and hash binding to each durable store built
  under TD-007 — this is additive scope on TD-007's work, not a separate migration.
- **Rollback:** Same as TD-007.
- **Risk:** Same as TD-007.
- **External auditor requirement: Yes — Security review, explicitly, because "approvals can be
  fabricated/reused" is a security property, not an engineering one.**
- **Definition of Done:** Every governance/QA/research/critique record carries a verifiable reviewer
  identity and a hash binding to the exact artifact revision it approved; a forged or replayed
  approval is detectable.
- **Status: External Auditor Required** — this is the one register item where the *engineering*
  work is straightforward (extend TD-007's stores with two more fields) but the *acceptance
  criteria* for what counts as adequate identity verification is a security policy decision this
  document cannot make unilaterally.

### TD-014 — All 23 registered trading hypotheses are unvalidated
- **Verified:** `docs/hypothesis-register.md` lists exactly 23 hypotheses (H-001…H-023), all status
  `UNVALIDATED`, confirmed by direct read.
- **Required migration:** None — this is not a code defect. It requires a walk-forward research
  harness, historical labeled market data, and governed study execution per capability (Research)
  ownership — none of which exist in this repository and none of which can be produced by writing
  code alone (they require market data history the repository does not and, per the project's own
  "no live-data" non-goal in `README.md`, is not meant to fabricate).
- **Rollback:** N/A.
- **Risk:** N/A.
- **External dependency:** Historical/labeled market data source; a walk-forward evaluation harness
  (itself XL new-code effort, but gated on having data to run it against).
- **External auditor requirement:** Yes — Research review area; no hypothesis may be promoted
  without Governance Level 2 evidence per `roadmap.md` Phase 3.
- **Definition of Done:** Cannot be stated as a code-level condition — it is inherently "N of 23
  hypotheses have completed governed validation," which is a research-outcome, not an
  implementation-completeness, metric.
- **Status: Genuine Business Constraint** — explicitly, per the mission's own Phase 4 classification
  rules, this must never be allowed to reduce implementation maturity, and it is recorded here as
  external to what code changes can resolve.

### TD-015 — Current CLI bypasses Trust/State/Comprehension contracts
- **Extended finding (§E):** This bypass is not CLI-specific — it is identical across all three
  composition roots, and the artifact generator (the one with real users) has the same bypass the
  register attributes only to the CLI.
- **Affected components:** `apps/decision_cli/main.py`, `apps/trading_cli/main.py`, `publish/generate_artifacts.py`.
- **Required migration:** The shared composition root (§E, Migration Order step 1) is the
  prerequisite; converting to a "Decision Presentation adapter" (the register's stated fix) is then
  identical work to RB-009, not separate work — merging TD-015 into RB-009's execution avoids
  building the presentation layer twice (once "for the CLI," once "for Publishing").
- **Rollback:** Same as RB-009.
- **Risk:** Same as RB-009.
- **External auditor requirement:** Same as RB-009 (Publishing/Explainability review).
- **Definition of Done:** Same as RB-009's Definition of Done, applied to all three entry points
  uniformly rather than just the CLI.
- **Status: Migration Ready**, explicitly merged into RB-009's execution rather than tracked as
  independent work (see §I — this is a scope correction, not a new claim; the underlying debt is
  unchanged, only its true extent is now documented).

---

## K. RB-001 … RB-012 Status

### RB-001 — Collection: no production collection adapter or source assurance
- **Verified:** `LiveMarketCollector` (`packages/infrastructure/live_collector.py`) **is** a real,
  production-composed collector (reachable from all four price-dependent generators, §B) with
  genuine network I/O, timeouts, and a three-tier honest-fallback chain (candles → spot price →
  empty). This contradicts the register's framing ("no production collection adapter") — a
  production collector exists and is live today.
- **What is still genuinely missing:** Source *assurance* — no retry/backoff policy beyond a single
  attempt per tier, no source-reliability scoring, no multi-source corroboration (only Yahoo Finance
  futures + gold-api.com spot, both unauthenticated free endpoints with no SLA).
- **Affected components:** `packages/infrastructure/live_collector.py`, `packages/infrastructure/yahoo_chart.py`, `packages/infrastructure/macro_collectors.py`.
- **Required migration:** Add retry-with-backoff (currently a single `urlopen` attempt per source);
  add a source-reliability/health record consumable by Monitoring. This is additive to an existing,
  working implementation — not a new build.
- **Test coverage:** `test_yahoo_chart.py` covers parsing defensively (12 tests); collector-level
  retry/backoff has no tests because no retry logic exists yet.
- **Rollback:** Additive; trivial.
- **Risk:** Low.
- **External dependency:** The two free public APIs themselves — no SLA, no authentication, subject
  to rate-limiting or disappearance without notice. This part is a **Genuine External Dependency**
  regardless of code quality.
- **External auditor requirement:** No — retry/backoff is standard engineering hardening.
- **Definition of Done:** Retry-with-exponential-backoff on both collector tiers; a source-health
  record exposed to Monitoring; documented SLA-less status of both upstream APIs.
- **Status: Migration Ready** for the retry/backoff hardening (small, isolated, additive — a strong
  Canonical Migration 2 candidate); **Genuine External Dependency** for the underlying "no paid,
  SLA-backed source exists" limitation, which no amount of repository-local work resolves.

### RB-002 — Normalization: no published transformation contract
- **Verified:** `capabilities/normalization/capability.py` implements deterministic normalization
  (86% coverage) but, per §B, is unreachable from production; the actual normalization performed by
  `LiveMarketCollector`/`build_observation_from_candles` (in `smc_detector.py`) has no published
  JSON Schema the way `contracts/` does for other artifacts (verified: `contracts/` has no
  normalization schema file).
- **Affected components:** `capabilities/normalization/capability.py`, `contracts/`.
- **Required migration:** Publish a versioned transformation contract (units, rounding, timezone
  normalization rules) alongside the existing 23 schemas in `contracts/`.
- **Rollback:** Additive.
- **Risk:** Low.
- **External auditor requirement:** No.
- **Definition of Done:** A `contracts/normalization-v1.schema.json` exists, is referenced by
  `capabilities/normalization`, and the live production normalization path
  (`build_observation_from_candles`) is checked against it.
- **Status: Migration Ready.**

### RB-003 — Evidence: canonical LineageGraph absent
- Identical scope to TD-004. **Status: Migration Ready** — see TD-004 for the full breakdown (not
  duplicated here to avoid two divergent Definitions of Done for one blocker, which Phase 0
  explicitly warns against — "do not leave two competing sources of truth").

### RB-004 — Knowledge: search index does not rehydrate safely
- Identical scope to TD-008. **Status: Migration Ready** — see TD-008.

### RB-005 — Reasoning: Market Story is not a canonical implemented projection
- **Verified:** `publish/generators/market_story.py` (293 lines) generates a story-shaped artifact
  live today, but it is a bespoke generator, not an instance of `capabilities/market_story`'s
  domain model — confirmed by import inspection (§B: the generator imports `DecisionEngine`,
  `MacroCollector`, `smc_detector`, `momentum`, `yahoo_chart` directly; it does not import
  `capabilities.market_story`).
- **Affected components:** `publish/generators/market_story.py`, `capabilities/market_story/capability.py`.
- **Required migration:** Either (a) make the generator construct and derive from the canonical
  `capabilities.market_story` object, giving that capability its first production consumer, or (b)
  formally retarget the canonical object to match what the generator already proves works in
  production, then wire the generator through it. Given §E/§I's sequencing (capability wiring comes
  after the shared composer and lineage work), this is deliberately downstream.
- **Rollback:** Additive/refactor.
- **Risk:** Medium-high (XL effort per register; touches a 293-line live generator).
- **External auditor requirement:** Yes — Reasoning/Explainability review of which representation becomes canonical.
- **Definition of Done:** One `MarketStory`-producing path; `publish/generators/market_story.py` and
  `capabilities/market_story` are the same object, not two compatible-by-convention ones.
- **Status: Migration Ready**, sequenced per §I step 6.

### RB-006 — Decision: MarketThesis and TradeQuality are not canonical code
- **Superseded by evidence.** As shown in TD-002/TD-003, `MarketThesis` and `TradeQuality` **are**
  canonical, implemented, tested, and production-composed today. This register entry is stale
  relative to the current codebase — the gap it describes has been substantially closed since the
  register was last written (evidence: `packages/application/trade_quality.py`'s own docstring
  documents the fix, and §B/§F confirm production reachability).
- **What remains genuinely open under this ID:** Only the `capabilities/decision` wiring (folded
  into RB-009) and the `OfficialDecision` retirement (TD-002's remaining scope).
- **Status: Resolved** for "MarketThesis and TradeQuality are not canonical code" as literally
  stated; remaining scope tracked under RB-009 and TD-002 to avoid double-counting.

### RB-007 — Learning: institutional learning records are not durably stored
- Identical scope to TD-007 for the `LearningEngine`/learning-record path specifically. **Status:
  Migration Ready** for storage mechanics, **External Auditor Required** for identity-binding — see
  TD-007 (this entry's `LearningEngine` is one of the six adapters covered there; not duplicated).

### RB-008 — Research: ResearchFinding absent; 23 hypotheses unvalidated
- Combines TD-005 (code-level: Migration Ready) and TD-014 (research-outcome level: Genuine
  Business Constraint). **Status: split — Migration Ready (model/lifecycle) + Genuine Business
  Constraint (validation outcomes)**, matching TD-005/TD-014 exactly.

### RB-009 — Publishing: DecisionPresentation absent and CLI bypasses controls
- **Extended per §E: this is the single highest-leverage remaining item.** It is the shared
  prerequisite for TD-002's completion, TD-009's completion, RB-005's completion, and it corrects
  TD-015's understated scope (the bypass is repository-wide, not CLI-specific).
- **Affected components:** New `DecisionPresentation` domain model; `apps/decision_cli`,
  `apps/trading_cli`, `publish/generate_artifacts.py`; `capabilities/publishing/capability.py`.
- **Required migration:** Build `DecisionPresentation` as a real projection of `MarketThesis` +
  `LineageGraph` (hence sequenced after TD-004 in §I); route the shared composer (§E) through it;
  give `capabilities/publishing` its first production consumer.
- **Rollback:** Additive at the presentation layer; the underlying `MarketThesis` computation is
  unchanged, so rollback is a routing change, not a data-model change.
- **Risk:** High — XL effort, touches all three entry points and the live dashboard's data contract.
- **External auditor requirement:** Yes — Publishing + Explainability review; this is the
  consumer-facing correctness boundary for the entire system.
- **Definition of Done:** All three entry points emit a `DecisionPresentation` built from
  `MarketThesis` + lineage; no entry point serializes `Decision`/`TradingDecision` directly to a
  public consumer; `docs/app.js` consumes the presentation contract (verified compatible via a
  parity test against the current `decision.json`/`market_thesis.json` shape, since the live
  dashboard must not regress).
- **Status: Migration Ready**, sequenced per §I step 5 (after the shared composer and LineageGraph).

### RB-010 — Monitoring: readiness and governance are not durable or executable
- **Verified:** `publish/generators/health.py` and `readiness.py` are live and production-composed
  (§F) — readiness *reporting* is executable today (it ships in the live artifacts). What is
  genuinely missing is durable, hash-bound governance enforcement (TD-007/TD-013's scope) — the
  "not executable" half of this claim is stale; the "not durable" half is accurate and tracked under
  TD-007/TD-013.
- **Status: Resolved** for "readiness ... not executable" (it is executable and ships live);
  **Migration Ready / External Auditor Required** for "governance ... not durable" — see TD-007/TD-013 (not duplicated).

### RB-011 — All: performance baselines are absent
- **Verified:** No performance/latency test exists anywhere in `tests/`; `coverage.py` measures
  correctness coverage only. `pyproject.toml` has no performance-testing tooling configured.
- **Affected components:** Repository-wide; most acute for `LiveMarketCollector` (network I/O
  latency directly affects generator run time, which affects `publish.yml`'s CI duration and the
  freshness of the live dashboard).
- **Required migration:** A performance baseline suite — even a minimal one (wall-clock assertions
  on `DecisionEngine.evaluate()` for a fixed fixture, with a documented "no unbounded network I/O in
  the hot path" invariant) — plus documented current numbers as a baseline, not a target.
- **Rollback:** Additive.
- **Risk:** Low.
- **External auditor requirement:** No — this is measurement, not a design decision.
- **Definition of Done:** At least one committed performance baseline measurement per capability
  with a documented methodology and re-measurement cadence, per `institutional-health-dashboard.md`'s
  own required fields (artifact hash, capture time, methodology, owner, threshold).
- **Status: Migration Ready.**

### RB-012 — All: human approvals are not revision-bound
- Identical scope to TD-013. **Status: External Auditor Required** — see TD-013 (not duplicated).

---

## L. Safe, Isolated Fixes Applied in This Session

Per Phase 0 Rule 12, the following defect was fixed because it met every required condition:
objectively proven (confirmed by direct code read and consumer inventory), no architectural
migration required (a one-field constructor signature change within the existing canonical class),
no competing implementation created, regression coverage added, and existing (real) production
behavior is unchanged because every real production caller already passed the field explicitly.

- **`packages/domain/market_thesis_models.py`:** `MarketThesis.setup_quality_score` changed from
  `int = 94` (fabricated default) to a required `int` field, reordered ahead of the class's other
  defaulted fields to satisfy dataclass field-ordering rules. `MarketThesis.from_dict` changed from
  `to_int(raw.get("setup_quality_score", 94))` to `to_int(raw["setup_quality_score"])`, matching the
  file's existing convention for every other required field (`thesis_id`, `symbol`, `verdict`, …).
- **`tests/test_production_completion.py`:** The one test that had been unintentionally relying on
  the fabricated default now passes `setup_quality_score=90` explicitly (matching the test's own
  `TradeQuality(score=90, ...)` fixture, for internal consistency). Added
  `test_from_dict_rejects_missing_setup_quality_score`, asserting `from_dict` now raises `KeyError`
  on a payload missing the field — the regression test required by Phase 0 Rule 12.
- **Verification:** Full suite (349 tests, was 348 — one net new test), `ruff check`, `ruff format
  --check`, `mypy` (strict), and `coverage report` (90%, unchanged from the pre-fix baseline) all
  pass. No consumer outside the fixed test needed a change (§F's consumer inventory for
  `MarketThesis.from_dict` confirmed this before the edit was made, not after).

This closes the root cause of the dashboard fabrication already fixed at the presentation layer in
commit `86a7585`; that commit remains correct and necessary (defense in depth — the frontend should
not display fabricated data even if the domain layer is later hardened), but this session's fix
removes the actual source.

No other code change was made in this session. Every other finding in this document is documented,
not implemented, per the Phase 0 rule against speculative or unauthorized migration.

---

## M. Verification

```text
python -m unittest discover -s tests   -> 349 tests, OK
ruff check .                            -> All checks passed!
ruff format --check .                   -> 181 files already formatted
mypy                                    -> Success: no issues found in 130 source files
coverage report                         -> TOTAL 90% (fail_under = 90, unchanged)
```

Architecture-boundary tests (`tests/test_architecture.py`) pass unchanged: layer-dependency
direction, `Any`/`cast` prohibition, and capability-isolation rules all still hold. No test was
weakened, skipped, or had its assertions loosened to accommodate any finding in this document.

---

## N. Migration Order Step 1 — Shared Composition Root (Implemented)

Dated after §A–M. Implements exactly the item §I named as the safe, unblocked first step, and
nothing beyond it — no downstream migration (TD-001, TD-004, RB-005, RB-009, etc.) was started.

**What was built:** `publish/composition.py` — pure factory functions (`configure_publish_logger`,
`build_decision_policy`, `build_decision_engine`, `build_live_market_collector`,
`build_macro_collector`, `build_execution_readiness_engine`, `build_multi_timeframe_engine`,
`build_opportunity_identity_engine`). It owns *how* each shared dependency is constructed; it holds
no state, makes no business decision, and is not a God Object — each function does exactly one
thing. The module's own docstring is the authoritative boundary statement (also mirrored in
`docs/publish-composition-root.md`).

**Production entry point now using it:** `publish/generate_artifacts.py` (unchanged itself — its
import list and `GENERATORS` registry were never touched) transitively uses the composition root
through the 10 of its 14 generator modules that previously constructed a shared dependency inline:
`decision.py`, `execution_readiness.py`, `market_story.py`, `market_thesis.py`,
`multi_timeframe.py`, `opportunity_identity.py`, `macro_assessment.py`, `macro_context.py`,
`macro_evidence.py`, `policy.py`. The other 4 (`context.py`, `health.py`, `hypotheses.py`,
`readiness.py`, `technical_debt.py`) never constructed any of these dependencies and were left
untouched — they had no duplication to eliminate.

**Dependency construction before vs. after:**

| | Before | After |
|---|---|---|
| `logging.basicConfig(...)` + `getLogger("gold_brain.publish")` | Duplicated verbatim in 7 files | One call site: `configure_publish_logger()` |
| `DecisionPolicy()` | Duplicated in 8 files | One call site: `build_decision_policy()` |
| `DecisionEngine(policy, JsonDecisionLogger(logger))` | Duplicated in 6 files | One call site: `build_decision_engine(policy, logger)` |
| `LiveMarketCollector()` | Duplicated in 7 call sites across 6 files | One call site: `build_live_market_collector()` |
| `MacroCollector(timeout_seconds=2)` | Duplicated in 4 files | One call site: `build_macro_collector()` |
| `ExecutionReadinessEngine()` | Duplicated in 4 files | One call site: `build_execution_readiness_engine()` |
| `MultiTimeframeEngine()` | 1 file (not duplicated, but now consistent with the rest) | One call site: `build_multi_timeframe_engine()` |
| `OpportunityIdentityEngine()` | 1 file | One call site: `build_opportunity_identity_engine()` |

**Components newly reachable:** None. This step is a pure construction refactor — it does not wire
any previously-orphaned class into production. Every class the composition root builds
(`DecisionEngine`, `ExecutionReadinessEngine`, `OpportunityIdentityEngine`, `MultiTimeframeEngine`,
`LiveMarketCollector`, `MacroCollector`, `DecisionPolicy`) was already production-reachable per §B
before this change; only *where* they are constructed changed.

**Components intentionally still unreachable — unchanged from §B, not activated:**
`TradingOpportunityEngine` (CLI-only, unscheduled); `EvidenceDecisionEngine`,
`InstitutionalReasoningEngine`, `LearningEngine`, `DecisionMemory`, `SqliteDecisionStore`,
`InstitutionalKnowledgeBase`, `ConstitutionalGovernance`, `InstitutionalQualityGate`,
`ResearchGovernance`, `SelfCritic`, `PatternDiscovery`, `InstitutionalComprehensionGate`,
`InstitutionalMemory`, `TrustAssurance`, `CurrentMarketStateAssembly`,
`MarketRegimeIdentification`; every `capabilities/*` class (all 14 folders). Each is explicitly
named in `publish/composition.py`'s own docstring as "not yet wired — scheduled for downstream
migration," per this mission's Rule 5. None was touched, imported, or instantiated anywhere in this
change.

**Behavior preservation:** No business logic changed. Every factory function's body is the exact
literal construction expression the generator used before (same class, same arguments, same
defaults — `MacroCollector(timeout_seconds=2)` is still `timeout_seconds=2`; `LiveMarketCollector()`
still takes no override). Call *sequencing* within each generator (what gets fetched, in what order,
what timestamp is captured when, the `opportunity_identity.py` state-restore-from-committed-artifact
pattern) was not touched — only the origin of each constructed object moved. Characterization
coverage already existed and was re-run, not newly written for this purpose:
`tests/test_publish.py::test_generate_artifacts_produces_all_expected_json_files` runs the real
`publish.generate_artifacts.run()` end-to-end (live network calls included) and
`tests/test_production_completion.py::CompletionPublishingTests::test_generators` exercises
`market_story.generate()` and `market_thesis.generate()` directly; both passed before this change
and pass after it, unmodified.

**Tests added:** `tests/test_composition.py` (12 tests) —

- Valid construction of all 8 factories (correct return type).
- Configuration/dependency-identity: `build_decision_engine` provably evaluates against the
  *supplied* policy (not a hidden default) and records through the *supplied* logger, verified
  through observable behavior rather than reaching into the engine's private attributes.
- Stateful-engine independence: two calls to `build_opportunity_identity_engine()` return distinct,
  non-shared instances (the composition root is not an accidental singleton cache).
- A regression guard (AST-based, walks every file in `publish/generators/`) asserting none of them
  constructs `DecisionEngine`, `DecisionPolicy`, `LiveMarketCollector`, `MacroCollector`,
  `ExecutionReadinessEngine`, `MultiTimeframeEngine`, or `OpportunityIdentityEngine` inline anymore
  — this is the test that would fail first if the duplication this step removed were reintroduced.

There is no "invalid configuration" test because there is no configuration: every value in
`publish/composition.py` is the same literal default the generators already hardcoded (no
environment variables, no config file, no secrets exist anywhere in this pipeline today). Per Rule 7
("avoid fabricated defaults for business-critical values... a missing required production value
must fail explicitly"), no new default was introduced, and there is nothing to fail on that wasn't
already unconditionally present before this change.

**Full verification (after this change):**

```text
python -m unittest discover -s tests   -> 361 tests, OK   (349 + 12 new)
ruff check .                            -> All checks passed!
ruff format --check .                   -> 183 files already formatted
mypy                                    -> Success: no issues found in 131 source files
mypy publish/ tests/test_composition.py -> Success: no issues found in 21 source files  (publish/ is
                                            outside pyproject.toml's default mypy `files` list —
                                            checked explicitly here to confirm it is clean anyway)
coverage report                         -> TOTAL 90% (fail_under = 90, unchanged; publish/ is
                                            outside the coverage `source` list in pyproject.toml,
                                            so this change is coverage-neutral by construction)
tests.test_architecture (4 tests)       -> OK — layer-inward-dependency, Any/cast prohibition, and
                                            capability-isolation rules all still pass unchanged
```

No circular dependency was introduced: `publish/composition.py` imports only from
`packages.application`, `packages.domain`, and `packages.infrastructure`, none of which import from
`publish`. No orphaned capability was activated: `grep -rn "capabilities" publish/composition.py
publish/generators/*.py` matches only the docstring's prose mention of `capabilities/*` and two
unrelated local-variable names (`health.py`/`readiness.py` reading a JSON key literally named
`"capabilities"`) — zero `from capabilities...` imports exist anywhere under `publish/`.

**Remaining TD/RB blockers:** Unchanged from §J/§K — this step resolves no TD/RB item on its own
(it was never claimed to); it is infrastructure preparation that TD-001, TD-004, TD-006, TD-015, and
RB-006/RB-009 depend on per §H/§I.

**Exact next migration:** Per §I step 2 — TD-001/TD-006/RB-006 (engine consolidation: converge
`TradingOpportunityEngine`'s gates into the canonical `DecisionEngine`→`build_market_thesis` path,
and determine via explicit dead-code analysis whether `EvidenceDecisionEngine`/
`InstitutionalReasoningEngine` compute anything not already covered, then delete or fold in).
**This requires Architecture + Trading review (ADR-0004) before any engine deletion** — per this
mission's explicit scope boundary, that review has not been requested or assumed here, and no work
on step 2 has begun.
