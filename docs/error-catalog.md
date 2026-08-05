# Error Catalog

| Error | Layer | Recoverability | Observability | Consumer action |
|---|---|---|---|---|
| `ContractValidationError` | Infrastructure | Correct the input and retry | Includes field path, received contract, or root validation context | Do not evaluate malformed evidence |
| `DecisionEvaluationError` | Application | Fix evaluation time or restore audit logger, then retry | Includes symbol, verdict/policy where available; chains sink failure | Treat decision as unavailable |
| CLI parser error | Presentation | Correct file, JSON, or timestamp and rerun | Includes observation path and underlying contextual error | No decision is emitted |

Domain constructor `ValueError` failures identify invalid invariants. Infrastructure adapters wrap them with boundary context instead of hiding them.
