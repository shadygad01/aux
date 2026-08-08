# ADR-0007 — Engine Consolidation: Architecture + Trading Review Package

**Pending Architecture Review and Trading Review.** Nothing in this document constitutes approval.
No engine has been deleted, no consumer has been migrated, and no production behavior has changed.
Companion document: `docs/adr/0007-engine-consolidation.md` (full evidence, engine inventory,
production call graph, duplication analysis, formula comparison, consumer inventory, canonical
ownership proposal, target architecture options, migration plan). This package isolates the specific
questions that need a human decision, per this repository's existing pattern
(`docs/PHASE_0_EXTERNAL_AUDITOR_PACKAGE.md`).

**Numbering note:** filed as ADR-0007, not ADR-0004, because `docs/adr/0004-institutional-quality-gate.md`
already exists — see the companion ADR's header for the full explanation.

**Update:** AQ-1, AQ-2, and TQ-1 below are marked `[RESOLVED — see ADR-0007 §21]`. The product owner
supplied an explicit product-first decision rule; applying it to this package's own evidence selected
Target A (`docs/adr/0007-engine-consolidation.md` §21). AQ-3 through AQ-7 and TQ-2 through TQ-6
remain open as originally written — the product-first decision did not require answering them.

---

## Architecture Questions

**[RESOLVED — see ADR-0007 §21] AQ-1. Which evidence surface is the intended long-term canonical decision model —
`DecisionEngine`'s 3-gate (structure/location/liquidity) model, or `TradingOpportunityEngine`'s
9-component (macro/execution-bias/cross-horizon/location/liquidity-sweep/nearby-liquidity/MACD/
reversal-candle/optional-SMC) model?**
This is the single highest-leverage unresolved question in the entire consolidation. §10/§11 of the
companion ADR show it cannot be derived from production usage (only `DecisionEngine` has scheduled
traffic; `TradingOpportunityEngine` has none) or from the ADR history (ADR-0002 names `MarketThesis`
canonical but is silent on which calculation feeds it). Selects between Target A and Target B in
§11.

**[RESOLVED — see ADR-0007 §21] AQ-2. Is the Evidence→Reasoning→OfficialDecision chain (`EvidenceDecisionEngine` →
`InstitutionalReasoningEngine` → `capabilities.decision.OfficialDecision`) the intended eventual
canonical path implied by the capability-ownership ADRs (ADR-0001/ADR-0002), or an earlier design
iteration superseded by the simpler `DecisionEngine` path?**
The chain is fully implemented, fully tested, and internally well-layered (§7 classifies it "E —
complementary, correctly layered"). It has simply never had a consumer. Its six-precondition
publication gate (critique, trust, market-state currency, comprehension review) has no equivalent
anywhere in the currently-live path. If this chain is superseded, that gate's institutional
requirements need an owner elsewhere before deletion; if it's the intended future, it needs a
wiring plan (which is RB-009's scope, not this ADR's).

**AQ-3. Is `DecisionEngine`'s audit trail being silently discarded in every production run
(confirmed in this session — §6 of the companion ADR) an accepted current state, or does it need
immediate remediation independent of the consolidation decision?**
Concretely: `logging.getLogger("gold_brain.publish").isEnabledFor(logging.INFO)` is `False` under
`publish/composition.py`'s current `WARNING`-level configuration, and `JsonDecisionLogger.record()`
logs at `INFO`. No exception is raised; `Decision` objects are computed and written to artifacts
correctly; only the structured per-decision log line is lost. This is independent of AQ-1/AQ-2 —
every target architecture in §11 keeps `DecisionEngine` in the canonical path in some form. Not
fixed in this session (a logging-level change is a production behavior change, outside this
mission's Implementation Allowance).

**[RESOLVED — see ADR-0007 §21.9] AQ-4. Should `TradingPolicy`, `EvidencePolicy`, and `ReasoningPolicy`
remain permanently scoped to their own engines, or does resolving AQ-1/AQ-2 imply one of them should
absorb `DecisionPolicy`'s role?**
Resolved by the same Target A decision that resolved AQ-1/AQ-2: `DecisionPolicy` remains the sole
canonical Policy object for the canonical `DecisionEngine`. `TradingPolicy`/`EvidencePolicy`/
`ReasoningPolicy` remain scoped to their now-dormant engines and are not absorbed, merged, or
retired — no code change occurs, only the classification in ADR-0007 §21.4/§21.10.

**AQ-5. Does `capabilities.decision.OfficialDecision`'s `contract_version = "5.0.0"` (implying at
least four prior schema iterations, matching TD-009's "five major schemas" finding) need a
migration/retention plan of its own, independent of whether the chain it belongs to (AQ-2) is kept
or retired?**
TD-009 in `docs/PHASE_0_MIGRATION_READINESS.md` already tracks this as sequenced after RB-009; this
question exists to confirm that sequencing still holds once AQ-2 is answered, since AQ-2's answer
could accelerate or eliminate TD-009's relevance.

**AQ-6. Should the parity-test gap flagged in §15 of the companion ADR — no cross-engine golden
fixture can exist without first defining a formal mapping between `MarketObservation`,
`TradingObservation`, and `tuple[Evidence, ...]` — be resolved by (a) defining that mapping as part
of Step 1 of the migration (§14), or (b) treating the three input models as permanently
non-interchangeable and instead proving equivalence only at the policy-threshold level (e.g., "both
formulas gate at 75/100")?**
This is an engineering-methodology question with a trading-domain dependency: option (a) requires
Trading Review to bless a specific field-by-field mapping (e.g., "a confirmed SMC break of structure
maps to `Evidence(kind=MARKET_BIAS, strength=1.0, ...)`"), which is itself a modeling decision this
document explicitly declined to invent.

**AQ-7. Does the existing `tests/test_architecture.py` layer-boundary suite need a new rule once a
target is chosen — e.g., "no `packages/application` engine may be instantiated outside
`publish/composition.py` or a named CLI `main.py`" — to prevent future duplication in the same shape
this ADR documents?**
Not required for Phase 0/consolidation-readiness itself, but worth deciding now so Step 3 (§14) can
include it if approved, rather than treating it as a later afterthought.

---

## Trading Questions

**[RESOLVED — see ADR-0007 §21] TQ-1. Does the project want its canonical decision philosophy to require macro context,
multi-horizon bias agreement, and active-news awareness (`TradingOpportunityEngine`'s model), or is
the simpler SMC-structure-only model (`DecisionEngine`'s model) the intended production philosophy,
with the richer model reserved for future research?**
This is the trading-domain half of AQ-1. `docs/hypothesis-register.md` lists both models' component
weights as `UNVALIDATED` hypotheses (H-006 for `DecisionEngine`'s 0.40/0.30/0.30; H-008 for
`TradingOpportunityEngine`'s 15/15/5/15/10/5/10/15/10) — neither has more empirical support than the
other today. The answer determines which evidence the live system should be *requiring* users/the
dashboard to trust, not just which code path runs.

**TQ-2. Is `EvidenceDecisionEngine`'s abstention state (`Recommendation.NO_OPINION`, distinct from
`WAIT`) a trading concept the canonical path should adopt — "we have not formed a view" versus "we
have a view but conditions aren't met to act on it" — or is collapsing everything to `WAIT` (as
`DecisionEngine` does today) the intended behavior?**
`README.md` already draws exactly this distinction in prose ("The Version 3 evidence engine
distinguishes insufficient evidence (`NO_OPINION`) from incomplete execution (`WAIT`)") but the
*production* path (`DecisionEngine`) does not implement it — only the orphaned
`EvidenceDecisionEngine` does. This is a case where the documented intent and the shipped behavior
already disagree, independent of any code this session touched.

**TQ-3. `TradingOpportunityEngine` treats certain missing evidence and conflicts as non-blocking
(optional SMC confirmations, minor macro contradictions, nearby-liquidity-level absence) while
`DecisionEngine` treats its three mandatory gates as strictly all-or-nothing. Is graduated,
partially-forgiving evidence weighting the intended trading philosophy, or should all evidence
remain strictly mandatory?**

**TQ-4. Should news-driven forced states (`PAUSED`, forced `WAIT` on `REJECTS_SETUP`/`FORCE_WAIT`
effects) — currently unique to `TradingOpportunityEngine` — become part of the canonical decision
path regardless of which evidence-surface answer TQ-1 produces?** `DecisionEngine` has no news input
at all today; the live dashboard's decisions are computed with zero news awareness.

**TQ-5. `minimum_trade_quality`/`attention_threshold` are `75` (on their respective 0–100 or
0.0–1.0 scales) in `TradingPolicy`, `EvidencePolicy`, and `DecisionPolicy` alike — an apparent
convergence. Is this numeric agreement intentional (all three were calibrated to the same target) or
coincidental (each was set independently and happens to match)?** If intentional, it's supporting
evidence the three formulas were meant to be threshold-compatible even while structurally different;
if coincidental, it shouldn't be read as evidence of anything.

**TQ-6. Given `capabilities.decision.OfficialDecision` requires nine completed `ReasoningStage`s, a
pre-publication critique, a trust manifest, current market state, and an approved comprehension
review before authorizing any output — is this the intended bar for *any* future canonical decision
path (i.e., should `DecisionEngine`/`build_market_thesis`'s output eventually be required to clear
the same six preconditions), or is that bar specific to the Evidence→Reasoning chain and not meant
to generalize?**
