"""Create canonical research bars from owner-supplied midpoint M5 data.

The supplied H1 file is deliberately not trusted for lineage because it does
not match M5 coverage and contains continuous zero-volume fills. M15 and H1
are rebuilt from nonzero-volume M5 bars. Bid/ask fields equal midpoint only
for technical feature computation; execution research must model spread
explicitly and may not claim tick-executable fills.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from .audit_supplied_mtf import load
from .mtf_data import H1_SECONDS, M15_SECONDS, aggregate_bars, validate_bar_lineage
from .mtf_models import BidAskBar
from .mtf_storage import write_bars


def ingest(m5_source: Path, output_root: Path) -> dict[str, object]:
    _header, source_bars, sources = load(m5_source)
    censored = [bar for bar in source_bars if bar.volume_bid > 0 or bar.volume_ask > 0]
    m5 = [
        BidAskBar(
            timestamp=bar.timestamp,
            seconds=300,
            bid_open=bar.open,
            bid_high=bar.high,
            bid_low=bar.low,
            bid_close=bar.close,
            ask_open=bar.open,
            ask_high=bar.high,
            ask_low=bar.low,
            ask_close=bar.close,
            tick_count=1,
            bid_volume=bar.volume_bid,
            ask_volume=bar.volume_ask,
            mean_spread=0.0,
        )
        for bar in censored
    ]
    m15 = aggregate_bars(m5, M15_SECONDS)
    h1 = aggregate_bars(m5, H1_SECONDS)
    validate_bar_lineage(m5, m15, h1)
    paths = {
        "M5": output_root / "XAUUSD_M5.jsonl",
        "M15": output_root / "XAUUSD_M15.jsonl",
        "H1": output_root / "XAUUSD_H1.jsonl",
    }
    for timeframe, bars in (("M5", m5), ("M15", m15), ("H1", h1)):
        write_bars(paths[timeframe], bars)
    manifest = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "source_file": str(m5_source),
        "declared_sources": sorted(sources),
        "price_scale": 100_000,
        "execution_quality": "MIDPOINT_ONLY_NO_BID_ASK_SPREAD",
        "zero_volume_m5_censored": len(source_bars) - len(m5),
        "bars": {"M5": len(m5), "M15": len(m15), "H1": len(h1)},
        "coverage": {
            "first": m5[0].timestamp.isoformat(),
            "last": m5[-1].timestamp.isoformat(),
        },
        "files": {timeframe: str(path) for timeframe, path in paths.items()},
    }
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    import sys

    print(json.dumps(ingest(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
