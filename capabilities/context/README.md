# Context Capability

The **Context Capability** acquires, validates, and provides the canonical environmental context in which evidence must be interpreted.

## Core Principles

- **Context is NOT Evidence**: Context describes the environment (session, regime, news window, liquidity conditions, calendar flags), not directional evidence or price levels.
- **Context is NOT Knowledge**: Context describes transient environmental state, not historical events or validated research patterns.
- **Mandatory Environment Wrapper**: Every downstream capability (including Reasoning and Decision engines) must consume `MarketContext` before producing reasoning or decision output.

## Operational Contracts

- `MarketContext`: Canonical domain object containing session, news window, macro regime, volatility regime, liquidity conditions, environment flags, observation timestamp, and TTL.
- `ContextCapability`: Telemetry-wrapped capability evaluating context validity and freshness.
