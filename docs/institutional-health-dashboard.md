# Institutional Health Dashboard

Owner: Monitoring Capability. This is the canonical metric specification; no second health model is
permitted. These measurements are evidence inputs, not readiness scores. The canonical readiness
view is `institutional-readiness-dashboard.md`.

| Metric | Definition | Baseline | Institutional target |
|---|---|---:|---:|
| Architecture Complexity | Canonical concepts with ambiguous/parallel owners | 7 | 0 P0 ambiguities |
| Documentation Coverage | Published schemas listed in contract catalog | 23/23 | 100% plus interface mapping |
| Knowledge Freshness | Current validated knowledge / production-consumed knowledge | Not measurable | 100% current |
| Research Coverage | Production hypotheses with completed governed validation | 0/25 | 100% of consumed hypotheses |
| Decision Explainability | Public outputs satisfying Market Thesis explanation contract | Compatibility CLI fails | 100% |
| Source Reliability | Active sources with current reliability evidence | Not measurable | 100% |
| Technical Debt | Open canonical debt items by priority | 15 total; 9 P0 | 0 P0 |
| Code Quality | Ruff + strict mypy + architecture tests | Passing at last verification | Passing |
| Maintainability | Engine classes outside capability ownership | 6 | 0 business-owning engines |
| Decision Quality Trend | Governed out-of-sample decision utility/calibration trend | No baseline | Measured, non-degrading |

Supporting inventory at consolidation: 109 domain classes, 39 application classes, 23 schemas, 24
pre-consolidation documentation files, 147 tests, and 6 classes named `*Engine`.

“Not measurable” is a failed health state, not zero risk. Metrics require artifact hashes, capture
time, methodology, owner, and threshold. A score without those fields cannot enter this dashboard.
