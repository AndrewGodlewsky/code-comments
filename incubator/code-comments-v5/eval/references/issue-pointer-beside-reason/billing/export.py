"""Write invoice rows for the accounting system's nightly import."""


def format_amount(value):
    """Return value formatted for the export file."""
    # The finance vendor's importer rejects the whole file if any amount lacks
    # exactly two decimal places, and we cannot change it (#212).
    return f"{value:.2f}"


def export_row(invoice):
    """Return one CSV row for invoice: id, customer, amount."""
    return [invoice["id"], invoice["customer"], format_amount(invoice["amount"])]
