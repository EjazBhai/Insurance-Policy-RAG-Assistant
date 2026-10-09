
from decimal import Decimal

from src.claims.eligibility import PolicyFinding
from src.claims.schemas import Claim, LineItem, PolicyTerms
from src.claims.service import assess_claim


def make_claim():
    return Claim(
        items=[
            LineItem(
                category="hospital",
                description="Hospital charges",
                amount=Decimal(10000),
                payable=True,
            )
        ]
    )


def make_terms():
    return PolicyTerms(
        sum_insured_remaining=Decimal(50000),
        deductible=Decimal(1000),
        copay_pct=Decimal(10),
        clauses={
            "deductible": "Policy clause 4.1",
            "copay": "Policy clause 4.2",
        },
    )


def make_coverage_finding():
    return PolicyFinding(
        rule_id="COV-001",
        description="Hospitalization is covered",
        finding_type="coverage",
        source="policy.pdf",
        page=5,
        excerpt="Eligible hospitalization expenses are covered.",
        verified=True,
    )


def test_covered_claim_produces_estimate():
    result = assess_claim(
        claim=make_claim(),
        terms=make_terms(),
        findings=[make_coverage_finding()],
        required_facts_complete=True,
    )

    assert result.eligibility.status == "likely_covered"
    assert result.estimate is not None
    assert result.payout_status == "estimated"


def test_incomplete_claim_does_not_estimate():
    result = assess_claim(
        claim=make_claim(),
        terms=make_terms(),
        findings=[make_coverage_finding()],
        required_facts_complete=False,
        missing_information=["Hospital admission date"],
    )

    assert result.eligibility.status == "requires_review"
    assert result.estimate is None
    assert result.payout_status == "not_estimated"


def test_missing_terms_does_not_estimate():
    result = assess_claim(
        claim=make_claim(),
        terms=None,
        findings=[make_coverage_finding()],
        required_facts_complete=True,
    )

    assert result.eligibility.status == "requires_review"
    assert result.estimate is None
    assert result.payout_status == "not_estimated"


def test_excluded_claim_does_not_estimate():
    exclusion = PolicyFinding(
        rule_id="EXC-001",
        description="Treatment is excluded",
        finding_type="exclusion",
        source="policy.pdf",
        page=8,
        excerpt="The specified treatment is excluded.",
        verified=True,
    )

    result = assess_claim(
        claim=make_claim(),
        terms=make_terms(),
        findings=[exclusion],
        required_facts_complete=True,
    )

    assert result.eligibility.status == "likely_excluded"
    assert result.estimate is None
    assert result.payout_status == "not_estimated"
