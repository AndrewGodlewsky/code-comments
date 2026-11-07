def format_dollars(amount_cents):
    return f"${amount_cents / 100:.2f}"


def line_item(name, amount_cents):
    return f"{name}: {format_dollars(amount_cents)}"


def total_line(items):
    return line_item("Total", sum(amount for _, amount in items))
