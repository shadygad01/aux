# Phase 0 — External Auditor Package

**Pending External Auditor Review.** Nothing in this document constitutes auditor approval. No
migration listed here has been executed. This package exists to isolate exactly what requires
independent sign-off before Canonical Migration 1 (per `docs/roadmap.md`) may begin, per
`docs/PHASE_0_MIGRATION_READINESS.md`.

Companion document: `docs/PHASE_0_MIGRATION_READINESS.md` (full evidence, consumer inventory,
canonical ownership matrix, migration order, and per-item Definitions of Done). This document does
not repeat that evidence — it isolates the questions that need a human decision.

---

## 1. Architectural Questions Requiring Independent Approval

**Q1. Is "whichever path is reachable from `publish/generate_artifacts.py`" an acceptable
tie-breaker for canonical ownership during the transition?**
`docs/PHASE_0_MIGRATION_READINESS.md` §C uses production reachability as a pragmatic tie-breaker
between competing implementations (e.g., `DecisionEngine` over `EvidenceDecisionEngine`) because no
ADR currently states this rule. It is consistent with the existing adapter map in
`concept-ownership.md`, but no ADR says "when two implementations exist, the one with live traffic
wins." **Disputed decision:** should this be codified as an ADR, or should canonical ownership be
decided purely by design intent regardless of current traffic?

**Q2. Should the 100%-unreachable `capabilities/` layer be given its first production consumer
before or after the decision-path consolidation (TD-001)?**
The migration order in §I sequences the shared composition root and TD-001 first, `capabilities/`
wiring (RB-009) fifth. An alternative view: wiring `capabilities/` first would validate the intended
architecture sooner and avoid building more logic into the `packages/application` engines that will
need to move later. **Disputed decision:** confirm or override the proposed sequencing.

**Q3. Four capability folders exist beyond ADR-0001's ten (`context`, `execution_readiness`,
`macro`, `opportunity_identity`).** None has an authorizing ADR amendment. Three are inconsistently
tracked in `readiness-history.json`'s snapshot without formula inclusion; one is not tracked at all.
**Disputed decision:** should these four be (a) formally authorized via an ADR-0001 amendment as new
capability owners, (b) folded into existing owners as subprofiles the way Market Story/Market
Thesis/Decision Presentation/Governance are under ADR-0006, or (c) deleted as premature scaffolding
with no current justification? This repository cannot resolve its own ownership-boundary question —
that is exactly ADR-0001's stated purpose ("any exception requires a new ADR and Constitutional
approval").

**Q4. `docs/architecture.md` (the V1 foundation document) is not cross-referenced from any current
governance document and describes a superseded model.** Should it be explicitly marked superseded,
merged into current documentation, or retired? (TD-012.)

---

## 2. Migration Risks

| Migration | Risk | Why |
|---|---|---|
| TD-001 (engine consolidation) | High | Core business logic; four independently-tested engines must converge to one without silently changing verdict/quality output for any historical or live observation. |
| TD-004 (LineageGraph) | High | Touches every decision-producing path; the largest single structural change (XL, confirmed by both the original register and this session's re-verification). |
| RB-009 (Decision Presentation) | High | The live GitHub Pages dashboard's data contract depends on today's `decision.json`/`market_thesis.json` shape (`docs/app.js`); a presentation-layer migration that doesn't preserve that shape breaks a system with real, if informal, users. |
| RB-005 (Market Story canonicalization) | Medium-High | `publish/generators/market_story.py` is a 293-line live generator; replacing its ad hoc construction with the canonical capability object risks behavior drift if not done via parity test. |
| TD-007/TD-013 (durable stores + identity binding) | Medium | Lower engineering risk (established pattern to extend) but carries a Security review requirement because durable governance records claim institutional authority once they exist — a fabricated or replayed approval is a security failure, not a bug. |
| TD-008 (Knowledge rehydration) | Low | Fully isolated, single file, no architectural decision required — flagged as the lowest-risk migration to execute first once Phase 0 exits. |

---

## 3. Proposed Canonical Ownership (for ratification, not self-approval)

See `docs/PHASE_0_MIGRATION_READINESS.md` §C in full. Summary of what requires ratification rather
than being merely descriptive:

- `DecisionEngine` + `build_market_thesis()` as the canonical decision path (currently true by
  traffic, not by ADR — see Q1).
- `MarketThesis`/`TradeQuality` as fully canonical (this one is **not** disputed — it matches
  ADR-0002 exactly and is evidence-confirmed; listed here only for completeness).
- Deferred/undecided: Market Story, Lineage Graph, Decision Presentation, Research Finding — all
  have a named target in existing ADRs/`concept-ownership.md` but no implementation to ratify yet.

---

## 4. Consumer Inventory Summary

Full detail in `docs/PHASE_0_MIGRATION_READINESS.md` §F. Headline finding for auditor attention:

- **3 real production entry points** exist: `apps/decision_cli`, `apps/trading_cli`,
  `publish/generate_artifacts.py`. Only the third is scheduled/CI-invoked
  (`.github/workflows/publish.yml`, `deploy_interserver.yml`).
- **14 of 20 `packages/application` classes and all 14 `capabilities/` classes have zero production
  consumers**, confirmed by exhaustive `grep`-based import-graph search, not sampling.
- The consumer inventory is complete for every TD/RB item in the companion document. No migration is
  proposed as "ready" without it.

---

## 5. Parity-Test Strategy

Full matrix in `docs/PHASE_0_MIGRATION_READINESS.md` §G. Summary: **6 of 7 required parity tests do
not exist yet** and were not written speculatively in this session (writing a parity test with no
committed second implementation to compare against would itself be scaffolding without a target —
the kind of premature construction Phase 0 prohibits). The one exception (`MarketThesis` required-
field regression test) was written because both sides of the comparison — the old fabricating
behavior and the new rejecting behavior — already existed in this session's own diff.

**Auditor decision needed:** should parity tests be written and reviewed *before* implementation
work on TD-001/TD-004/RB-005/RB-009 begins (test-first, slower, higher confidence), or concurrently
with a feature-branch implementation that isn't merged until parity passes (faster, standard
practice, equal end-state safety)? The Institutional Quality Gate (ADR-0004) does not currently
specify an order for this.

---

## 6. Migration Order (for ratification)

Full graph and rationale in `docs/PHASE_0_MIGRATION_READINESS.md` §H–§I:

1. Shared composition root (no auditor gate — mechanical refactor, no behavior change)
2. TD-001/TD-006/RB-006 — engine consolidation (**Architecture + Trading review required**)
3. TD-008/RB-004 — Knowledge rehydration (no auditor gate — isolated engineering completion)
4. TD-004/RB-003 — LineageGraph (**Architecture review required**)
5. RB-009/TD-002/TD-009/TD-015 — Decision Presentation + first capability-layer wiring
   (**Publishing + Explainability review required**)
6. RB-005/TD-006(cont.) — Market Story canonicalization (**Reasoning + Explainability review required**)
7. TD-007/TD-013/RB-007/RB-010/RB-012 — durable governance stores (**Security review required**)
8. TD-005/RB-008 (model/lifecycle half only) — Research Finding lifecycle (**Research review required**)

Items not on this list because they are not migrations: TD-003 (resolved), TD-010 (resolved), TD-011
(resolved), TD-012 (documentation-only, no auditor gate), RB-001's collector hardening (engineering
hardening, no auditor gate), RB-002 (contract publication, no auditor gate), RB-011 (measurement, no
auditor gate).

---

## 7. Rollback Strategy

Summarized per migration in `docs/PHASE_0_MIGRATION_READINESS.md` §I's closing note. Headline for
auditor attention: steps 1, 3, 7, and 8 above are additive/refactor-only and carry low rollback
risk by construction (no deletion, no schema change to persisted data — note that none of the
durable stores in step 7 currently hold any production data to migrate, since they have zero
current consumers). Steps 2, 4, 5, and 6 delete or redirect live production code paths and are
gated — by rule, not by this document's preference — on passing parity tests *before* any deletion
occurs.

---

## 8. Questions Requiring Independent Approval — Consolidated List

1. Q1 (canonical-ownership tie-breaker rule) — needs an ADR or an explicit override.
2. Q2 (sequencing: consolidate first vs. wire `capabilities/` first) — needs ratification of the
   proposed order or a directed alternative.
3. Q3 (four unauthorized capability folders) — needs a disposition decision (authorize / fold into
   subprofiles / delete).
4. Q4 (stale `architecture.md`) — needs a disposition decision (mark superseded / merge / retire).
5. Parity-test sequencing relative to implementation (§5) — needs a Quality Gate process decision.
6. TD-013/RB-012's identity-binding acceptance criteria — needs a Security review to define "durable
   reviewer identity" concretely enough to implement against (the current text is a requirement
   statement, not a specification).
7. Per-migration sign-off: each of the eight Migration Order steps requiring auditor review (§6)
   needs its own scheduled review slot — this package does not assume any of the ten Institutional
   Quality Gate reviews (ADR-0004) have occurred for any of them.

No item in this section has been answered by this session. Answering them is explicitly out of
scope for repository-local work — they require a decision-maker external to the code, which is the
entire reason this package exists as a separate document from the migration-readiness evidence.
