
from src.claims.evidence import extract_evidence_candidates


def test_extracts_passage_as_unverified_candidate():
    passages = [
        {
            "id": "doc-1",
            "text": "Eligible hospitalization expenses are covered.",
            "source": "policy.pdf",
            "page": 5,
        }
    ]

    findings = extract_evidence_candidates(passages)

    assert len(findings) == 1
    assert findings[0].source == "policy.pdf"
    assert findings[0].page == 5
    assert findings[0].excerpt == (
        "Eligible hospitalization expenses are covered."
    )
    assert findings[0].finding_type == "unresolved"
    assert findings[0].verified is False


def test_skips_passage_without_source():
    findings = extract_evidence_candidates(
        [{"id": "doc-2", "text": "Some policy text.", "page": 2}]
    )

    assert findings == []


def test_skips_invalid_page():
    findings = extract_evidence_candidates(
        [{
            "id": "doc-3",
            "text": "Some policy text.",
            "source": "policy.pdf",
            "page": 0,
        }]
    )

    assert findings == []


def test_empty_passages_return_empty_list():
    assert extract_evidence_candidates([]) == []



def test_preserves_citations_for_multiple_passages():
    passages = [
        {
            "id": "doc-1",
            "text": "Hospitalization is covered subject to terms.",
            "source": "policy.pdf",
            "page": 5,
        },
        {
            "id": "doc-2",
            "text": "Certain treatments are excluded.",
            "source": "exclusions.pdf",
            "page": 12,
        },
    ]

    findings = extract_evidence_candidates(passages)

    assert len(findings) == 2
    assert [(f.source, f.page) for f in findings] == [
        ("policy.pdf", 5),
        ("exclusions.pdf", 12),
    ]
    assert all(f.verified is False for f in findings)
    assert all(f.finding_type == "unresolved" for f in findings)
