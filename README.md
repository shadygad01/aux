# Gold Brain

Gold Brain publishes a single, synchronized, decision-free XAUUSD market-data
snapshot. It reports measurements with timestamps, sources, methods, data
availability, and explicit limitations. It does not publish trade calls,
confidence scores, setup quality, opportunities, execution plans, or composite
macro forecasts.

## Production path

```text
Yahoo candles + authoritative spot quote + DXY + US10Y
                         |
                 fail-closed collectors
                         |
                   market_data.json
                         |
                 static browser dashboard
```

Generate the artifact:

```powershell
python publish/generate_artifacts.py
```

Production output is limited to:

- `docs/artifacts/market_data.json`
- `docs/artifacts/manifest.json`

The `backtest/` directory is quarantined research tooling. It may retain legacy
simulation types for reproducibility, but it is not imported by the publisher
or browser and cannot produce a live product output.

## Verification

```powershell
python -m unittest discover -s tests
python -m ruff check .
python -m mypy
```
