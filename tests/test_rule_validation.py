
from src.claims.rule_extractor import PolicyRuleCandidate
from src.claims.rule_validation import validate_rule_candidates


def test_unverified_candidate_requires_review():
    candidate = PolicyRuleCandidate(
        rule_type="coverage",
        source="policy.pdf",
        page=5,
        excerpt="Eligible hospitalization expenses are covered.",
    )

    result = validate_rule_candidates([candidate])

    assert result[0].status == "requires_review"


def test_conditional_clause_requires_review():
    candidate = PolicyRuleCandidate(
        rule_type="coverage",
        source="policy.pdf",
        page=6,
        excerpt="Hospitalization is covered subject to the waiting period.",
        verified=True,
    )

    result = validate_rule_candidates([candidate])

    assert result[0].status == "requires_review"
    assert result[0].reasons


def test_review_candidate_stays_in_review():
    candidate = PolicyRuleCandidate(
        rule_type="review",
        source="policy.pdf",
        page=10,
        excerpt="The exclusion does not apply in certain circumstances.",
        verified=False,
    )

    result = validate_rule_candidates([candidate])

    assert result[0].status == "requires_review"


def test_verified_unambiguous_candidate_passes_basic_checks():
    candidate = PolicyRuleCandidate(
        rule_type="coverage",
        source="policy.pdf",
        page=5,
        excerpt="Eligible hospitalization expenses are covered.",
        verified=True,
    )

    result = validate_rule_candidates([candidate])

    assert result[0].status == "candidate_validated"
