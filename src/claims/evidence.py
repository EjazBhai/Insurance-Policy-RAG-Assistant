
from src.claims.eligibility import PolicyFinding


def extract_evidence_candidates(
    passages: list[dict],
) -> list[PolicyFinding]:
    """Convert retrieved policy passages into unverified evidence candidates.

    Retrieval identifies potentially relevant text; it does not prove
    that the text establishes coverage or an exclusion.
    """
    findings = []

    for passage in passages:
        text = str(passage.get("text", "")).strip()
        source = str(passage.get("source", "")).strip()
        page = passage.get("page")

        if not text or not source:
            continue

        try:
            page_number = int(page)
        except (TypeError, ValueError):
            continue

        if page_number < 1:
            continue

        findings.append(
            PolicyFinding(
                rule_id=f"RETRIEVED-{passage.get('id', len(findings))}",
                description="Retrieved policy passage requiring review",
                finding_type="unresolved",
                source=source,
                page=page_number,
                excerpt=text,
                verified=False,
            )
        )

    return findings
