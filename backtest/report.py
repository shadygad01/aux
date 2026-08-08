"""Writes backtest_report.json (machine-readable) and backtest_report.md
(human-readable) -- deliberately not reusing publish/generators' envelope
machinery, which is publish-pipeline-specific; this tool is not wired into
that pipeline.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from packages.domain import DecisionPolicy

from .statistics import BacktestSummary
from .trade_simulator import AMBIGUOUS_CANDLE_RULE, METHODOLOGY_NOTE_ATR_TIMEFRAME, SimulatedTrade
from .walk_forward import WINDOW_CANDLES


def _summary_to_dict(summary: BacktestSummary) -> dict[str, object]:
    return {
        "total_signals": summary.total_signals,
        "total_buy": summary.total_buy,
        "total_sell": summary.total_sell,
        "win_rate_overall": summary.win_rate_overall,
        "win_rate_buy": summary.win_rate_buy,
        "win_rate_sell": summary.win_rate_sell,
        "average_rr_overall": summary.average_rr_overall,
        "average_rr_buy": summary.average_rr_buy,
        "average_rr_sell": summary.average_rr_sell,
        "target_hit_count": summary.target_hit_count,
        "stop_hit_count": summary.stop_hit_count,
        "open_at_end_count": summary.open_at_end_count,
        "no_risk_guidance_count": summary.no_risk_guidance_count,
    }


def _trade_to_dict(trade: SimulatedTrade) -> dict[str, object]:
    return {
        "signal_index": trade.signal.index,
        "signal_timestamp": trade.signal.decision.evaluated_at.isoformat(),
        "verdict": str(trade.signal.decision.verdict),
        "entry_price": trade.risk_guidance.entry_price,
        "stop_loss_price": trade.risk_guidance.stop_loss_price,
        "target_price": trade.risk_guidance.target_price,
        "planned_risk_reward": trade.risk_guidance.risk_reward,
        "outcome": str(trade.outcome),
        "exit_index": trade.exit_index,
        "achieved_rr": trade.achieved_rr,
    }


def write_report(
    output_dir: Path,
    *,
    ticker: str,
    policy: DecisionPolicy,
    candle_count: int,
    data_start: datetime | None,
    data_end: datetime | None,
    summary: BacktestSummary,
    trades: list[SimulatedTrade],
    sensitivity: dict[float, BacktestSummary] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    run_metadata = {
        "generated_at": datetime.now(UTC).isoformat(),
        "ticker": ticker,
        "window_candles": WINDOW_CANDLES,
        "candle_count": candle_count,
        "data_start": data_start.isoformat() if data_start else None,
        "data_end": data_end.isoformat() if data_end else None,
        "policy": {
            "version": policy.version,
            "equilibrium_band": policy.equilibrium_band,
            "attention_threshold": policy.attention_threshold,
            "structure_weight": policy.structure_weight,
            "location_weight": policy.location_weight,
            "liquidity_weight": policy.liquidity_weight,
        },
        "ambiguous_candle_rule": AMBIGUOUS_CANDLE_RULE,
        "methodology_notes": [METHODOLOGY_NOTE_ATR_TIMEFRAME],
    }

    json_payload = {
        "run": run_metadata,
        "summary": _summary_to_dict(summary),
        "sensitivity_sweep": (
            {str(k): _summary_to_dict(v) for k, v in sensitivity.items()} if sensitivity else None
        ),
        "trades": [_trade_to_dict(t) for t in trades],
    }
    (output_dir / "backtest_report.json").write_text(
        json.dumps(json_payload, indent=2), encoding="utf-8"
    )
    (output_dir / "backtest_report.md").write_text(
        _render_markdown(run_metadata, summary, sensitivity), encoding="utf-8"
    )


def _render_markdown(
    run_metadata: dict[str, object],
    summary: BacktestSummary,
    sensitivity: dict[float, BacktestSummary] | None,
) -> str:
    lines: list[str] = [
        "# Backtest Report",
        "",
        "## Run parameters",
        "",
        f"- Ticker: `{run_metadata['ticker']}`",
        f"- Generated at: {run_metadata['generated_at']}",
        f"- Window (candles per observation): {run_metadata['window_candles']}",
        f"- Policy version: `{run_metadata['policy']['version']}`",  # type: ignore[index]
        "",
        "## Data coverage actually obtained",
        "",
        f"- Candle count: {run_metadata['candle_count']}",
        f"- Data start: {run_metadata['data_start']}",
        f"- Data end: {run_metadata['data_end']}",
        (
            "- **Note:** Yahoo's real intraday history limit is not assumed by this "
            "tool -- the range above is what was actually returned, not a requested "
            "target. Treat a shorter-than-expected range as the discovered boundary, "
            "not a bug."
        ),
        "",
        "## Summary statistics",
        "",
        "| Metric | Overall | BUY | SELL |",
        "|---|---|---|---|",
        (f"| Signals | {summary.total_signals} | {summary.total_buy} | {summary.total_sell} |"),
        (
            f"| Win rate | {summary.win_rate_overall} | {summary.win_rate_buy} | "
            f"{summary.win_rate_sell} |"
        ),
        (
            f"| Average R:R | {summary.average_rr_overall} | {summary.average_rr_buy} | "
            f"{summary.average_rr_sell} |"
        ),
        "",
        (
            f"Target hit: {summary.target_hit_count} · Stop hit: {summary.stop_hit_count} · "
            f"Open at end of data: {summary.open_at_end_count} · "
            f"No risk guidance: {summary.no_risk_guidance_count}"
        ),
        "",
    ]

    if sensitivity:
        lines += [
            "## Sensitivity sweep (attention_threshold)",
            "",
            "| Threshold | Signals | Win rate | Avg R:R |",
            "|---|---|---|---|",
        ]
        for threshold, s in sorted(sensitivity.items()):
            lines.append(
                f"| {threshold} | {s.total_signals} | {s.win_rate_overall} | "
                f"{s.average_rr_overall} |"
            )
        lines.append("")

    lines += [
        "## Caveats",
        "",
        f"- **Risk model:** {run_metadata['methodology_notes'][0]}",  # type: ignore[index]
        (
            f"- **Ambiguous candles:** when a single candle's range touches both the "
            f"stop and the target, this backtest classifies it as "
            f"`{run_metadata['ambiguous_candle_rule']}` -- a deliberate conservative "
            "choice, not a modeling gap."
        ),
        (
            "- **Signal counting:** one signal is recorded per verdict transition "
            "(edge-triggered), not per candle a setup remains valid. A different "
            "counting convention would change these totals but not the underlying "
            "trades."
        ),
        (
            f"- **Open trades:** {summary.open_at_end_count} signal(s) never resolved "
            "before the data ended and are excluded from win rate / R:R, not counted "
            "as either a win or a loss."
        ),
    ]
    return "\n".join(lines) + "\n"
