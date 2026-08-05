# Testing

## Responsibility

Verify domain units, engine behavior, failures, edge cases, JSON contracts, CLI integration, regression compatibility, and architecture boundaries.

## Architecture notes

Tests may depend on every production layer. Production packages never depend on tests.

## Public interface

Run `python -m unittest discover -s tests -v`.

## Dependencies

Production packages and Python standard-library `unittest`. CI additionally uses the documented development quality tools.
