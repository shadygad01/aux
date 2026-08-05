# Collection Capability

Owns acquisition of raw observations through `CollectionPort`. Input: `CollectionRequest`. Output: `CollectionBatch`. Metric: `records_collected`. Logs completion/failure. Health is `NOT_READY` without an adapter. It contains no normalization or decision logic and depends only on capability contracts.
