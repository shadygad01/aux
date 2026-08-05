"""Fail-closed constitutional authorization without a mutation interface."""

from datetime import datetime
from typing import Protocol

from packages.domain import (
    AuthorityLevel,
    GovernanceActor,
    GovernanceChangeRequest,
    GovernanceDecision,
    GovernanceVerdict,
    GovernedDomain,
)


class GovernanceAudit(Protocol):
    def append(self, request: GovernanceChangeRequest, decision: GovernanceDecision) -> None: ...


class ConstitutionalGovernance:
    def __init__(self, audit: GovernanceAudit, policy_version: str) -> None:
        if not policy_version.strip():
            raise ValueError("governance policy version is required")
        self._audit = audit
        self._policy_version = policy_version

    def authorize(
        self, request: GovernanceChangeRequest, decided_at: datetime
    ) -> GovernanceDecision:
        failures = self._failures(request)
        verdict = GovernanceVerdict.REJECTED if failures else GovernanceVerdict.AUTHORIZED
        reasons = tuple(failures) or ("All authority and evidence gates passed.",)
        decision = GovernanceDecision(
            f"GOVERNANCE-{request.request_id}",
            request.request_id,
            verdict,
            reasons,
            decided_at,
            self._policy_version,
        )
        self._audit.append(request, decision)
        return decision

    @staticmethod
    def _failures(request: GovernanceChangeRequest) -> list[str]:
        evidence = request.evidence
        failures: list[str] = []
        expected_authority = {
            GovernedDomain.IMMUTABLE_PRINCIPLES: AuthorityLevel.IMMUTABLE_PRINCIPLE,
            GovernedDomain.TRADING_CONSTITUTION: AuthorityLevel.VALIDATED_TRADING_RULE,
            GovernedDomain.DECISION_CONSTITUTION: AuthorityLevel.IMMUTABLE_PRINCIPLE,
            GovernedDomain.IMPLEMENTATION: AuthorityLevel.IMPLEMENTATION,
            GovernedDomain.PERFORMANCE: AuthorityLevel.PERFORMANCE_IMPROVEMENT,
            GovernedDomain.DOCUMENTATION: AuthorityLevel.DOCUMENTATION,
        }
        if request.authority is not expected_authority[request.domain]:
            failures.append("The declared authority level does not match the governed domain.")
        minimum_level = {
            GovernanceActor.PROJECT_OWNER: AuthorityLevel.IMMUTABLE_PRINCIPLE,
            GovernanceActor.IMPLEMENTATION: AuthorityLevel.IMPLEMENTATION,
            GovernanceActor.AUTOMATION: AuthorityLevel.PERFORMANCE_IMPROVEMENT,
            GovernanceActor.DOCUMENTATION: AuthorityLevel.DOCUMENTATION,
        }.get(request.applied_by)
        if minimum_level is None or request.authority < minimum_level:
            failures.append("The applying actor lacks authority for this level.")
        if (
            request.domain is GovernedDomain.TRADING_CONSTITUTION
            and request.applied_by is GovernanceActor.LEARNING
        ):
            failures.append("Learning cannot modify the Trading Constitution.")
        if (
            request.domain is GovernedDomain.DECISION_CONSTITUTION
            and request.applied_by is GovernanceActor.RESEARCH
        ):
            failures.append("Research cannot modify the Decision Constitution.")
        if (
            request.authority
            in {
                AuthorityLevel.IMMUTABLE_PRINCIPLE,
                AuthorityLevel.VALIDATED_TRADING_RULE,
            }
            and request.applied_by is not GovernanceActor.PROJECT_OWNER
        ):
            failures.append("Only the project owner can apply Level 1 or Level 2 changes.")
        if (
            request.authority is AuthorityLevel.IMMUTABLE_PRINCIPLE
            and not evidence.owner_approval_reference
        ):
            failures.append("Level 1 requires explicit project-owner approval.")
        if request.authority is AuthorityLevel.VALIDATED_TRADING_RULE:
            if not evidence.research_references:
                failures.append("Level 2 requires research.")
            if not evidence.backtest_references:
                failures.append("Level 2 requires backtesting.")
            if not evidence.documentation_references:
                failures.append("Level 2 requires documentation.")
            if not evidence.owner_approval_reference:
                failures.append("Level 2 requires project-owner approval.")
        if request.authority is AuthorityLevel.IMPLEMENTATION and not evidence.logic_identical:
            failures.append("Level 3 changes must preserve identical logic.")
        if (
            request.authority is AuthorityLevel.PERFORMANCE_IMPROVEMENT
            and not evidence.test_references
        ):
            failures.append("Level 4 changes require passing test evidence.")
        return failures
