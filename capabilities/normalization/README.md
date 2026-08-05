# Normalization Capability

Owns conversion of raw numeric fields into configured canonical units. Input: `CollectionBatch`. Output: `tuple[NormalizedDatum, ...]`. Metric: `records_normalized`. Logs completion/failure. Health is `NOT_READY` without field-unit configuration. It does not collect or interpret market meaning.
