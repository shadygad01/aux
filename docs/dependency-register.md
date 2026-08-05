# Dependency Register

## Runtime

Gold Brain has no third-party runtime dependencies. The standard library is sufficient for domain modeling, JSON, CLI presentation, and logging. This reduces supply-chain and license risk.

## Development and CI

| Dependency | Reason | Owner | Considered alternative | License compatibility |
|---|---|---|---|---|
| Ruff 0.12.7 | Deterministic formatting and fast lint enforcement | Platform engineering | Black plus Flake8; more tools for overlapping duties | MIT; compatible |
| mypy 1.17.1 | Strict static type checking for Python contracts | Architecture | Pyright; capable but adds Node-based tooling | MIT; compatible |
| coverage.py 7.10.2 | Branch-aware coverage measurement and threshold | QA | Standard-library trace; lacks practical branch reporting | Apache-2.0; compatible |

Versions are pinned in `pyproject.toml`. Changes require a dependency-register update and CI verification.
