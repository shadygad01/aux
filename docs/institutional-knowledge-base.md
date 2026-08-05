# Institutional Gold Knowledge Base

Status: **GOVERNING CONSTITUTION — explicit approval is required for philosophical changes.**

## Mission

The knowledge base is Gold Brain’s evidence-backed institutional memory. It is not treated as a news archive, wiki, document folder, or ungoverned database. Knowledge objects, sources, historical events, and patterns are structured first-class domain objects with append-only revisions.

No knowledge object is accepted without registered sources and supporting evidence. Contradictions remain attached; they are not deleted to make a rule look cleaner.

## Lifecycle

The only forward lifecycle is:

`OBSERVATION → HYPOTHESIS → VALIDATED → INSTITUTIONAL_RULE → DEPRECATED`

Skipping stages or reversing status is rejected. Each transition appends a higher revision with fresh validation evidence; prior revisions remain intact. Every object has a review interval, and the latest revision becomes due for revalidation when that interval expires.

## Source ranking

Sources store type, reliability, freshness, authority, historical accuracy, bias risk, transparency, review schedule, and ranking evidence. Ranking is recalculated at query time. The initial versioned formula weights reliability 25%, freshness 15%, authority 20%, historical accuracy 20%, transparency 15%, and inverse bias risk 5%.

These weights are hypotheses. Source type does not silently grant a fixed score. Historical performance and review decay affect actual ranking.

## Event and pattern memory

Historical events store timelines, cross-market reactions, gold/DXY/yield behavior, lessons, explicit query flags, and evidence references. Pattern objects store conditions, status, sample size, win/failure rates, weaknesses, best/worst sessions, evidence, and review schedule. Experimental patterns are stored but excluded from validated failure-rate answers.

## Question engine

The first structured questions are:

- When did gold explicitly ignore DXY?
- When did yields explicitly dominate gold?
- Which recorded macro events had the strongest absolute gold reversals?
- What is the sample-weighted validated premium failure rate?
- What is the sample-weighted validated sweep failure rate?

Answers contain result IDs, statistics, and evidence references. Missing evidence produces an explicit abstention. The engine does not interpret arbitrary prose or infer historical relationships that were not encoded and evidenced.

## Storage maturity

`JsonLinesKnowledgeRepository` writes a durable append-only journal and maintains a typed query index for the current process. A production restart-safe index rehydration pipeline is not yet implemented; the journal is the recoverable source record, but production deployment must remain blocked until deterministic rehydration, corruption detection, backup, and migration tests exist.
