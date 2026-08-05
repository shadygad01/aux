"""Opportunity Identity Engine implementation.

Distinguishes between an aging opportunity and a completely new opportunity.
Ensures every opportunity receives a globally unique Opportunity ID that remains
constant throughout its lifetime. Generates a new Opportunity ID when a new liquidity
sweep or structural event creates a genuinely new setup.
"""

from __future__ import annotations

from datetime import datetime

from packages.domain import (
    DecisionVerdict,
    ExecutionReadiness,
    ExecutionStatus,
    MarketObservation,
    MarketThesis,
    OpportunityArchiveStatus,
    OpportunityIdentity,
    OpportunityLifecycleState,
    OpportunityOutcome,
)


class OpportunityIdentityEngine:
    """Manages globally unique Opportunity IDs and lifecycle states across observations."""

    def __init__(self) -> None:
        self._current_opportunity: OpportunityIdentity | None = None
        self._previous_opportunity: OpportunityIdentity | None = None
        self._counter: int = 1
        self._last_sweep_signature: str | None = None

    @property
    def current_opportunity(self) -> OpportunityIdentity | None:
        return self._current_opportunity

    @property
    def previous_opportunity(self) -> OpportunityIdentity | None:
        return self._previous_opportunity

    def _build_sweep_signature(
        self, observation: MarketObservation, verdict: DecisionVerdict
    ) -> str:
        symbol = observation.symbol
        dr = observation.dealing_range
        range_key = f"{dr.low:.1f}-{dr.high:.1f}" if dr else "no-range"
        liq_swept = "none"
        if observation.liquidity:
            swept_events = [
                f"{ev.side}:{ev.swept}:{ev.displacement_confirmed}"
                for ev in observation.liquidity
                if ev.swept
            ]
            if swept_events:
                liq_swept = "|".join(swept_events)
        return f"{symbol}:{verdict}:{range_key}:{liq_swept}"

    def evaluate_opportunity(
        self,
        observation: MarketObservation,
        thesis: MarketThesis,
        readiness: ExecutionReadiness,
        evaluated_at: datetime,
    ) -> tuple[OpportunityIdentity, OpportunityIdentity | None]:
        verdict = thesis.verdict
        sweep_sig = self._build_sweep_signature(observation, verdict)

        # Determine if this observation triggers a BRAND NEW opportunity
        is_new = (
            self._current_opportunity is None
            or self._current_opportunity.current_state
            in {
                OpportunityLifecycleState.COMPLETED,
                OpportunityLifecycleState.INVALIDATED,
                OpportunityLifecycleState.ARCHIVED,
            }
        )

        if not is_new and verdict is DecisionVerdict.WAIT:
            # Mandatory WAIT invalidates or completes previous active opportunity if active
            if self._current_opportunity and self._current_opportunity.current_state in {
                OpportunityLifecycleState.ACTIVE,
                OpportunityLifecycleState.AGING,
            }:
                archived_prev = OpportunityIdentity(
                    opportunity_id=self._current_opportunity.opportunity_id,
                    symbol=self._current_opportunity.symbol,
                    timeframe=self._current_opportunity.timeframe,
                    created_at=self._current_opportunity.created_at,
                    last_updated_at=evaluated_at,
                    creation_conditions=self._current_opportunity.creation_conditions,
                    verdict=self._current_opportunity.verdict,
                    setup_quality_score=self._current_opportunity.setup_quality_score,
                    max_setup_quality_score=self._current_opportunity.max_setup_quality_score,
                    execution_readiness=readiness,
                    current_state=OpportunityLifecycleState.INVALIDATED,
                    outcome=OpportunityOutcome.CANCELLED,
                    archive_status=OpportunityArchiveStatus.ARCHIVED,
                    is_fresh=False,
                )
                self._previous_opportunity = archived_prev
                self._current_opportunity = None
            is_new = True
        elif not is_new and self._last_sweep_signature != sweep_sig:
            is_new = True

        if is_new:
            # Move current opportunity to previous if present
            if self._current_opportunity is not None:
                self._previous_opportunity = OpportunityIdentity(
                    opportunity_id=self._current_opportunity.opportunity_id,
                    symbol=self._current_opportunity.symbol,
                    timeframe=self._current_opportunity.timeframe,
                    created_at=self._current_opportunity.created_at,
                    last_updated_at=evaluated_at,
                    creation_conditions=self._current_opportunity.creation_conditions,
                    verdict=self._current_opportunity.verdict,
                    setup_quality_score=self._current_opportunity.setup_quality_score,
                    max_setup_quality_score=self._current_opportunity.max_setup_quality_score,
                    execution_readiness=self._current_opportunity.execution_readiness,
                    current_state=OpportunityLifecycleState.ARCHIVED,
                    outcome=self._current_opportunity.outcome,
                    archive_status=OpportunityArchiveStatus.ARCHIVED,
                    is_fresh=False,
                )

            # Generate globally unique Opportunity ID: OPP-YYYYMMDD-XXX
            date_str = evaluated_at.strftime("%Y%m%d")
            opp_id = f"OPP-{date_str}-{self._counter:03d}"
            self._counter += 1

            conds: list[str] = []
            if observation.structure:
                b = observation.structure.bias
                bos = observation.structure.break_of_structure
                conds.append(f"Structure: {b} (BOS={bos})")
            if observation.dealing_range:
                dr = observation.dealing_range
                conds.append(
                    f"Dealing Range: [{dr.low:.1f} - {dr.high:.1f}] Price={dr.current_price:.1f}"
                )
            if observation.liquidity:
                for ev in observation.liquidity:
                    if ev.swept:
                        conds.append(
                            f"Liquidity Swept: {ev.side} (Displacement={ev.displacement_confirmed})"
                        )
            if not conds:
                conds.append("Initial market observation setup re-evaluation.")

            state = (
                OpportunityLifecycleState.CREATING
                if readiness.status == ExecutionStatus.WAIT
                else OpportunityLifecycleState.ACTIVE
            )
            outcome = OpportunityOutcome.PENDING

            new_opp = OpportunityIdentity(
                opportunity_id=opp_id,
                symbol=observation.symbol,
                timeframe=observation.timeframe,
                created_at=evaluated_at,
                last_updated_at=evaluated_at,
                creation_conditions=tuple(conds),
                verdict=verdict,
                setup_quality_score=thesis.setup_quality_score,
                max_setup_quality_score=thesis.setup_quality_score,
                execution_readiness=readiness,
                current_state=state,
                outcome=outcome,
                archive_status=OpportunityArchiveStatus.LIVE,
                is_fresh=True,
            )
            self._current_opportunity = new_opp
            self._last_sweep_signature = sweep_sig
            return new_opp, self._previous_opportunity

        # CONTINUATION of existing opportunity: preserve opportunity_id!
        curr = self._current_opportunity
        assert curr is not None

        new_max_quality = max(curr.max_setup_quality_score, thesis.setup_quality_score)

        if readiness.status == ExecutionStatus.EXPIRED:
            new_state = OpportunityLifecycleState.COMPLETED
            new_outcome = OpportunityOutcome.EXPIRED
        elif readiness.status == ExecutionStatus.LATE:
            new_state = OpportunityLifecycleState.AGING
            new_outcome = curr.outcome
        else:
            new_state = OpportunityLifecycleState.ACTIVE
            new_outcome = curr.outcome

        updated_opp = OpportunityIdentity(
            opportunity_id=curr.opportunity_id,
            symbol=curr.symbol,
            timeframe=curr.timeframe,
            created_at=curr.created_at,
            last_updated_at=evaluated_at,
            creation_conditions=curr.creation_conditions,
            verdict=verdict,
            setup_quality_score=thesis.setup_quality_score,
            max_setup_quality_score=new_max_quality,
            execution_readiness=readiness,
            current_state=new_state,
            outcome=new_outcome,
            archive_status=OpportunityArchiveStatus.LIVE,
            is_fresh=False,
        )
        self._current_opportunity = updated_opp
        return updated_opp, self._previous_opportunity
