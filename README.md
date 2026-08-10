# Gold Brain

Gold Brain publishes a single, synchronized XAUUSD market-data snapshot and a
fail-closed directional lean. The lean is allowed only when H1 structure, MACD
momentum, and DXY/US10Y context are available and unanimous. It is not a trade
call and has no confidence score, setup, opportunity, or execution plan.

## Production path

```text
Yahoo candles + authoritative spot quote + DXY + US10Y
                         |
                 fail-closed collectors
                         |
          market_data.json + consistency guidance
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
