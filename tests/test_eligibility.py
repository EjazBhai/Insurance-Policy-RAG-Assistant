
from src.claims.eligibility import (
    PolicyFinding,
    assess_eligibility,
)


def make_finding(finding_type="coverage", verified=True):
    return PolicyFinding(
        rule_id="HEALTH-001",
        description="The treatment is covered under the applicable clause.",
        finding_type=finding_type,
        source="demo_policy.pdf",
        page=5,
        excerpt="Eligible treatment is covered subject to policy conditions.",
        verified=verified,
    )


def test_verified_coverage_is_likely_covered():
    result = assess_eligibility(
        findings=[make_finding()],
        required_facts_complete=True,
    )

    assert result.status == "likely_covered"
    assert len(result.evidence) == 1


def test_verified_exclusion_is_likely_excluded():
    result = assess_eligibility(
        findings=[make_finding("exclusion")],
        required_facts_complete=True,
    )

    assert result.status == "likely_excluded"


def test_incomplete_claim_requires_review():
    result = assess_eligibility(
        findings=[make_finding()],
        required_facts_complete=False,
    )

    assert result.status == "requires_review"
    assert result.missing_information


def test_no_findings_requires_review():
    result = assess_eligibility(
        findings=[],
        required_facts_complete=True,
    )

    assert result.status == "requires_review"


def test_unverified_policy_finding_requires_review():
    result = assess_eligibility(
        findings=[make_finding(verified=False)],
        required_facts_complete=True,
    )

    assert result.status == "requires_review"


def test_conflicting_coverage_and_exclusion_requires_review():
    result = assess_eligibility(
        findings=[
            make_finding("coverage"),
            make_finding("exclusion"),
        ],
        required_facts_complete=True,
    )

    assert result.status == "requires_review"
    assert result.missing_information


def test_unresolved_policy_condition_requires_review():
    result = assess_eligibility(
        findings=[make_finding("unresolved")],
        required_facts_complete=True,
    )

    assert result.status == "requires_review"


def test_missing_policy_source_requires_review():
    finding = make_finding()
    finding = PolicyFinding(
        rule_id=finding.rule_id,
        description=finding.description,
        finding_type=finding.finding_type,
        source="",
        page=finding.page,
        excerpt=finding.excerpt,
        verified=True,
    )

    result = assess_eligibility(
        findings=[finding],
        required_facts_complete=True,
    )

    assert result.status == "requires_review"
