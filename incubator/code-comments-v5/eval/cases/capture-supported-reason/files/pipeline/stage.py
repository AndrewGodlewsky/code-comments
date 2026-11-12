"""Stage cleaned customer rows for the warehouse loader."""


def clean(row):
    """Return a copy of row with a trimmed id and a lower-case email."""
    return {**row, "customer_id": row["customer_id"].strip(), "email": row["email"].lower()}


def write_batch(rows, sink):
    for row in rows:
        sink.write(clean(row))
