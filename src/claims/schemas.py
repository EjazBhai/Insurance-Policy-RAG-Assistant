from dataclasses import dataclass, field
from decimal import Decimal


def D(x) -> Decimal:
    return Decimal(str(x))


@dataclass
class LineItem:
    category: str  # room, icu, surgeon, anesthesia, ot, procedure, medicines, diagnostics, consumables, other
    description: str
    amount: Decimal
    payable: bool = True  # False for non-payable items (e.g. consumables)


@dataclass
class Claim:
    items: list
    room_days: int = 0


@dataclass
class PolicyTerms:
    sum_insured_remaining: Decimal
    room_rent_cap_per_day: Decimal | None = None
    deductible: Decimal = Decimal(0)
    copay_pct: Decimal = Decimal(0)
    sublimits: dict = field(default_factory=dict)  # category -> max payable
    proportionate: frozenset = frozenset({"surgeon", "anesthesia", "ot", "procedure"})
    clauses: dict = field(default_factory=dict)    # rule name -> citation text


@dataclass
class Step:
    rule: str
    detail: str
    before: Decimal
    after: Decimal
    clause: str = ""


@dataclass
class Estimate:
    claimed: Decimal
    insurer_pays: Decimal
    patient_pays: Decimal
    steps: list