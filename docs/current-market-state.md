# Current Market State

Every reviewed update produces one immutable `CurrentMarketState`. It contains the current Market
Regime, Macro State, horizon Biases, Volatility, Liquidity, Momentum, News, Confidence, Uncertainty,
evidence references, source, policy, timestamp, and TTL.

The state ID is deterministic over all contextual fields. Identical canonical inputs reproduce the
same ID; changing any state component produces a new ID. A state is current only while both its own
TTL and its embedded regime TTL remain valid.

The public Evidence and Reasoning Capabilities accept Current State rather than detached context.
Evidence interpretations must reference its embedded regime. `OfficialDecision 4.0` records the
same Current State ID and refuses authorization when the state is stale. This prevents downstream
steps from silently mixing context captured at different updates.

The older `reasoning_models.MarketState` remains part of Compatibility Adapter contracts during
migration; it is not the new public Current State boundary. Production still needs a transactional
state store, atomic update publication, subscriber version checks, and monitoring that blocks every
consumer when no current state exists.
