"""The payment record sent to the bank.

Its keys are the export's column names (export/columns.py) plus any the export does
not send.
"""


def payment(date, payee, amount, reference, currency="GBP"):
    """Return a payment record. amount is a decimal string such as "12.50"."""
    return {"date": date, "payee": payee, "amount": amount, "reference": reference, "currency": currency}
