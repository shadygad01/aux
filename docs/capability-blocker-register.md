# Capability Blocker Register

| ID | Capability | Severity | Blocker | Evidence | Promotion prevented | Estimated effort |
|---|---|---|---|---|---|---|
| RB-001 | Collection | Critical | No production collection adapter or source assurance | Capability README and source inventory | 60 | L |
| RB-002 | Normalization | Major | No published transformation contract | Contracts catalog | 60 | M |
| RB-003 | Evidence | Critical | Canonical LineageGraph absent | ADR-0003, TD-004 | 80 | XL |
| RB-004 | Knowledge | Critical | Search index does not rehydrate safely | TD-008 | 80 | L |
| RB-005 | Reasoning | Critical | Market Story is not a canonical implemented projection | Ownership map | 60 | XL |
| RB-006 | Decision | Critical | MarketThesis and TradeQuality are not canonical code | ADR-0002, TD-002, TD-003 | 60 | XL |
| RB-007 | Learning | Critical | Institutional learning records are not durably stored | TD-007 | 80 | L |
| RB-008 | Research | Critical | ResearchFinding absent; 23 hypotheses unvalidated | TD-005, TD-014 | 60 | XL |
| RB-009 | Publishing | Critical | DecisionPresentation absent and CLI bypasses controls | TD-015 | 40 | XL |
| RB-010 | Monitoring | Critical | Readiness and governance are not durable or executable | TD-007, TD-013 | 40 | XL |
| RB-011 | All | Major | Performance baselines are absent | Capability matrix | 80 | L |
| RB-012 | All | Major | Human approvals are not revision-bound | Quality constitution, TD-013 | 80 | L |

Critical blocks the next production-path milestone; Major blocks Production Candidate; Minor
requires correction but does not independently block the next milestone. Closed blockers remain in
readiness history with closure evidence and are never deleted.
