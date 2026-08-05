import unittest
from datetime import UTC, datetime, timedelta

from packages.application import CurrentMarketStateAssembly, MarketRegimeIdentification
from packages.domain import (
    AttentionBias,
    HorizonBias,
    MarketRegime,
    MarketRegimeContext,
    TradingHorizon,
)

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def regime() -> MarketRegimeContext:
    return MarketRegimeIdentification("regime-v1").identify(
        MarketRegime.TRENDING,
        (MarketRegime.TRENDING, MarketRegime.EXPANSION, MarketRegime.HIGH_VOLATILITY),
        NOW,
        timedelta(minutes=10),
        80,
        "Directional expansion is active.",
        ("regime:evidence:1",),
        "reviewed-classifier",
    )


class CurrentMarketStateTests(unittest.TestCase):
    def test_every_update_produces_complete_deterministic_state(self) -> None:
        current_regime = regime()
        assembler = CurrentMarketStateAssembly("state-v1")
        arguments = (
            "XAUUSD",
            NOW,
            timedelta(minutes=5),
            current_regime,
            "Real yields falling; DXY neutral.",
            (HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.BUY_ONLY, "Macro bias."),),
            "High and expanding.",
            "Sell-side liquidity swept; buy-side remains.",
            "Positive but not overextended.",
            "No active tier-one release.",
            84,
            16,
            ("macro:1", "liquidity:1", "momentum:1"),
            "state-assembly",
        )
        first = assembler.assemble(*arguments)
        repeated = assembler.assemble(*arguments)
        self.assertEqual(first.state_id, repeated.state_id)
        self.assertTrue(first.is_current(NOW))
        self.assertEqual(first.regime, current_regime)

        changed = assembler.assemble(
            "XAUUSD",
            NOW,
            timedelta(minutes=5),
            current_regime,
            "Real yields falling; DXY neutral.",
            (HorizonBias(TradingHorizon.MEDIUM_TERM, AttentionBias.BUY_ONLY, "Macro bias."),),
            "High and expanding.",
            "Sell-side liquidity swept; buy-side remains.",
            "Positive but not overextended.",
            "News catalyst active.",
            84,
            16,
            ("macro:1", "liquidity:1", "momentum:1"),
            "state-assembly",
        )
        self.assertNotEqual(first.state_id, changed.state_id)

    def test_missing_named_state_is_rejected(self) -> None:
        current_regime = regime()
        with self.assertRaisesRegex(ValueError, "every named state"):
            CurrentMarketStateAssembly("state-v1").assemble(
                "XAUUSD",
                NOW,
                timedelta(minutes=5),
                current_regime,
                "Macro state",
                (HorizonBias(TradingHorizon.SCALPING, AttentionBias.WAIT, "Bias"),),
                "Volatility state",
                "",
                "Momentum state",
                "News state",
                50,
                50,
                ("evidence:1",),
                "source",
            )


if __name__ == "__main__":
    unittest.main()
