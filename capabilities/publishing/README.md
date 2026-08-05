# Publishing Capability

Owns delivery of `OfficialDecision` through replaceable `PublicationSink`. Output: `PublicationReceipt`. Metric/log: successful publications. Health is `NOT_READY` without a sink. It cannot alter the decision or execute a trade.

New publications inherit the current Official Decision compatibility contract, including
explanation, critique, trust, Current State, and comprehension review. Publishing cannot replace the
canonical Market Thesis with a score or summary string.
