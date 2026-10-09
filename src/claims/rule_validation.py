
from dataclasses import dataclass

from src.claims.rule_extractor import PolicyRuleCandidate


@dataclass(frozen=True)
class RuleValidationResult:
    candidate: PolicyRuleCandidate
    status: str
    reasons: tuple[str, ...]


def validate_rule_candidates(
    candidates: list[PolicyRuleCandidate],
) -> list[RuleValidationResult]:
    """Flag ambiguity and conflicts without claiming policy verification.

    This validates candidate quality and consistency only. It does not
    establish legal applicability or authorize payout calculations.
    """
    results = []

    for candidate in candidates:
        text = candidate.excerpt.casefold()
        reasons = []

        if candidate.rule_type == "review":
            reasons.append("The clause was flagged as ambiguous.")

        if any(
            phrase in text
            for phrase in (
                "subject to",
                "unless",
                "except where",
                "in certain circumstances",
                "may be",
            )
        ):
            reasons.append(
                "The clause contains conditional or ambiguous language."
            )

        if not candidate.source.strip() or candidate.page < 1:
            reasons.append("The citation is incomplete.")

        if not candidate.excerpt.strip():
            reasons.append("The policy excerpt is empty.")

        if reasons or not candidate.verified:
            status = "requires_review"
            if not reasons:
                reasons.append(
                    "The extracted candidate has not been verified."
                )
        else:
            status = "candidate_validated"

        results.append(
            RuleValidationResult(
                candidate=candidate,
                status=status,
                reasons=tuple(reasons),
            )
        )

    return results
