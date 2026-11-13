"""Filter order rows by change date and write them as CSV."""

import csv


def export_rows(source, since=None, output="-", stdout=None):
    """Copy rows from `source` to `output`, keeping those changed on or after `since`.

    Dates are ISO strings, so comparing them as text orders them correctly.
    Returns the number of rows written.
    """
    with open(source, newline="") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rows = [row for row in reader if not since or row["changed"] >= since]
    target = stdout if output == "-" else open(output, "w", newline="")
    try:
        writer = csv.DictWriter(target, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    finally:
        if target is not stdout:
            target.close()
    return len(rows)
