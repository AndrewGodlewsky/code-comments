"""Write the nightly export file: python -m ledger.nightly DB OUT.csv"""
import sys

from ledger.csv_out import write_rows
from ledger.db import connect
from ledger.rows import fetch_rows


def export(conn, fh):
    """Write every ledger row to fh as CSV."""
    write_rows(fetch_rows(conn), fh)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    db_path, out_path = argv
    conn = connect(db_path)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        export(conn, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
