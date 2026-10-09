
from src.claims.rule_extractor import extract_rule_candidates


def test_detects_coverage_candidate():
    result = extract_rule_candidates([
        {
            "text": "Eligible hospitalization expenses are covered.",
            "source": "policy.pdf",
            "page": 5,
        }
    ])

    assert len(result) == 1
    assert result[0].rule_type == "coverage"
    assert result[0].verified is False


def test_detects_exclusion_candidate():
    result = extract_rule_candidates([
        {
            "text": "Dental treatment is excluded.",
            "source": "policy.pdf",
            "page": 8,
        }
    ])

    assert len(result) == 1
    assert result[0].rule_type == "exclusion"


def test_detects_multiple_rule_categories():
    result = extract_rule_candidates([
        {
            "text": (
                "Hospitalization is covered subject to a 10% co-pay "
                "and a 30-day waiting period."
            ),
            "source": "policy.pdf",
            "page": 6,
        }
    ])

    categories = {item.rule_type for item in result}

    assert categories == {"coverage", "copay", "waiting_period"}


def test_skips_invalid_passages():
    result = extract_rule_candidates([
        {"text": "This is covered."},
        {
            "text": "This is covered.",
            "source": "policy.pdf",
            "page": 0,
        },
    ])

    assert result == []


def test_preserves_policy_citation():
    result = extract_rule_candidates([
        {
            "text": "The maximum payable amount is limited to the stated sublimit.",
            "source": "policy.pdf",
            "page": 12,
        }
    ])

    assert result
    assert result[0].source == "policy.pdf"
    assert result[0].page == 12
    assert result[0].excerpt == (
        "The maximum payable amount is limited to the stated sublimit."
    )
    assert result[0].verified is False
