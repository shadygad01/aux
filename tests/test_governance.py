import unittest
from datetime import UTC, datetime

from packages.application import ConstitutionalGovernance
from packages.domain import (
    AuthorityLevel,
    GovernanceActor,
    GovernanceChangeRequest,
    GovernanceEvidence,
    GovernanceVerdict,
    GovernedDomain,
)
from packages.infrastructure import InMemoryGovernanceAudit

NOW = datetime(2026, 8, 5, 12, tzinfo=UTC)


def request(
    authority: AuthorityLevel,
    domain: GovernedDomain,
    applied_by: GovernanceActor,
    evidence: GovernanceEvidence | None = None,
    requested_by: GovernanceActor = GovernanceActor.IMPLEMENTATION,
) -> GovernanceChangeRequest:
    return GovernanceChangeRequest(
        f"request-{authority.value}-{domain.value}-{applied_by.value}-{requested_by.value}",
        "artifact-1",
        authority,
        domain,
        requested_by,
        applied_by,
        "Governed change",
        evidence or GovernanceEvidence(),
        NOW,
    )


class GovernanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.audit = InMemoryGovernanceAudit()
        self.governance = ConstitutionalGovernance(self.audit, "governance-v1")

    def test_level_one_requires_owner_as_actor_and_explicit_approval(self) -> None:
        denied = self.governance.authorize(
            request(
                AuthorityLevel.IMMUTABLE_PRINCIPLE,
                GovernedDomain.IMMUTABLE_PRINCIPLES,
                GovernanceActor.IMPLEMENTATION,
            ),
            NOW,
        )
        self.assertEqual(denied.verdict, GovernanceVerdict.REJECTED)
        approved = self.governance.authorize(
            request(
                AuthorityLevel.IMMUTABLE_PRINCIPLE,
                GovernedDomain.IMMUTABLE_PRINCIPLES,
                GovernanceActor.PROJECT_OWNER,
                GovernanceEvidence(owner_approval_reference="owner:approval:1"),
            ),
            NOW,
        )
        self.assertEqual(approved.verdict, GovernanceVerdict.AUTHORIZED)

    def test_level_two_requires_all_four_gates_and_owner_application(self) -> None:
        incomplete = self.governance.authorize(
            request(
                AuthorityLevel.VALIDATED_TRADING_RULE,
                GovernedDomain.TRADING_CONSTITUTION,
                GovernanceActor.PROJECT_OWNER,
                GovernanceEvidence(research_references=("research:1",)),
            ),
            NOW,
        )
        self.assertEqual(incomplete.verdict, GovernanceVerdict.REJECTED)
        evidence = GovernanceEvidence(
            research_references=("research:1",),
            backtest_references=("backtest:1",),
            documentation_references=("docs:1",),
            owner_approval_reference="owner:approval:2",
        )
        approved = self.governance.authorize(
            request(
                AuthorityLevel.VALIDATED_TRADING_RULE,
                GovernedDomain.TRADING_CONSTITUTION,
                GovernanceActor.PROJECT_OWNER,
                evidence,
                GovernanceActor.RESEARCH,
            ),
            NOW,
        )
        self.assertEqual(approved.verdict, GovernanceVerdict.AUTHORIZED)

    def test_learning_and_research_cannot_apply_constitutional_changes(self) -> None:
        learning = self.governance.authorize(
            request(
                AuthorityLevel.VALIDATED_TRADING_RULE,
                GovernedDomain.TRADING_CONSTITUTION,
                GovernanceActor.LEARNING,
            ),
            NOW,
        )
        research = self.governance.authorize(
            request(
                AuthorityLevel.IMMUTABLE_PRINCIPLE,
                GovernedDomain.DECISION_CONSTITUTION,
                GovernanceActor.RESEARCH,
            ),
            NOW,
        )
        self.assertTrue(any("Learning" in reason for reason in learning.reasons))
        self.assertTrue(any("Research" in reason for reason in research.reasons))

    def test_lower_levels_enforce_logic_tests_and_domain_mapping(self) -> None:
        implementation = self.governance.authorize(
            request(
                AuthorityLevel.IMPLEMENTATION,
                GovernedDomain.IMPLEMENTATION,
                GovernanceActor.IMPLEMENTATION,
                GovernanceEvidence(logic_identical=True),
            ),
            NOW,
        )
        performance = self.governance.authorize(
            request(
                AuthorityLevel.PERFORMANCE_IMPROVEMENT,
                GovernedDomain.PERFORMANCE,
                GovernanceActor.AUTOMATION,
                GovernanceEvidence(test_references=("tests:1",)),
            ),
            NOW,
        )
        documentation = self.governance.authorize(
            request(
                AuthorityLevel.DOCUMENTATION,
                GovernedDomain.DOCUMENTATION,
                GovernanceActor.DOCUMENTATION,
            ),
            NOW,
        )
        mislabeled = self.governance.authorize(
            request(
                AuthorityLevel.DOCUMENTATION,
                GovernedDomain.TRADING_CONSTITUTION,
                GovernanceActor.DOCUMENTATION,
            ),
            NOW,
        )
        self.assertEqual(
            (implementation.verdict, performance.verdict, documentation.verdict),
            (GovernanceVerdict.AUTHORIZED,) * 3,
        )
        self.assertEqual(mislabeled.verdict, GovernanceVerdict.REJECTED)


if __name__ == "__main__":
    unittest.main()
