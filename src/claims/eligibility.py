
from dataclasses import dataclass, field
from typing import Literal

EligibilityStatus = Literal[
    "likely_covered",
    "likely_excluded",
    "requires_review",
]

FindingType = Literal[
    "coverage",
    "exclusion",
    "unresolved",
]


@dataclass(frozen=True)
class PolicyFinding:
    """A finding based on an applicable policy clause."""

    rule_id: str
    description: str
    finding_type: FindingType
    source: str
    page: int
    excerpt: str
    verified: bool = False


@dataclass
class EligibilityResult:
    status: EligibilityStatus
    reasons: list[str] = field(default_factory=list)
    evidence: list[PolicyFinding] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)


def assess_eligibility(
    findings: list[PolicyFinding],
    required_facts_complete: bool,
    missing_information: list[str] | None = None,
) -> EligibilityResult:
    """Assess preliminary eligibility using explicit policy findings.

    This function does not interpret raw policy text, calculate payouts,
    or make a final insurance claim decision.
    """
    missing = list(missing_information or [])

    if not required_facts_complete:
        if not missing:
            missing.append("Required claim facts have not been verified.")

        return EligibilityResult(
            status="requires_review",
            reasons=["The claim information is incomplete."],
            missing_information=missing,
        )

    if not findings:
        return EligibilityResult(
            status="requires_review",
            reasons=["No applicable policy findings were supplied."],
            missing_information=[
                "Verified evidence for the applicable coverage terms."
            ],
        )

    # Every finding must be verified and traceable to policy evidence.
    for finding in findings:
        if (
            not finding.verified
            or not finding.rule_id.strip()
            or not finding.source.strip()
            or finding.page < 1
            or not finding.excerpt.strip()
        ):
            return EligibilityResult(
                status="requires_review",
                reasons=[
                    ("At least one policy finding lacks verified, "
                    "traceable evidence.")
                ],
                evidence=findings,
                missing_information=[
                    "Verified policy clause references and supporting text."
                ],
            )

    unresolved = [
        f for f in findings if f.finding_type == "unresolved"
    ]
    coverage = [
        f for f in findings if f.finding_type == "coverage"
    ]
    exclusions = [
        f for f in findings if f.finding_type == "exclusion"
    ]

    if unresolved:
        return EligibilityResult(
            status="requires_review",
            reasons=[
                "One or more applicable policy conditions remain unresolved."
            ],
            evidence=findings,
            missing_information=[
                "Clarification of the unresolved policy conditions."
            ],
        )

    if coverage and exclusions:
        return EligibilityResult(
            status="requires_review",
            reasons=[
                ("Both coverage-supporting and exclusion findings exist; "
                "their applicability must be reconciled.")
            ],
            evidence=findings,
            missing_information=[
                "Human review of the applicable coverage and exclusion clauses."
            ],
        )

    if exclusions:
        return EligibilityResult(
            status="likely_excluded",
            reasons=[f.description for f in exclusions],
            evidence=exclusions,
        )

    if coverage:
        return EligibilityResult(
            status="likely_covered",
            reasons=[f.description for f in coverage],
            evidence=coverage,
        )

    return EligibilityResult(
        status="requires_review",
        reasons=["No decisive coverage finding was established."],
        evidence=findings,
        missing_information=[
            "A verified finding establishing coverage or exclusion."
        ],
    )
