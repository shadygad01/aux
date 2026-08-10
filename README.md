# Gold Brain

Gold Brain publishes a single, synchronized XAUUSD market-data snapshot and a
fail-closed directional lean. The lean is allowed only when H1 structure, MACD
momentum, and DXY/US10Y context are available and unanimous. It is not a trade
call and has no confidence score, setup, opportunity, or execution plan.

The dashboard also surfaces a "Reversal Signal Start" watch, evaluated on
M15 (not H1): M15 prints a BOS or CHoCH inside the premium zone while
bullish and MACD is still positive (`WATCH_SELL`), or inside the discount
zone while bearish and MACD is still negative (`WATCH_BUY`). This is a
heuristic pattern watch, not a tested edge -- a closely related H1
premium/discount structural-break reversal rule (H-028) was evaluated
against five years of tick data and rejected; see
`backtest/reports/h028_supplied_5y_2026-08-10.md`.

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
