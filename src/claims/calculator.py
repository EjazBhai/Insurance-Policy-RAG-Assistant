from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from src.claims.schemas import Claim, Estimate, PolicyTerms, Step

CENT = Decimal("0.01")


def q(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def estimate_payout(claim: Claim, terms: PolicyTerms) -> Estimate:
    """Deterministic payout estimate. Every adjustment is recorded as a Step,
    so the result is fully explainable. No LLM is involved in the arithmetic."""
    steps = []
    ref = terms.clauses.get

    totals = defaultdict(Decimal)
    claimed = Decimal("0")
    for it in claim.items:
        claimed += it.amount
        if it.payable:
            totals[it.category] += it.amount

    running = sum(totals.values(), Decimal("0"))
    steps.append(Step("non_payable_items",
                      "Removed items the policy does not pay for",
                      claimed, running, ref("non_payable_items", "")))

    # 1) Room rent cap with proportionate deduction on related charges
    cap = terms.room_rent_cap_per_day
    if cap is not None and claim.room_days > 0 and totals["room"] > 0:
        actual = totals["room"] / claim.room_days
        if actual > cap:
            factor = cap / actual
            before = running
            totals["room"] = cap * claim.room_days
            for cat in terms.proportionate:
                if cat in totals:
                    totals[cat] = totals[cat] * factor
            running = sum(totals.values(), Decimal("0"))
            steps.append(Step(
                "room_rent_cap",
                f"Room rent {q(actual)}/day exceeds cap {q(cap)}/day; room capped and "
                f"related charges reduced to {q(factor * 100)}%",
                before, running, ref("room_rent_cap", "")))

    # 2) Sub-limits per category
    for cat, limit in terms.sublimits.items():
        if totals.get(cat, Decimal("0")) > limit:
            before = running
            totals[cat] = limit
            running = sum(totals.values(), Decimal("0"))
            steps.append(Step(f"sublimit_{cat}",
                              f"{cat} limited to {q(limit)}",
                              before, running, ref(f"sublimit_{cat}", "")))

    # 3) Deductible, then 4) co-pay (order is policy-specific: confirm in the wording)
    if terms.deductible > 0:
        before = running
        running = max(running - terms.deductible, Decimal("0"))
        steps.append(Step("deductible", f"Deductible {q(terms.deductible)} applied",
                          before, running, ref("deductible", "")))
    if terms.copay_pct > 0:
        before = running
        running = running * (Decimal("1") - terms.copay_pct / Decimal("100"))
        steps.append(Step("copay", f"Co-payment {terms.copay_pct}% applied",
                          before, running, ref("copay", "")))

    # 5) Cannot exceed remaining sum insured
    if running > terms.sum_insured_remaining:
        before = running
        running = terms.sum_insured_remaining
        steps.append(Step("sum_insured_cap",
                          f"Limited to remaining sum insured {q(running)}",
                          before, running, ref("sum_insured_cap", "")))

    pays = q(running)
    for s in steps:
        s.before, s.after = q(s.before), q(s.after)
    return Estimate(q(claimed), pays, q(claimed - pays), steps)