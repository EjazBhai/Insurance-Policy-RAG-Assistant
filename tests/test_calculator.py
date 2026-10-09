
from decimal import Decimal

from src.claims.calculator import estimate_payout
from src.claims.schemas import Claim, LineItem, PolicyTerms


def test_basic_payout_without_adjustments():
    claim = Claim(items=[
        LineItem("room", "Room charges", Decimal("10000")),
        LineItem("medicines", "Medicines", Decimal("5000")),
    ])
    terms = PolicyTerms(sum_insured_remaining=Decimal("50000"))

    result = estimate_payout(claim, terms)

    assert result.claimed == Decimal("15000.00")
    assert result.insurer_pays == Decimal("15000.00")
    assert result.patient_pays == Decimal("0.00")


def test_non_payable_item_is_excluded():
    claim = Claim(items=[
        LineItem("room", "Room charges", Decimal("10000")),
        LineItem(
            "consumables", "Excluded consumables",
            Decimal("1000"), payable=False,
        ),
    ])
    terms = PolicyTerms(sum_insured_remaining=Decimal("50000"))

    result = estimate_payout(claim, terms)

    assert result.claimed == Decimal("11000.00")
    assert result.insurer_pays == Decimal("10000.00")
    assert result.patient_pays == Decimal("1000.00")


def test_deductible_and_copay():
    claim = Claim(items=[
        LineItem("medicines", "Medicines", Decimal("10000")),
    ])
    terms = PolicyTerms(
        sum_insured_remaining=Decimal("50000"),
        deductible=Decimal("1000"),
        copay_pct=Decimal("20"),
    )

    result = estimate_payout(claim, terms)

    assert result.insurer_pays == Decimal("7200.00")
    assert result.patient_pays == Decimal("2800.00")


def test_sublimit_caps_category():
    claim = Claim(items=[
        LineItem("medicines", "Medicines", Decimal("10000")),
    ])
    terms = PolicyTerms(
        sum_insured_remaining=Decimal("50000"),
        sublimits={"medicines": Decimal("6000")},
    )

    result = estimate_payout(claim, terms)

    assert result.insurer_pays == Decimal("6000.00")
    assert result.patient_pays == Decimal("4000.00")


def test_remaining_sum_insured_caps_payout():
    claim = Claim(items=[
        LineItem("medicines", "Medicines", Decimal("20000")),
    ])
    terms = PolicyTerms(sum_insured_remaining=Decimal("12000"))

    result = estimate_payout(claim, terms)

    assert result.insurer_pays == Decimal("12000.00")
    assert result.patient_pays == Decimal("8000.00")


def test_room_rent_cap_and_proportionate_reduction():
    claim = Claim(
        items=[
            LineItem("room", "Room charges", Decimal("4000")),
            LineItem("surgeon", "Surgeon charges", Decimal("6000")),
        ],
        room_days=2,
    )
    terms = PolicyTerms(
        sum_insured_remaining=Decimal("50000"),
        room_rent_cap_per_day=Decimal("1000"),
    )

    result = estimate_payout(claim, terms)

    # Room rent is reduced from 4000 to 2000.
    # Surgeon charges are proportionately reduced from 6000 to 3000.
    assert result.insurer_pays == Decimal("5000.00")
    assert result.patient_pays == Decimal("5000.00")
