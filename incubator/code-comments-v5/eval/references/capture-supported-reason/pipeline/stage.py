"""Stage cleaned customer rows for the warehouse loader."""


def clean(row):
    """Return a copy of row with a trimmed id and a lower-case email."""
    return {**row, "customer_id": row["customer_id"].strip(), "email": row["email"].lower()}


def write_batch(rows, sink):
    # The warehouse loader merge-joins each batch against the previous snapshot
    # on customer_id in a single pass, and silently skips rows that arrive out of
    # order, so the batch must be written sorted by customer_id.
    for row in sorted((clean(row) for row in rows), key=lambda row: row["customer_id"]):
        sink.write(row)
