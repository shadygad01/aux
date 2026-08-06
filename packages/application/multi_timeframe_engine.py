"""Multi-Timeframe Scalping Engine implementation.

Cascades M5/M15 lower timeframe execution triggers from H1 higher timeframe structural bias.
Strictly blocks execution if lower timeframe signals contradict higher timeframe bias.
"""

from __future__ import annotations

from datetime import datetime

from packages.domain import (
    DecisionVerdict,
    ExecutionReadiness,
    MarketObservation,
    MarketThesis,
    MultiTimeframeThesis,
    StructureBias,
)


class MultiTimeframeEngine:
    """Evaluates M5/M15 lower timeframe triggers cascaded from H1 structural bias."""

    def evaluate_multi_timeframe(
        self,
        htf_thesis: MarketThesis,
        ltf_observation: MarketObservation,
        execution_readiness: ExecutionReadiness,
        evaluated_at: datetime,
    ) -> MultiTimeframeThesis:
        symbol = ltf_observation.symbol
        htf_bias = htf_thesis.verdict
        ltf_tf = ltf_observation.execution_timeframe

        # Check alignment
        reasons: list[str] = []
        ltf_bias = ltf_observation.structure.bias if ltf_observation.structure else None

        if htf_bias is DecisionVerdict.WAIT:
            cascade_status = "WAIT_HTF"
            reasons.append("Higher timeframe (H1) bias is WAIT. Execution blocked.")
            trigger = f"{ltf_tf} setup blocked by H1 WAIT status."
        elif ltf_bias == StructureBias.BEARISH and htf_bias is DecisionVerdict.BUY:
            cascade_status = "CONFLICT"
            reasons.append(f"{ltf_tf} structure opposes H1 BUY bias. Execution strictly blocked.")
            trigger = f"{ltf_tf} bearish structure contradicts H1 BUY bias."
        elif ltf_bias == StructureBias.BULLISH and htf_bias is DecisionVerdict.SELL:
            cascade_status = "CONFLICT"
            reasons.append(f"{ltf_tf} structure opposes H1 SELL bias. Execution strictly blocked.")
            trigger = f"{ltf_tf} bullish structure contradicts H1 SELL bias."
        else:
            cascade_status = "ALIGNED"
            reasons.append(f"H1 bias ({htf_bias}) is aligned with {ltf_tf} entry trigger.")
            if ltf_observation.structure and ltf_observation.structure.break_of_structure:
                reasons.append(f"{ltf_tf} structure confirms a break of structure with H1.")
                trigger = f"{ltf_tf} break of structure aligned with H1 {htf_bias}."
            else:
                trigger = f"{ltf_tf} structure aligned with H1 {htf_bias}; no {ltf_tf} BOS yet."

        tight_sl_pips = 12.5 if ltf_tf == "M5" else 18.0
        target_rr = 3.2 if ltf_tf == "M5" else 2.8

        return MultiTimeframeThesis(
            thesis_id=f"MTF-{evaluated_at.strftime('%Y%m%d')}-01",
            symbol=symbol,
            higher_timeframe="H1",
            execution_timeframe=ltf_tf,
            htf_bias=htf_bias,
            ltf_trigger=trigger,
            cascade_status=cascade_status,
            setup_quality_score=htf_thesis.setup_quality_score,
            execution_readiness=execution_readiness,
            tight_stop_loss_pips=tight_sl_pips,
            target_rr=target_rr,
            reasons=tuple(reasons),
            evaluated_at=evaluated_at,
        )
