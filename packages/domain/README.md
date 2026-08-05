# Domain Package

## Responsibility

Own immutable business concepts and named decision configuration. It contains no parsing, logging, file, UI, or API code.

## Architecture notes

This is the innermost Clean Architecture layer. Every outer package may depend on it; it depends only on the Python standard library.

## Public interfaces

The exports in `packages.domain.__init__` are the supported interface. Inputs are `MarketObservation` and `DecisionPolicy`; the principal output is `Decision`.

## Dependencies

Python standard library only. Reason: domain behavior needs no third-party capability. Owner: Gold Brain architecture. License compatibility: Python PSF license.
