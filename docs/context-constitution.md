# Context Constitution

Status: **CANONICAL CONSTITUTION**

## Purpose

The Context Constitution governs the definition, structure, and lifecycle of the **Context Capability** within Gold Brain.

## Core Rules

1. **Context is NOT Evidence**:
   - Evidence represents weighted observations (e.g. liquidity sweeps, BOS, price location).
   - Context represents the environment in which evidence must be interpreted (e.g. London session, clear news window, expansion regime).

2. **Context is NOT Knowledge**:
   - Knowledge represents historical facts, event memories, and validated research findings.
   - Context represents the transient, expiring environmental state.

3. **Mandatory Environment Wrapper**:
   - Every downstream capability (including Reasoning and Decision engines) MUST consume a valid `MarketContext` before producing reasoning or decision outputs.

4. **Environment Elements**:
   - **Trading Session**: `LONDON`, `NEW_YORK`, `ASIAN`, `OVERLAP`, `CLOSED`
   - **News Window**: `CLEAR`, `PRE_NEWS`, `ACTIVE_HIGH_IMPACT`, `POST_NEWS`
   - **Macro Regime**: `EXPANSION`, `CONTRACTION`, `INFLATIONARY_PRESSURE`, `NEUTRAL`
   - **Volatility Regime**: `LOW_VOLATILITY`, `HIGH_VOLATILITY`, `COMPRESSION`, `EXPANSION`
   - **Liquidity Conditions**: `NORMAL`, `THIN`, `VACUUM`, `HIGH`
   - **Environment Flags**: `is_holiday`, `is_weekend`, `is_market_open`, `is_market_close`

5. **Lifecycle and Expiry**:
   - Context MUST include an `observed_at` timestamp and a `ttl_seconds` duration.
   - Downstream consumers MUST reject expired context (`is_valid(evaluated_at) == False`).
