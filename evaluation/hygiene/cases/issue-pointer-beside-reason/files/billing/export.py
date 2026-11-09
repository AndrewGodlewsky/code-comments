"""Write invoice rows for the accounting system's nightly import."""


def format_amount(value):
    """Return value formatted for the export file."""
    return str(value)


def export_row(invoice):
    """Return one CSV row for invoice: id, customer, amount."""
    return [invoice["id"], invoice["customer"], format_amount(invoice["amount"])]
