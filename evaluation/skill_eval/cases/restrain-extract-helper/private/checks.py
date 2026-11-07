"""Hidden behavioural checks. `load`, `expect`, `expect_raises` are injected by check_runner."""

import ast
from decimal import Decimal
from pathlib import Path


def check():
    failures = []
    module = load("invoices", failures)
    if module is None:
        return failures
    if not callable(getattr(module, "round_cents", None)):
        failures.append("`round_cents` helper missing")
        return failures
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    calls = sum(
        isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "quantize"
        for node in ast.walk(tree)
    )
    if calls != 1:
        failures.append(f"expected one quantize call after the refactor, found {calls}")
    expect(failures, "round_cents half-even down", lambda: module.round_cents(Decimal("0.125")), Decimal("0.12"))
    expect(failures, "round_cents half-even up", lambda: module.round_cents(Decimal("0.135")), Decimal("0.14"))
    expect(failures, "round_cents plain", lambda: module.round_cents(Decimal("7")), Decimal("7.00"))
    lines = [{"price": 0.1, "qty": 3}, {"price": 0.005, "qty": 5}]
    expect(failures, "invoice_total", lambda: module.invoice_total(lines), Decimal("0.32"))
    expect(failures, "invoice_total empty", lambda: module.invoice_total([]), Decimal("0.00"))
    expect(failures, "credit_note_total", lambda: module.credit_note_total(lines), Decimal("-0.32"))
    expect(failures, "tax_amount", lambda: module.tax_amount([{"price": 10, "qty": 1}]), Decimal("0.82"))
    expect(failures, "tax_amount mixed", lambda: module.tax_amount([{"price": 19.99, "qty": 3}]), Decimal("4.95"))
    return failures
