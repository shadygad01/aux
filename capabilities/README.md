# Capabilities

This is the capability-first public architecture. Each folder owns one business responsibility, public interface, typed contract, tests, metrics, logs, health status, and documentation. Capabilities depend on contracts and injected ports, never UI or dashboards. Compatibility Adapter `*Engine` classes remain implementation details outside this public layer.
