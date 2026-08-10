from __future__ import annotations

import lzma
import tempfile
import unittest
import urllib.error
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from unittest.mock import patch

from backtest.dukascopy_ticks import (
    DATAFEED_ROOT,
    TICK_STRUCT,
    HourFile,
    TickManifest,
    decode_hour,
    download_hour,
    download_range,
    hour_url,
    write_manifest,
)


class DukascopyTickTests(unittest.TestCase):
    def test_zero_based_month_url(self) -> None:
        url = hour_url("XAUUSD", datetime(2026, 1, 5, 10, tzinfo=UTC))
        self.assertTrue(url.endswith("/XAUUSD/2026/00/05/10h_ticks.bi5"))

    def test_bi5_decode_preserves_bid_ask_and_millis(self) -> None:
        raw = b"".join(
            (
                TICK_STRUCT.pack(1000, 200_200, 200_000, 2.0, 1.0),
                TICK_STRUCT.pack(1500, 200_300, 200_100, 4.0, 3.0),
            )
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "ticks.bi5"
            path.write_bytes(lzma.compress(raw))
            ticks = decode_hour(
                path, datetime(2026, 1, 5, 10, tzinfo=UTC), price_scale=1000
            )
        self.assertEqual(len(ticks), 2)
        self.assertEqual(ticks[0].bid, 200.0)
        self.assertEqual(ticks[0].ask, 200.2)
        self.assertEqual(ticks[1].timestamp.microsecond, 500_000)
        self.assertEqual(ticks[1].bid_volume, 3.0)

    def test_manifest_serializes_hour_as_iso_datetime(self) -> None:
        hour = datetime(2026, 1, 5, 10, tzinfo=UTC)
        manifest = TickManifest(
            "1.0.0",
            "XAUUSD",
            DATAFEED_ROOT,
            hour.isoformat(),
            hour.isoformat(),
            None,
            None,
            0,
            (),
            0,
            (HourFile(hour, "x.bi5", "abc", 10, 0),),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            write_manifest(manifest, path)
            content = path.read_text()
        self.assertIn("2026-01-05T10:00:00+00:00", content)

    def test_transient_503_is_retried_but_404_is_missing(self) -> None:
        hour = datetime(2025, 1, 6, 10, tzinfo=UTC)
        transient = urllib.error.HTTPError("url", 503, "busy", Message(), None)
        missing = urllib.error.HTTPError("url", 404, "missing", Message(), None)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch("backtest.dukascopy_ticks.urllib.request.urlopen", side_effect=transient),
                patch("backtest.dukascopy_ticks.time.sleep") as sleep,
                self.assertRaises(urllib.error.HTTPError),
            ):
                download_hour("XAUUSD", hour, root, retries=2)
            sleep.assert_called_once_with(1)
            with patch(
                "backtest.dukascopy_ticks.urllib.request.urlopen", side_effect=missing
            ):
                self.assertIsNone(download_hour("XAUUSD", hour, root, retries=2))

    def test_range_continues_when_one_hour_exhausts_retries(self) -> None:
        start = datetime(2025, 1, 6, 10, tzinfo=UTC)
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch(
                "backtest.dukascopy_ticks.download_hour",
                side_effect=(urllib.error.URLError("timeout"), None),
            ),
        ):
            downloaded, unavailable = download_range(
                "XAUUSD", start, start.replace(hour=12), Path(temporary), workers=1
            )
        self.assertEqual(downloaded, 0)
        self.assertEqual(unavailable, 2)


if __name__ == "__main__":
    unittest.main()
