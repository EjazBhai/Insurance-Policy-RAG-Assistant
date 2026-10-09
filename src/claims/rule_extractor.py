
from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyRuleCandidate:
    rule_type: str
    source: str
    page: int
    excerpt: str
    verified: bool = False


RULE_PATTERNS = {
    "exclusion": (
        "excluded",
        "not covered",
        "shall not be covered",
        "exclusion",
    ),
    "waiting_period": (
        "waiting period",
        "after continuous coverage",
        "months of continuous coverage",
    ),
    "deductible": (
        "deductible",
        "deductibles",
        "excess amount",
    ),
    "copay": (
        "co-pay",
        "copay",
        "co-payment",
        "co payment",
    ),
    "sublimit": (
        "sub-limit",
        "sublimit",
        "limited to",
        "maximum payable",
        "up to a maximum",
    ),
    "coverage": (
        "is covered",
        "are covered",
        "shall be covered",
        "eligible expenses",
        "coverage includes",
    ),
}


def extract_rule_candidates(
    passages: list[dict],
) -> list[PolicyRuleCandidate]:
    """Identify possible policy rules without validating their meaning."""
    candidates = []
    seen = set()

    for passage in passages:
        text = str(passage.get("text", "")).strip()
        source = str(passage.get("source", "")).strip()

        try:
            page = int(passage.get("page"))
        except (TypeError, ValueError):
            continue

        if not text or not source or page < 1:
            continue

        normalized = text.casefold()

        # Avoid classifying negated exclusion statements as exclusions.
        

        # exclusion_is_negated = any(
        #     phrase in normalized
        #     for phrase in (
        #         "not excluded",
        #         "no exclusion",
        #         "isn't excluded",
        #         "is not excluded",
        #         "exclusion does not apply",
        #         "exclusion doesn't apply",
        #         "exclusion shall not apply",
        #         "exclusion will not apply",
        #         "exclusion is inapplicable",
        #     )
        # )

        
        review_phrases = (
            "exclusion does not apply",
            "exclusion doesn't apply",
            "exclusion shall not apply",
            "exclusion will not apply",
            "exclusion is inapplicable",
        )

        exclusion_is_negated = any(
            phrase in normalized
            for phrase in (
                "not excluded",
                "no exclusion",
                "isn't excluded",
                "is not excluded",
            )
        )

        requires_review = any(
            phrase in normalized for phrase in review_phrases
        )

        if requires_review:
            candidate = PolicyRuleCandidate(
                rule_type="review",
                source=source,
                page=page,
                excerpt=text,
            )
            key = ("review", source, page, text)

            if key not in seen:
                candidates.append(candidate)
                seen.add(key)

            continue


        for rule_type, phrases in RULE_PATTERNS.items():
            if rule_type == "exclusion" and exclusion_is_negated:
                continue
            if any(phrase in normalized for phrase in phrases):
                key = (rule_type, source, page, text)

                if key not in seen:
                    candidates.append(
                        PolicyRuleCandidate(
                            rule_type=rule_type,
                            source=source,
                            page=page,
                            excerpt=text,
                        )
                    )
                    seen.add(key)

    return candidates



