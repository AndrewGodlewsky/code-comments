"""Invoice lines."""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    quantity: int
    unit_price: Decimal
