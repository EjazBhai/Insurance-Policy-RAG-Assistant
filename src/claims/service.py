
from dataclasses import dataclass, field

from src.claims.calculator import estimate_payout
from src.claims.eligibility import (
    EligibilityResult,
    PolicyFinding,
    assess_eligibility,
)
from src.claims.schemas import Claim, Estimate, PolicyTerms


@dataclass
class ClaimAssessment:
    eligibility: EligibilityResult
    estimate: Estimate | None
    payout_status: str
    missing_information: list[str] = field(default_factory=list)


def assess_claim(
    claim: Claim,
    terms: PolicyTerms | None,
    findings: list[PolicyFinding],
    required_facts_complete: bool,
    missing_information: list[str] | None = None,
) -> ClaimAssessment:
    """Combine preliminary eligibility and deterministic payout estimation.

    A numeric estimate is produced only when:
    - required claim facts are complete;
    - applicable policy evidence is verified;
    - eligibility is likely covered; and
    - policy calculation terms have been supplied.
    """
    missing = list(missing_information or [])

    eligibility = assess_eligibility(
        findings=findings,
        required_facts_complete=required_facts_complete,
        missing_information=missing,
    )

    if eligibility.status != "likely_covered":
        return ClaimAssessment(
            eligibility=eligibility,
            estimate=None,
            payout_status="not_estimated",
            missing_information=eligibility.missing_information,
        )

    if terms is None:
        missing_terms = [
            "Verified policy calculation terms are required."
        ]
        eligibility.status = "requires_review"
        eligibility.reasons.append(
            "Eligibility evidence is available, but payout rules are missing."
        )
        eligibility.missing_information.extend(missing_terms)

        return ClaimAssessment(
            eligibility=eligibility,
            estimate=None,
            payout_status="not_estimated",
            missing_information=eligibility.missing_information,
        )

    # Do not run arithmetic on terms without evidence for each
    # non-default adjustment that is actually configured.
    required_rules = set()

    if terms.room_rent_cap_per_day is not None:
        required_rules.add("room_rent_cap")

    required_rules.update(
        f"sublimit_{category}" for category in terms.sublimits
    )

    if terms.deductible > 0:
        required_rules.add("deductible")

    if terms.copay_pct > 0:
        required_rules.add("copay")

    if terms.sum_insured_remaining < 0:
        eligibility.status = "requires_review"
        eligibility.reasons.append(
            "Remaining sum insured cannot be negative."
        )
        eligibility.missing_information.append(
            "A valid remaining sum insured."
        )
        return ClaimAssessment(
            eligibility=eligibility,
            estimate=None,
            payout_status="not_estimated",
            missing_information=eligibility.missing_information,
        )

    missing_rules = [
        rule for rule in sorted(required_rules)
        if not terms.clauses.get(rule, "").strip()
    ]

    if missing_rules:
        eligibility.status = "requires_review"
        eligibility.reasons.append(
            "Some configured payout adjustments lack policy references."
        )
        eligibility.missing_information.extend(
            f"Verified policy clause for {rule}."
            for rule in missing_rules
        )
        return ClaimAssessment(
            eligibility=eligibility,
            estimate=None,
            payout_status="not_estimated",
            missing_information=eligibility.missing_information,
        )

    estimate = estimate_payout(claim, terms)

    return ClaimAssessment(
        eligibility=eligibility,
        estimate=estimate,
        payout_status="estimated",
        missing_information=[],
    )

