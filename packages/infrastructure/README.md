# Infrastructure Package

## Responsibility

Translate versioned JSON contracts, implement structured decision logging, and append complete research evaluations and later outcomes. It contains adapters only; it owns no decision rules.

## Architecture notes

This outer layer depends on application ports and domain models. Contract failures include JSON paths and preserve their root exceptions.

## Public interfaces

`observation_from_json`, all versioned serializers, structured loggers, append-only decision/learning/reasoning audits, and the institutional knowledge journal with its in-process typed index.

## Dependencies

Application and domain packages plus Python standard library. JSON and logging use the standard library to avoid unjustified dependencies. Owner: platform engineering.
