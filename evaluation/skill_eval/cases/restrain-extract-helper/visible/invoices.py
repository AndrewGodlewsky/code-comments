from decimal import Decimal, ROUND_HALF_EVEN

TAX_RATE = Decimal("0.0825")


def line_amount(line):
    # Go through str(): Decimal(0.1) is 0.1000000000000000055511151231257827...,
    # and that binary noise would otherwise survive into the rounded totals.
    return Decimal(str(line["price"])) * line["qty"]


def invoice_total(lines):
    subtotal = sum((line_amount(line) for line in lines), Decimal("0"))
    # Round half to even, not half up: the ledger service rounds this way, and
    # half-up totals disagreed with it by a cent on reconciled invoices.
    return subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def credit_note_total(lines):
    subtotal = sum((line_amount(line) for line in lines), Decimal("0"))
    return -subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)


def tax_amount(lines):
    subtotal = sum((line_amount(line) for line in lines), Decimal("0"))
    return (subtotal * TAX_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_EVEN)
