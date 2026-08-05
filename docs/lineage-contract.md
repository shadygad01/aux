# Canonical Lineage Contract

## Required path

`Fact → Evidence → Knowledge → Market Story → Reasoning → Market Thesis → Decision Presentation → Dashboard`

## Canonical object

One immutable `LineageGraph` will be owned by the Evidence Capability. It is not yet implemented;
this absence is P0 technical debt and blocks institutional production readiness.

Every node must expose:

- stable node ID and node kind;
- canonical artifact ID and SHA-256 hash;
- observed/created timestamp and source identity;
- policy, contract, and transformation version;
- known limitations and expiry/review state;
- references to the immutable parent nodes used to derive it.

Every edge must expose a typed transformation, calculation/method reference, actor/capability, and
time. Presentations may filter the graph but may not invent, copy without linkage, or remove
contradicting provenance.

## Migration

`DecisionGraph`, `ExplanationTrace`, `supporting_evidence` tuples, trust references, source fields,
and audit IDs become immutable projections/adapters over the Lineage Graph. No second graph API may
be introduced during migration.
