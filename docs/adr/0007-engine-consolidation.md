# ADR-0007: Engine Consolidation (TD-001 / TD-006 / RB-006)

> **Numbering note:** The Phase 0 migration order and this mission's brief both refer to this work
> as "ADR-0004." `docs/adr/0004-institutional-quality-gate.md` already occupies ADR-0004 in this
> repository's ADR sequence. Rather than create a second, ambiguous ADR-0004, this proposal is filed
> as **ADR-0007**, the next unused number in the existing `docs/adr/000N-slug.md` sequence (0001
> through 0006 are taken). The companion review package is
> `docs/ADR-0007-ENGINE-CONSOLIDATION-REVIEW-PACKAGE.md`. Every cross-reference elsewhere in this
> repository that says "ADR-0004" for engine consolidation should be read as this document.

## 1. Status

**PROPOSED — Pending Architecture Review and Trading Review.** Unlike ADR-0001 through ADR-0006,
which record settled decisions, §13 ("Decision") below is explicitly not final. This ADR exists to
make the engine-consolidation migration *reviewable*, not to pre-empt the review. No engine has been
deleted, no production behavior has changed, and no consumer has been migrated as part of producing
this document — see `docs/PHASE_0_MIGRATION_READINESS.md` §N for the one prior, unrelated,
already-shipped change (the shared composition root) this ADR builds on.

## 2. Context

`docs/PHASE_0_MIGRATION_READINESS.md` (§H, §I) named engine consolidation — TD-001, TD-006, RB-006 —
as Migration Order step 2, explicitly gated on "Architecture + Trading review (ADR-0004) before any
engine deletion." This document is that gate's evidence package: a complete inventory of every
engine-shaped class touching Decision/Market Thesis/Trade Quality/Opportunity/Policy/Research, the
real production call graph, an objective classification of what genuinely overlaps versus what only
shares a name, a formula-level comparison of every "trade quality"-shaped calculation in the
repository, an exhaustive consumer inventory, a canonical-ownership proposal derived from actual
production usage (not assumption), a target architecture, a parity-test plan, and a staged migration
plan — with every question this document cannot answer from repository evidence alone marked
`PENDING REVIEW` rather than guessed.

## 3. Current Architecture

```text
Production Entry Point         publish/generate_artifacts.py
        |
        v
Composition Root               publish/composition.py   (docs/PHASE_0_MIGRATION_READINESS.md §N)
        |
        v
Application Engines            packages/application/{decision_engine,execution_readiness_engine,
                                multi_timeframe_engine,opportunity_identity_engine}.py
        |                       + packages/application/trade_quality.py (build_market_thesis,
        |                         derive_trade_quality — the composition function, not a class)
        v
Domain / Infrastructure         packages/domain/*, packages/infrastructure/{live_collector,
                                macro_collectors,smc_detector,...}.py
        v
Persistence / Artifact          docs/artifacts/*.json (committed), var/*.jsonl (unused in this path)
```

Running in parallel, reachable only from `apps/trading_cli/main.py` (not CI-scheduled — confirmed in
`docs/PHASE_0_MIGRATION_READINESS.md` §B, re-confirmed in §6 below):

```text
apps/trading_cli/main.py → TradingOpportunityEngine → packages/domain/trading_models.py
                                                      → var/trading_opportunities.jsonl (JSONL, durable)
```

Fully orphaned (zero non-test consumers, re-confirmed in §6):

```text
EvidenceDecisionEngine  → packages/domain/evidence_models.py  → JsonLinesEvidenceDecisionAudit (durable, unwired)
InstitutionalReasoningEngine → (composes EvidenceDecisionEngine via an EvidenceEvaluator port)
                              → packages/domain/reasoning_models.py → JsonLinesReasoningAudit (durable, unwired)
capabilities/decision.OfficialDecision → (validates ReasoningDecision + critique + trust + state + comprehension)
```

## 4. Problem

Six classes compute or transport a decision-shaped or quality-shaped output over three structurally
different input models, using three independent formulas, three independent verdict vocabularies,
and inconsistent persistence guarantees. `docs/technical-debt-register.md` (TD-001, TD-003, TD-006)
and `docs/capability-blocker-register.md` (RB-006) already flag this at the ownership level; this
document adds the missing engineering detail — exactly which formulas diverge, by how much, on what
inputs, and who actually consumes each one today — that a deletion decision requires.

## 5. Engine Inventory

Every class with a `.evaluate(...)`-shaped public API that produces a decision-, thesis-, or
quality-shaped output, found by full-repository search (not limited to names already in the
registers):

| Engine | File | Public API | Constructor deps | Input | Output | Side effects / persistence | Production reachable |
|---|---|---|---|---|---|---|---|
| `DecisionEngine` | `packages/application/decision_engine.py` | `evaluate(observation, evaluated_at) -> Decision` | `DecisionPolicy`, `DecisionLogger` | `MarketObservation` | `Decision` (verdict, score 0.0–1.0, reasons/conflicts/missing) | `DecisionLogger.record()` — **verified in this session to be a silent no-op in production**: `publish/composition.py`'s `configure_publish_logger()` sets `logging.basicConfig(level=WARNING)`, and `JsonDecisionLogger.record()` calls `logger.info(...)`; `logging.getLogger("gold_brain.publish").isEnabledFor(logging.INFO)` is `False` under that configuration (confirmed by direct interpreter check, §6). No exception is raised; the record call succeeds and produces no observable output. | **Yes** — `apps/decision_cli`, `gold_brain.engine` facade, `publish/composition.build_decision_engine` (6 generators) |
| `build_market_thesis` / `derive_trade_quality` | `packages/application/trade_quality.py` | functions, not a class | none (pure functions over `Decision`/`MarketObservation`) | `Decision` + `MarketObservation` | `TradeQuality`, `MarketThesis` | none (pure) | **Yes** — 4 generators |
| `ExecutionReadinessEngine` | `packages/application/execution_readiness_engine.py` | `evaluate(observation, verdict, setup_quality_score, macro_assessment, evaluated_at) -> ExecutionReadiness` | none (stateless) | `MarketObservation` + upstream `Decision`/`TradeQuality` outputs | `ExecutionReadiness` (readiness_score 0–100, distinct concept from trade quality — entry timing, not setup quality) | none | **Yes** — 4 generators |
| `MultiTimeframeEngine` | `packages/application/multi_timeframe_engine.py` | `evaluate_multi_timeframe(htf_thesis, ltf_obs, readiness, at) -> MultiTimeframeThesis` | none (stateless) | `MarketThesis` + LTF `MarketObservation` | `MultiTimeframeThesis` (cascades `setup_quality_score` through unchanged — does not recompute it) | none | **Yes** — 1 generator |
| `OpportunityIdentityEngine` | `packages/application/opportunity_identity_engine.py` | `evaluate_opportunity(observation, thesis, readiness, at)`, `restore_state(...)`, `snapshot_state()` | none (stateful — current/previous opportunity, counter, sweep signature) | `MarketObservation` + `MarketThesis` + `ExecutionReadiness` | `OpportunityIdentity` × 2 (current, previous) — copies `thesis.setup_quality_score`, does not recompute it | none directly; the *generator* (`opportunity_identity.py`) persists state via the committed `opportunity_identity.json` artifact itself | **Yes** — 1 generator |
| `TradingOpportunityEngine` | `packages/application/trading_engine.py` | `evaluate(observation, evaluated_at) -> TradingDecision` | `TradingPolicy`, `TradingDecisionLogger`, `OpportunityRepository` | `TradingObservation` (macro + 3 horizon biases + dealing range + SMC + momentum + news — a materially larger evidence surface than `MarketObservation`) | `TradingDecision` (trade_quality 0–100 int, `OpportunityExecutionStatus`) | `TradingDecisionLogger.record()` + `OpportunityRepository.append()` → `JsonLinesOpportunityRepository` writes `var/trading_opportunities.jsonl` (durable, and — unlike `DecisionEngine`'s logger — actually reachable at its configured level since `apps/trading_cli/main.py` calls `logging.basicConfig(level=logging.INFO, ...)`, not WARNING) | Reachable, **not production-composed**: only `apps/trading_cli/main.py`, which no CI workflow invokes |
| `EvidenceDecisionEngine` | `packages/application/evidence_engine.py` | `evaluate(evidence, evaluated_at) -> EvidenceDecision` | `EvidencePolicy`, `EvidenceDecisionAudit` | `tuple[Evidence, ...]` (kind/direction/strength/reliability/importance/historical_performance/confidence, TTL-decayed) | `EvidenceDecision` (trade_quality 0–100 int, `Recommendation` — 4-value vocabulary) | `EvidenceDecisionAudit.record()` → `JsonLinesEvidenceDecisionAudit`, durable, tested, **never instantiated outside tests** | **No** — zero non-test consumers |
| `InstitutionalReasoningEngine` | `packages/application/reasoning_engine.py` | `evaluate(reasoning_input, evaluated_at) -> ReasoningDecision` | `ReasoningPolicy`, `EvidenceEvaluator` (port — structurally satisfied by `EvidenceDecisionEngine`), `ReasoningAudit` | `ReasoningInput` (wraps `Evidence` tuple + knowledge + historical context + market state) | `ReasoningDecision` — **composes, does not recompute**, `evidence_decision.trade_quality` from its injected `EvidenceEvaluator`; adds a `reliability` score on top | `ReasoningAudit.append_path()`/`append_mistake()` → `JsonLinesReasoningAudit`, durable, tested, **never instantiated outside tests** | **No** — zero non-test consumers |
| `capabilities.decision.OfficialDecision` (not an engine — a validation gate) | `capabilities/decision/capability.py` | `DecisionCapability.decide(...) -> OfficialDecision` | `CapabilityTelemetry` | `ReasoningDecision` + `DecisionExplanation` + `DecisionCritique` + `RecommendationTrust` + `CurrentMarketState` + `ReasoningComprehensionReview` (six preconditions) | `OfficialDecision` — **copies** `reasoning.trade_quality`/`reasoning.reliability` verbatim; performs no calculation | telemetry only | **No** — zero non-test consumers; also depends transitively on 5 other orphaned capabilities |
| `LearningEngine` | `packages/application/learning_engine.py` | `evaluate_outcome(...)`-shaped (learning recommendations, not a decision) | `LearningPolicy`, learning ports | historical outcome records | `LearningRecommendation` — explicitly non-authoritative by design (README: "can propose — but never deploy — changes") | in-memory only (TD-007) | **No** — zero non-test consumers; **not** a decision-duplication candidate — different responsibility entirely, included here only because it appeared in the initial class search |

**Test coverage** (from `coverage report`, unchanged by this document): `decision_engine.py` 98%,
`trade_quality.py` (derive/build functions) 98%, `execution_readiness_engine.py` 98%,
`multi_timeframe_engine.py` 100%, `opportunity_identity_engine.py` 92%, `trading_engine.py` 90%,
`evidence_engine.py` 98%, `reasoning_engine.py` 96%, `capabilities/decision/capability.py` — part of
`capabilities/decision` package coverage, exercised only by `test_capabilities.py`. Every engine in
this table is well-tested in isolation; reachability, not test coverage, is what separates them.

**Classification** (production / test / legacy / orphaned / duplicate / canonical):

- **Canonical + production:** `DecisionEngine` → `build_market_thesis`/`derive_trade_quality`. This
  is the only decision path with a real, CI-scheduled, non-test caller.
- **Production, different responsibility (not a duplication candidate):** `ExecutionReadinessEngine`,
  `MultiTimeframeEngine`, `OpportunityIdentityEngine` — each consumes the canonical thesis output
  rather than recomputing trade quality; see §7 classification C/E below.
- **Reachable, not production-composed:** `TradingOpportunityEngine` — a fully-implemented,
  well-tested, *different* evaluation model than `DecisionEngine`, sitting behind an entry point no
  scheduler invokes.
- **Orphaned, implementation-complete:** `EvidenceDecisionEngine`, `InstitutionalReasoningEngine`,
  `capabilities.decision.OfficialDecision`, `LearningEngine`. Not "legacy" in the sense of superseded
  — they were never wired into any composition root to begin with (confirmed in
  `docs/PHASE_0_MIGRATION_READINESS.md` §B).
- **Not a duplicate:** `LearningEngine` — different business responsibility (research/learning
  recommendation, explicitly non-authoritative), included in this inventory only because the
  investigation scope required searching for every Decision/Thesis/Quality/Opportunity/Policy-named
  class, not because it competes with `DecisionEngine`.

## 6. Production Call Graph

Re-traced from `publish/generate_artifacts.py` in this session (not assumed from Phase 0 — verified
fresh against the current tree at commit `cd5c466`):

```text
publish/generate_artifacts.py
  → GENERATORS registry (14 entries, unchanged since §N)
  → publish/generators/{decision,execution_readiness,market_story,market_thesis,
      multi_timeframe,opportunity_identity,macro_assessment,macro_context,
      macro_evidence,policy}.py
      → publish/composition.py
          → build_decision_engine(policy, logger) → packages.application.DecisionEngine
          → build_execution_readiness_engine()    → packages.application.execution_readiness_engine.ExecutionReadinessEngine
          → build_multi_timeframe_engine()        → packages.application.multi_timeframe_engine.MultiTimeframeEngine
          → build_opportunity_identity_engine()   → packages.application.opportunity_identity_engine.OpportunityIdentityEngine
          → build_live_market_collector()         → packages.infrastructure.live_collector.LiveMarketCollector
          → build_macro_collector()               → packages.infrastructure.macro_collectors.MacroCollector
      → packages.application.trade_quality.{build_market_thesis, derive_trade_quality}  (called directly, not via composition.py — pure functions, no construction needed)
  → docs/artifacts/*.json  (committed output; consumed live by docs/app.js)
```

Confirmed by direct grep in this session (§ methodology matches
`docs/PHASE_0_MIGRATION_READINESS.md` §F/§B, re-run rather than assumed):

```text
grep -rl "TradingOpportunityEngine"       apps publish gold_brain  → apps/trading_cli/main.py only
grep -rl "EvidenceDecisionEngine"         apps publish gold_brain  → none (outside prose docstrings)
grep -rl "InstitutionalReasoningEngine"   apps publish gold_brain  → none (outside prose docstrings)
grep -rl "OfficialDecision"               apps publish gold_brain  → none
```

No workflow under `.github/workflows/` invokes `apps/trading_cli` or `apps/decision_cli` — only
`publish/generate_artifacts.py` (`publish.yml`, `deploy_interserver.yml`). This is unchanged from
Phase 0 and is the load-bearing fact for the entire canonical-ownership proposal in §10: "which
engine is authoritative" is not a matter of which is best-designed, it is a matter of which one a
scheduler actually runs.

**Verified logging-level finding (new in this session):** `DecisionEngine`'s only audit mechanism
(`JsonDecisionLogger.record()`, called via the `DecisionLogger` port) is a structured `logger.info()`
call. `publish/composition.py::configure_publish_logger()` configures the root logger at `WARNING`.
Direct interpreter verification: `logging.getLogger("gold_brain.publish").isEnabledFor(logging.INFO)`
returns `False` under that configuration. The call does not raise (so `DecisionEngine.evaluate()`
completes normally and `Decision` objects are still returned and written to `docs/artifacts/*.json`
correctly) — but the structured per-decision audit log line itself is silently swallowed by the
standard library's level filter in every scheduled production run today. This is a genuine
production-behavior finding, **not fixed in this session** (a logging-level change is a production
behavior change, out of this mission's Implementation Allowance) — flagged as Architecture Question
AQ-6 in the review package and as a candidate item for whichever migration step touches
`DecisionEngine`'s composition next.

## 7. Duplication Analysis

For every pair of engines that appear to overlap on "produce a decision-shaped or quality-shaped
output," classified per the mission's five categories:

| Pair | Classification | Basis |
|---|---|---|
| `DecisionEngine` vs. `TradingOpportunityEngine` | **C — different versions of the same business philosophy, not interchangeable code.** Both implement the same underlying trading-constitution idea (SMC structure + location + liquidity as mandatory gates, fail-closed to WAIT), but over different evidence surfaces (`MarketObservation`'s 3 mandatory gates vs. `TradingObservation`'s 9-component, macro+3-horizon+news-aware model) with different scoring granularity (§8) and different verdict vocabularies (§8). Neither is a strict superset of the other: `TradingOpportunityEngine` evaluates macro/news/multi-horizon evidence `DecisionEngine` has no field for; `DecisionEngine`'s SMC gates are a strict subset of what `TradingOpportunityEngine` checks under its own field names. | Formula comparison in §8; both engines' `__init__.py`/domain models read directly. |
| `DecisionEngine` vs. `EvidenceDecisionEngine` | **C.** Same relationship as above but more acute: `EvidenceDecisionEngine` operates on an abstract `Evidence` kind/direction/weight model (geometric-mean weighted, TTL-decayed) that has no structural relationship to `MarketObservation`'s concrete SMC fields at all. A `MarketObservation` cannot be mechanically converted to a `tuple[Evidence, ...]` without a policy decision about how to map, e.g., "confirmed break of structure" to an `Evidence.strength`/`reliability`/`importance` tuple — that mapping does not exist in the repository and this document does not invent one (see §8's explicit refusal to fabricate a cross-formula equivalence). | `packages/domain/evidence_models.py` vs. `packages/domain/models.py`. |
| `TradingOpportunityEngine` vs. `EvidenceDecisionEngine` | **B — different responsibilities incorrectly sharing the word "trade quality."** `TradingOpportunityEngine` produces an execution-permission signal for a specific `TradingObservation`. `EvidenceDecisionEngine` produces an abstention/attention signal (`Recommendation.NO_OPINION` is a state `TradingOpportunityEngine` cannot express at all) from a general evidence ledger. Their `required_execution_kinds`/evidence categories overlap substantially (macro, bias, location, liquidity sweep, MACD, reversal candle — 6 of `TradingPolicy`'s 9 components map by name to `EvidencePolicy.required_execution_kinds`), which is *why* they read as duplicative, but the computations and even the questions they answer differ. | §8. |
| `EvidenceDecisionEngine` vs. `InstitutionalReasoningEngine` | **E — complementary, correctly layered, not a duplication at all.** `InstitutionalReasoningEngine` explicitly composes `EvidenceDecisionEngine` through the `EvidenceEvaluator` port (`packages/application/ports.py`) and reuses its `trade_quality`/`recommendation` rather than recomputing them, adding a `reliability` score from knowledge-context weighting on top. This is the one pair in this table that is already architecturally correct — its only defect is that *both* halves are equally orphaned (§5, §6), not that they compete. | `packages/application/reasoning_engine.py` line 60: `self._evidence_evaluator.evaluate(...)`. |
| `InstitutionalReasoningEngine` vs. `capabilities.decision.OfficialDecision` | **E — correctly layered.** `OfficialDecision` copies `reasoning.trade_quality`/`reasoning.reliability` verbatim and adds a publication/authorization gate (critique, trust, market-state currency, comprehension review) rather than computing anything new. | `capabilities/decision/capability.py` lines 96–97. |
| `ExecutionReadinessEngine` / `MultiTimeframeEngine` / `OpportunityIdentityEngine` vs. anything | **E — complementary by construction, not duplication candidates.** All three take `setup_quality_score`/`MarketThesis` as an *input parameter* and never recompute it (verified: no `score +=`-shaped accumulation touching trade quality exists in any of the three files). They compute genuinely different concepts (entry timing, HTF/LTF cascade, opportunity lifecycle identity). Excluded from the consolidation decision entirely — there is nothing to consolidate. | §5 table; direct read of all three files in this session. |

**Net finding:** exactly one *genuine* multi-way duplication exists at the calculation level — three
independent "trade quality" formulas (`DecisionEngine`→`derive_trade_quality`,
`TradingOpportunityEngine`, `EvidenceDecisionEngine`) — and it is a category-C duplication (different
versions of the same underlying philosophy over different evidence surfaces), not a category-A
"literally the same code, twice." That distinction matters for §13: a category-A duplicate can be
deleted once a parity test passes; a category-C duplicate requires a canonical-ownership *decision*
about which evidence surface (and therefore which formula) is authoritative before any deletion,
because deleting either one changes what evidence the system requires to form an opinion — which is
a trading-policy question this document cannot answer, hence TQ-1 through TQ-4 in the review package.

## 8. Formula / Behavior Comparison

All three "trade quality" formulas, compared on their own terms (no synthetic cross-engine mapping
was constructed — see the refusal above):

| | `derive_trade_quality` (canonical, `DecisionEngine`-fed) | `TradingOpportunityEngine` (inline) | `EvidenceDecisionEngine` |
|---|---|---|---|
| Formula | `round(decision.score * 100)`; `decision.score` = sum of 3 weights (`structure_weight=0.40 + location_weight=0.30 + liquidity_weight=0.30`) each awarded all-or-nothing | Sum of 9 point components (`macro=15, execution_bias=15, cross_horizon_alignment=5, location=15, liquidity_sweep=10, nearby_liquidity=5, macd=10, reversal_candle=15, optional_smc=10` = 100), with `optional_smc` partially awarded proportionally (0–3 of 3 confirmations), plus subtractive penalties (`macro_contradiction_penalty_points=5` per contradiction, `news_confidence_penalty_points=10 × news.confidence` per reducing-confidence news item), clamped to `[0, 100]` | `round(confidence * completeness)`; `confidence` = `round(abs(buy_weight-sell_weight)/directional_weight*100)` from geometric-mean-weighted (`prod(strength,reliability,importance,historical_performance,confidence)**(1/5)`), TTL-decayed evidence; `completeness` = fraction of `EvidencePolicy.required_execution_kinds` (6 kinds) present at reliable weight |
| Mandatory gate before any score | Structure + dealing range + liquidity all present, else hard `WAIT` at score `0.0` | Execution-horizon bias present and not `WAIT`; all 3 horizons present | Directional weight ≥ `0.25`, confidence ≥ `60`, MACRO+MARKET_BIAS present, else `NO_OPINION` (a 4th state the other two formulas cannot express) |
| Threshold for a directional verdict | `attention_threshold = 0.75` (on the 0.0–1.0 score) | `minimum_trade_quality = 75` (on the 0–100 score) — numerically the same cutoff, different formula feeding it | `minimum_trade_quality = 75` (`EvidencePolicy`) — same cutoff again |
| Verdict vocabulary | `DecisionVerdict`: `BUY / SELL / WAIT` (3) | `OpportunityExecutionStatus`: `SEARCH_BUY_SETUPS / SEARCH_SELL_SETUPS / WAIT / PAUSED` (4) | `Recommendation`: `BUY_SETUPS_ONLY / SELL_SETUPS_ONLY / WAIT / NO_OPINION` (4) |
| Missing-data behavior | Missing structure/range/liquidity → `WAIT`, score `0.0`, itemized in `missing_evidence` | Missing evidence appended to `missing`; some missing items (`No optional CHoCH...`, `No context-relevant prior liquidity level...`) are explicitly *non-blocking* — a distinction the other two formulas don't make | Missing required-kind evidence → itemized in `missing`, contributes to `completeness < 1.0`, can still yield a score `> 0` unlike `DecisionEngine`'s all-or-nothing gate |
| News handling | None — `DecisionEngine` has no news input at all | Explicit: can force `PAUSED` or `WAIT` regardless of score (`forced_status`), or apply a confidence-proportional penalty | None — `Evidence` items carry a generic `forces_wait: bool`, not a news-specific model |
| Extreme-case agreement (existing fixtures, not invented) | Full alignment: `decision.score = 1.0` → quality `100` (`tests/test_engine.py::test_bullish_confluence_justifies_searching_for_buy_setup`) | Full alignment: `trade_quality = 100` (`tests/test_trading_engine.py::test_full_buy_evidence_grants_setup_search_only`) | Full alignment: `trade_quality = 100` (`tests/test_evidence_engine.py::test_complete_buy_evidence_returns_buy_setups_only`) |
| Missing-mandatory-evidence agreement | `score = 0.0` (`test_missing_mandatory_evidence_fails_closed`) | (no single-fixture equivalent found; multiple mandatory-missing tests each force `WAIT` without asserting a specific `trade_quality` value at zero evidence) | `NO_OPINION` (not comparable to `0` — a 4th state) |
| Partial-evidence divergence (illustrative, from each engine's own existing fixtures — not a cross-mapped scenario) | Wrong location only: `score = 0.7` (structure+liquidity pass, location fails: `0.40+0.30`) | Missing optional SMC + no nearby liquidity level: `trade_quality = 85` | Conflicting evidence: `trade_quality = 71` |

**Conclusion — stated plainly and without rounding to "they're basically the same":** all three
formulas agree exactly at both extremes evaluated in existing tests (perfect alignment → 100).
Mid-range, they are not comparable on a single fixture because they consume structurally different
inputs (`MarketObservation` vs. `TradingObservation` vs. `tuple[Evidence, ...]`) — the partial-case
numbers above (0.7 / 85 / 71) are each engine's own documented behavior on its own fixture, presented
side by side for context, not evidence of equivalence or of a quantified gap. Any claim that these
three formulas "produce the same trade quality" or "produce different trade quality by X points" for
the *same underlying market situation* would require defining a formal mapping between
`MarketObservation`, `TradingObservation`, and `Evidence` tuples that does not exist in this
repository today — inventing one is a trading-policy decision, explicitly out of this document's
authority (see TQ-1 in the review package).

## 9. Consumer Inventory

Exhaustive, re-run in this session (not copied from Phase 0) against `apps/`, `publish/`,
`packages/`, `capabilities/`, `gold_brain/`, `tests/`:

| Engine | Consumer | Current API used | Migration risk | Parity requirement |
|---|---|---|---|---|
| `DecisionEngine` | `apps/decision_cli/main.py` | `DecisionEngine(DecisionPolicy(), JsonDecisionLogger(logger)).evaluate(obs, at)` | Low — single call site, thin CLI | None if left as-is; any change flows through `decision_to_json` contract test coverage already in `test_trading_cli_integration.py`-adjacent CLI tests |
| `DecisionEngine` | `gold_brain/engine.py` (compatibility facade) | `DecisionEngine(policy=None, now=...)` compatibility constructor kwargs (ADR-0005 Compatibility Adapter) | Low — facade explicitly frozen per ADR-0005 ("Compatibility Adapters cannot contain new business logic") | Facade behavior is already characterized by `tests/test_engine.py::test_compatibility_adapter_constructor_and_now_keyword_remain_supported` |
| `DecisionEngine` | `publish/composition.py::build_decision_engine` → 6 generators | Factory-constructed, see §N | Low — single construction point after this session's composition-root work | `tests/test_composition.py` (12 tests) already guards this wiring |
| `build_market_thesis`/`derive_trade_quality` | 4 generators | Direct function calls | Low — pure functions, already the canonical path | `tests/test_trade_quality.py` |
| `TradingOpportunityEngine` | `apps/trading_cli/main.py` | `TradingOpportunityEngine(TradingPolicy(), JsonTradingDecisionLogger(logger), JsonLinesOpportunityRepository(ledger)).evaluate(obs, at)` | **Medium** — this is the only real consumer, but it is a full CLI with its own durable ledger (`var/trading_opportunities.jsonl`) and its own contract tests (`tests/test_trading_cli_integration.py`); any consolidation must either preserve this CLI's contract unchanged or explicitly migrate it | Full `TradingDecision` JSON contract parity (`trading_observation_from_json`/`trading_decision_to_json`) required before any change to what backs it |
| `EvidenceDecisionEngine` | none (production) | — | None today | N/A until a consumer exists |
| `InstitutionalReasoningEngine` | none (production) | — | None today | N/A until a consumer exists |
| `capabilities.decision.OfficialDecision` | none (production) | — | None today | N/A until a consumer exists |
| `LearningEngine` | none (production) | — | None today; excluded from consolidation scope (§5) | N/A |

No fixtures, mocks, scripts, or workflow YAML reference any of these engines outside what's listed
above and their own unit test files (`tests/test_engine.py`, `tests/test_trading_engine.py`,
`tests/test_evidence_engine.py`, `tests/test_reasoning_engine.py`, `tests/test_capabilities.py`) —
verified by `grep -rn` across `.github/workflows/*.yml` and `tests/*.py` for each engine's class
name.

## 10. Canonical Ownership Proposal

Derived from §6 (actual production usage), not assumed:

| Responsibility | Proposed canonical owner | Basis |
|---|---|---|
| Market Thesis | `MarketThesis` (domain) via `build_market_thesis()` | Already the sole reachable production output shape; matches ADR-0002 exactly; no dispute. |
| Decision (the SMC-gate evaluation feeding Market Thesis) | `DecisionEngine` | The only decision-computing class with a real, CI-scheduled caller. |
| Trade Quality | `derive_trade_quality()` | Same basis — it is the formula actually feeding the artifacts real users see. |
| Opportunity (identity/lifecycle) | `OpportunityIdentityEngine` | Sole implementation; no competitor exists (§5, §7). |
| Execution Readiness | `ExecutionReadinessEngine` | Sole implementation; no competitor exists. |
| Policy (the `DecisionPolicy` configuration object specifically) | `DecisionPolicy` (domain) | Feeds the canonical `DecisionEngine`; `TradingPolicy`/`EvidencePolicy`/`ReasoningPolicy` remain scoped to their own engines and are not claimed as duplicates of `DecisionPolicy` — they configure a materially different evidence model each (§8), so "one canonical Policy" is **not** proposed here. |
| **Trading-constitution evaluation** (the broader macro+3-horizon+news+SMC evidence model `TradingOpportunityEngine` implements) | **PENDING ARCHITECTURE/TRADING REVIEW** — see AQ-1/TQ-1 | Cannot be derived from production usage alone: `TradingOpportunityEngine` has *zero* scheduled production traffic today, so "actual usage" gives no signal here, unlike every other row. The two live options are (a) `TradingOpportunityEngine`'s richer evidence model is the intended eventual canonical path and `DecisionEngine` is the interim/simpler one, or (b) `DecisionEngine`'s path is canonical and `TradingOpportunityEngine` is a superseded experiment that was never fully cut over. Repository evidence supports either reading equally (see §11's two target-architecture options) — this is a trading-domain call, not an engineering one. |
| **Research/Evidence evaluation** (`EvidenceDecisionEngine`/`InstitutionalReasoningEngine`/`OfficialDecision` chain) | **PENDING ARCHITECTURE REVIEW** — see AQ-2 | Fully implemented, fully tested, architecturally self-consistent (§7's "E" classification), and durably persistable once wired — but has never had a consumer. Whether this chain is (a) the intended future canonical path per the capability-ownership ADRs (ADR-0001/0002 describe exactly this Evidence→Reasoning→Decision shape) that `DecisionEngine` should eventually be replaced by, or (b) an earlier design iteration that the simpler `DecisionEngine` path superseded, cannot be determined from usage (there is none) or from the ADRs (ADR-0002 names `MarketThesis` as canonical but doesn't say which *calculation path* produces it). |

## 11. Target Architecture

Two structurally different target proposals follow from the two unresolved ownership questions in
§10. Neither is implemented; both are shown so Architecture Review can pick a direction rather than
have one assumed.

**Current (as of this ADR):**

```text
publish/generate_artifacts.py → composition root → DecisionEngine → build_market_thesis → artifacts
apps/trading_cli               (separate root)   → TradingOpportunityEngine → var/trading_opportunities.jsonl  [unscheduled]
(nothing)                                        → EvidenceDecisionEngine → InstitutionalReasoningEngine → OfficialDecision  [orphaned]
```

**Target A — `DecisionEngine` path is canonical; retire the other two as public paths.**

```text
Every entry point → shared composition root → DecisionEngine → build_market_thesis → MarketThesis
                                                                                     → artifacts / presentation
TradingOpportunityEngine's evidence surface (macro, 3-horizon bias, news) is either:
  (a) folded into DecisionEngine/DecisionPolicy as optional evidence inputs, with a parity-proven
      equivalence for the subset DecisionEngine already covers, or
  (b) retired entirely if Trading Review determines its evidence surface was an abandoned direction.
EvidenceDecisionEngine/InstitutionalReasoningEngine/OfficialDecision become internal implementation
details of the Evidence/Reasoning/Decision capabilities (per concept-ownership.md's existing adapter
map) or are deleted if Architecture Review determines they were superseded, not merely unwired.
```

**Target B — `TradingOpportunityEngine`'s evidence model is canonical; `DecisionEngine` becomes the
Compatibility Adapter.**

```text
Every entry point → shared composition root → TradingOpportunityEngine-equivalent evaluation
                                              → MarketThesis (re-derived from the richer evidence
                                                model; requires a new build_market_thesis variant
                                                that accepts TradingObservation-shaped input)
DecisionEngine remains only as the gold_brain compatibility facade's backing implementation, per
ADR-0005, frozen and never gaining new business logic.
EvidenceDecisionEngine/InstitutionalReasoningEngine/OfficialDecision status unchanged from Target A —
this axis is independent of the Target A/B choice.
```

Both targets share: one canonical composition root (already built, §N), no circular dependencies, no
domain→infrastructure leakage (already enforced by `tests/test_architecture.py` and unaffected by
either target), and no production dependency on the still-orphaned `capabilities/*` layer until a
separate migration (RB-009, per `docs/PHASE_0_MIGRATION_READINESS.md` §I step 5) gives it a reason
to be wired.

## 12. Alternatives Considered

1. **Keep all engines as permanently separate, independently-scheduled paths.** Rejected as a
   *default* (not necessarily as a final answer) — it does not resolve TD-001/TD-003's core problem,
   that "trade quality" means three different numbers depending on which unscheduled code path
   computed it, which is a standing risk if any of the orphaned paths is ever wired up without this
   document's evidence in hand.
2. **Delete `TradingOpportunityEngine`/`EvidenceDecisionEngine`/`InstitutionalReasoningEngine`
   immediately since they have zero production consumers.** Rejected — Phase 0 Rule 6 requires
   explicit dead-code analysis, not assumption, before deletion, and §10/§11 show the ownership
   question these three engines raise cannot be resolved from repository evidence alone. Deleting a
   fully-implemented, well-tested, richer evidence model on the grounds that nothing calls it yet
   would risk exactly the "delete legacy implementations before consumer inventory" mistake this
   mission's rules forbid — except inverted: here the risk is deleting the *possibly-intended-future-
   canonical* implementation because it's temporarily unscheduled.
3. **Merge all formulas into one super-formula that satisfies every engine's evidence surface.**
   Rejected — this is the "parallel implementation" / "rewrite the production algorithm" failure mode
   this mission explicitly forbids; a merged formula is a new, fourth formula, not a consolidation.

## 13. Decision

**PENDING.** This ADR does not select Target A or Target B, does not resolve the
`TradingOpportunityEngine` or `EvidenceDecisionEngine`/`InstitutionalReasoningEngine` ownership
questions, and authorizes no deletion. §14–§18 below describe how *either* target would be executed
safely once Architecture Review and Trading Review answer the questions in the companion review
package — they are migration mechanics, not a pre-selection of the outcome.

## 14. Migration Strategy (mechanics, independent of Target A/B; to run only after §13 is resolved)

1. **Step 1 — Canonical formula/vocabulary decision.** Architecture + Trading Review answer AQ-1/
   TQ-1 through TQ-4 (review package). Output: a signed decision recorded as an amendment to this
   ADR, selecting Target A, Target B, or a named third option. *Files affected: none. Consumers
   migrated: none.*
2. **Step 2 — Parity test authorship.** Once a target is selected, write the specific parity tests
   named in §15 for that target (this ADR pre-specifies the *shape* of those tests now so Step 2 is
   mechanical, not exploratory). *Files affected: new test files only. Consumers migrated: none.*
3. **Step 3 — Adapter-based cutover.** Introduce the target composition without deleting the
   non-canonical path(s) yet — e.g., under Target A, `TradingOpportunityEngine`'s evidence surface
   gets folded into `DecisionPolicy`/`DecisionEngine` behind a feature-flag-free but additive change
   (new optional fields, not a replaced signature), so `apps/trading_cli` keeps working unchanged
   throughout. *Files affected: `packages/domain/policy.py`, `packages/application/decision_engine.py`
   (Target A) or `packages/application/trade_quality.py` (Target B), plus the composition root.
   Consumers migrated: none yet — this step is additive.*
4. **Step 4 — Consumer migration.** Point `apps/trading_cli/main.py` (and any other consumer named
   in §9) at the now-canonical path. *Files affected: the consumer's `main.py`. Consumers migrated:
   all consumers of the non-canonical engine, one at a time, each verified against its own existing
   contract tests before and after.*
5. **Step 5 — Deletion.** Only after §14's own deletion criteria (§18) are all met for the specific
   non-canonical engine(s) selected against in Step 1.

Rollback at every step: Steps 1–2 are pure documentation/tests, revert trivially. Step 3 is additive
(new fields/functions, nothing removed), revert by not calling the new path — the old path is
untouched and still passes its own tests throughout. Step 4 is per-consumer and revertible by
pointing the one changed `main.py` back at the old construction. Step 5 is irreversible by design and
gated on §18.

## 15. Parity Test Strategy

Test shapes required before Step 5 of any target (concrete cases enumerated per Phase 0 Rule 9 —
normal, boundary, missing data, malformed data, extreme values, zero values, error cases, persistence,
determinism, idempotency):

| Test | Covers | Exists today? |
|---|---|---|
| Golden-fixture equivalence: identical scenario expressed in both engines' native input types (requires the formal mapping this ADR explicitly does not invent — Step 1 output) → assert quality/verdict agree within a Trading-Review-approved tolerance | Normal case | No — blocked on Step 1's mapping decision |
| Full-mandatory-evidence-present → both engines' max score (100) | Extreme value (upper) | **Partially exists** — each engine has its own 100-score fixture (§8); no cross-engine assertion exists because no mapping exists |
| Zero/missing-mandatory-evidence → both engines' fail-closed state | Extreme value (lower), missing data | **Partially exists**, same caveat |
| Malformed/out-of-range input (e.g., `TradingPolicy` points not summing to 100, `DecisionPolicy` weights not summing to 1.0) → both reject via `__post_init__` `ValueError` | Malformed data, error case | **Exists independently** — `tests/test_engine.py::test_policy_rejects_unbalanced_weights`, `tests/test_trading_engine.py`'s policy-validation tests (`TradingDomainFailureTests`) |
| Naive (non-timezone-aware) `evaluated_at` → both raise `DecisionEvaluationError` | Error case | **Exists independently** for each engine |
| Audit/persistence failure → decision unavailable, exception propagates with context | Error case, persistence | **Exists independently** — `test_trading_engine.py::test_audit_storage_failure_makes_decision_unavailable`; no `DecisionEngine`-side equivalent test exists (worth adding regardless of Target A/B, since it would also have caught the logging-level finding in §6 had it asserted the log was *observed*, not just that `.record()` didn't raise) |
| Determinism: same input + same `evaluated_at` → byte-identical output across repeated calls | Determinism | **Exists implicitly** via existing unit tests being non-flaky; no explicit "call twice, assert equal" test exists for either engine |
| Idempotency of `OpportunityRepository.append()` / `EvidenceDecisionAudit.record()` under a retried write | Idempotency | **Does not exist** for either durable store |

Scaffolding added in this session (§ Implementation) targets the rows marked "exists independently"
by *cross-referencing* them explicitly (so a reviewer can see the parity gap is specifically the
cross-engine row, not a general test-coverage gap) and adds the one row that was purely missing
(`DecisionEngine` audit-observability) as a new, safe, non-production characterization test.

## 16. Rollback Strategy

Per step in §14. Summarized: nothing before Step 3 touches production code. Step 3's additive changes
carry the same rollback profile as Phase 0's composition-root work (§N) — revert the commit, old path
untouched throughout. Step 4 is reversible per-consumer. Step 5 (deletion) is the only irreversible
step and is explicitly the last one, gated on §18.

## 17. Risks

- **Trading-domain risk, not engineering risk, dominates this migration.** The central open question
  (§10, TQ-1) is which evidence surface — `DecisionEngine`'s 3-gate model or
  `TradingOpportunityEngine`'s 9-component model — the project actually wants as its long-term
  decision philosophy. Getting this wrong by engineering convenience (e.g., picking whichever is
  currently wired, ignoring why the richer model exists) risks silently narrowing the system's
  evidence requirements.
- **The `DecisionEngine` audit-silence finding (§6) is a latent observability risk independent of
  which target is chosen** — worth remediating regardless of Step 1's outcome, since every target
  keeps `DecisionEngine` in the canonical path in some form.
- **`capabilities.decision.OfficialDecision`'s six-precondition validation gate encodes real
  institutional requirements** (critique, trust, market-state currency, comprehension review) that
  neither `DecisionEngine` nor `TradingOpportunityEngine` currently enforce. Whichever target is
  chosen, deleting the Evidence→Reasoning→OfficialDecision chain outright (rather than wiring it in)
  would also delete those requirements' only existing implementation — a risk this ADR flags but does
  not resolve (AQ-2).

## 18. Deletion Criteria

No engine named in §5 may be deleted until **all** of the following hold for that specific engine:

1. §13's Decision (post-review) names it non-canonical.
2. Every consumer in §9 has been migrated to the canonical path and its own existing contract tests
   still pass unchanged.
3. The parity tests in §15 relevant to that engine pass.
4. `grep -rn "<ClassName>"` across `apps/`, `publish/`, `capabilities/`, `gold_brain/` returns zero
   non-comment, non-docstring matches.
5. `tests/test_architecture.py` and the full validation suite (§ Validation) remain green after the
   deletion, not just before it.
6. Rollback is no longer required — i.e., at least one full production cycle (one CI-scheduled
   `publish.yml` run) has completed successfully against the new canonical path with no incident.

## 19. Open Architecture Questions

See `docs/ADR-0007-ENGINE-CONSOLIDATION-REVIEW-PACKAGE.md` §Architecture Questions (AQ-1 through
AQ-7) for the full, board-ready list.

## 20. Open Trading Questions

See `docs/ADR-0007-ENGINE-CONSOLIDATION-REVIEW-PACKAGE.md` §Trading Questions (TQ-1 through TQ-6).
