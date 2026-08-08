# Capability Readiness Matrix

**Scope note:** this measures the `capabilities/*` institutional governance framework only -- a
separate architecture with no production consumer today (see `publish/composition.py`'s
docstring). It is not a report on the live canonical trading pipeline, which is deployed and
developed independently of this track. See the `scope` field in `docs/readiness-history.json` for
the full explanation, also rendered on the live dashboard's Capability Readiness tab.

Assessment: `READINESS-20260805-GOVERNANCE-01`. Scores use only the governed milestone scale.

| Capability | Mission | Current state | Architecture | Contracts | Tests | Documentation | Performance | Debt and missing components | Risks | Readiness | Confidence | Blocking issues | Effort |
|---|---|---|---|---|---|---|---|---|---|---:|---|---|---|
| Collection | Acquire source facts without interpretation | Port and manual collector; no production source adapter | Boundary defined | Source contract missing | Behavior covered | README present | Unmeasured | Durable collectors, source identity, retries | Missing or stale facts | **40 Architecture Ready** | High | Critical: no production collector. Major: no reliability evidence | L |
| Normalization | Convert facts into canonical units without meaning changes | Deterministic implementation | Boundary defined | No published transformation contract | Behavior covered | README present | Unmeasured | Versioned contract and units registry | Semantic corruption | **40 Architecture Ready** | High | Major: unpublished contract | M |
| Evidence | Create expiring, weighted evidence with provenance | Implemented and tested | Boundary defined; lineage unresolved | Evidence v3 | Capability and regime tests | README and constitution | Unmeasured | LineageGraph and source reliability | Provenance fragmentation | **60 Implementation Ready** | High | Critical: lineage incomplete. Major: reliability unmeasured | XL |
| Knowledge | Preserve and query evidence-backed memory | Repository and questions; restart indexing incomplete | Canonical object exists | Knowledge v1 | Behavior covered | README and constitution | Unmeasured | Rehydration and durable validation review | Search loss after restart | **60 Implementation Ready** | High | Critical: restart safety. Major: freshness absent | L |
| Reasoning | Produce comprehensible reasoning and Market Story | Reasoning path exists; Market Story not canonical code | Ownership defined; parallel projection | Reasoning v4 and comprehension v1 | Behavior covered | README and constitution | Unmeasured | MarketStory, one projection, full lineage | Opaque or divergent reasoning | **40 Architecture Ready** | High | Critical: Market Story missing. Major: parallel outputs | XL |
| Decision | Produce the sole Market Thesis | Multiple precursors; MarketThesis absent | Target governed; migration incomplete | Five decision versions and adapters | Behavior covered | README and constitutions | Unmeasured | MarketThesis, TradeQuality, one path | Conflicting decisions or scores | **40 Architecture Ready** | High | Critical: canonical thesis and scoring absent. Major: contract sprawl | XL |
| Learning | Recommend governed improvements without changing production | Records, recommendations, critique implemented | Boundary defined | Learning v1 and critique v1 | Behavior covered | README and constitution | Unmeasured | Durable archive and calibration | Suggestions mistaken for authority | **60 Implementation Ready** | High | Critical: durable memory absent. Major: calibration absent | L |
| Research | Test hypotheses and produce governed findings | Proposals and discovery; ResearchFinding absent | Output ownership incomplete | Proposal and pattern contracts | Capability and governance tests | README and governance | Unmeasured | Finding lifecycle and 23 studies | Unsupported production claims | **40 Architecture Ready** | High | Critical: finding and validation absent | XL |
| Publishing | Transform Market Thesis into Decision Presentation and deliver it | Sink abstraction; presentation model absent | Target documented | No presentation contract | Behavior covered | README present | Unmeasured | Presentation, lineage enforcement, adapter migration | Non-compliant public output | **20 Prototype** | High | Critical: no canonical presentation. Major: CLI bypass | XL |
| Monitoring | Measure health, readiness, and governance controls | Availability health; readiness documented only | Ownership defined; durable governance missing | Health and quality contracts | Behavior covered | README, health and quality docs | Unmeasured | Evaluator/store, signed approvals, alerts | False readiness and lost audit | **20 Prototype** | High | Critical: readiness and governance not executable or durable | XL |

Confidence is High because repository-wide source, test, contract, and documentation inventories were
available. It describes confidence in this assessment, not confidence in trading outcomes.

Confidence is reproducible: High requires current source, contract, test, documentation, and debt
inventories; Medium permits one missing inventory; Low means two or more are missing. Effort bands
are S (at most one sprint), M (one to two), L (two to four), and XL (more than four or research-led).

## Mandatory owned subprofiles

| Subprofile | Owner | Score | Why | Missing and promotion blocker |
|---|---|---:|---|---|
| Market Story | Reasoning | 20 | Named in lineage and ownership documents only | Canonical object, contract, derivation, tests |
| Market Thesis | Decision | 20 | ADR exists but code uses competing precursors | Canonical object, one calculator, adapters, parity evidence |
| Decision Presentation | Publishing | 0 | Target only; no domain object or contract | Explainability projection and publishing migration |
| Governance | Monitoring | 20 | Policies and in-memory audits exist | Durable identity and hash-bound enforcement |

Each subprofile caps its owner at the next permitted milestone. These profiles create no parallel
business ownership.
