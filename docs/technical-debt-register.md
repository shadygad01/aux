# Canonical Technical Debt Register

Priority: P0 blocks institutional production; P1 blocks maintainable scale; P2 planned cleanup.

| ID | Reason | Impact | Owner | Priority | Estimated cost | Target sprint | Removal strategy |
|---|---|---|---|---|---|---|---|
| TD-001 | Multiple decision engines predate canonical ownership | Parallel decisions and scoring | Decision | P0 | XL | Canonical Migration 1 | Route one path to Market Thesis; parity test; delete duplicates |
| TD-002 | Market Thesis canonical object is not yet named/moved into domain | Decision truth remains ambiguous | Decision | P0 | M | Canonical Migration 1 | Migrate `OfficialDecision`; retain contract adapter only |
| TD-003 | Trade Quality is a raw integer with multiple formulas | Scores can diverge silently | Decision | P0 | L | Canonical Migration 1 | Introduce one governed value object/calculator after research mapping |
| TD-004 | No canonical Lineage Graph | Provenance can fragment or disappear | Evidence | P0 | XL | Canonical Migration 2 | Implement ADR-0003 and adapters; verify full paths |
| TD-005 | No canonical Research Finding | Proposal, artifact, and finding meanings overlap | Research | P0 | M | Canonical Migration 2 | Define finding lifecycle; migrate projections |
| TD-006 | Six engine classes expose historical paths | Ownership and maintenance duplication | Architecture | P1 | XL | Compatibility Retirement | Convert to adapters or remove after parity evidence |
| TD-007 | Governance/review/research stores are in-memory | Records disappear on restart | Monitoring | P0 | L | Durable Controls | Durable hash-bound repositories and restore tests |
| TD-008 | Knowledge index does not rehydrate after restart | Search is not production-safe | Knowledge | P0 | L | Durable Controls | Deterministic rehydration and corruption tests |
| TD-009 | Official Decision has five major schemas in one sprint history | Consumer and documentation burden | Publishing | P1 | M | Contract Consolidation | Market Thesis v1 plus explicit adapters/retention |
| TD-010 | No roadmap or ADRs existed before consolidation | Decisions were unauditable | Architecture | P1 | M | Governance Consolidation | Created; enforce ADR check |
| TD-011 | Documentation contains encoding corruption | Reduces trust and maintainability | Documentation | P1 | S | Documentation Repair | Normalize UTF-8 and add encoding check |
| TD-012 | Compatibility documentation is stale | Wrong output ownership claims | Architecture | P1 | S | Governance Consolidation | Correct terminology and interfaces |
| TD-013 | No durable reviewer identity or artifact hash binding | Quality approvals can be fabricated/reused | Security | P0 | L | Durable Controls | Signed identity, commit/artifact binding, expiry |
| TD-014 | All 25 registered trading hypotheses are unvalidated | Decision quality is not institutionally measured | Research | P0 | XL | Research Baseline | Pre-register and execute governed studies |
| TD-015 | Current CLI bypasses Trust/State/Comprehension contracts | Public output is non-compliant | Publishing | P0 | L | Canonical Migration 1 | Convert CLI to Decision Presentation adapter |
