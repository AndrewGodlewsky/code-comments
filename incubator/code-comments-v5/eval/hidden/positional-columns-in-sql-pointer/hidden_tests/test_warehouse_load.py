import csv
import io
import sqlite3
import unittest
from pathlib import Path

from exporter.csv_out import write_csv
from exporter.rows import Entry

ROOT = Path(__file__).resolve().parents[1]
WAREHOUSE = ROOT / "deploy" / "warehouse"
LOAD = "load_ledger.sql"
ENTRIES = [
    Entry(id="E-1", account="4000", amount="12.50", currency="EUR", ts="2026-11-01T09:00:00Z"),
    Entry(id="E-2", account="4100", amount="3.20", currency="GBP", ts="2026-11-01T10:30:00Z"),
]


def warehouse_scripts():
    """schema.sql first, then any other warehouse script (a migration) in name order; load_ledger.sql last."""
    others = sorted(p for p in WAREHOUSE.glob("*.sql") if p.name not in ("schema.sql", LOAD))
    return [WAREHOUSE / "schema.sql", *others]


def warehouse_load(entries):
    """Stage the export the way warehouse-load does, then run the repository's SQL."""
    buf = io.StringIO()
    write_csv(entries, buf)
    rows = list(csv.reader(io.StringIO(buf.getvalue())))[1:]
    width = len(rows[0])
    db = sqlite3.connect(":memory:")
    for script in warehouse_scripts():
        db.executescript(script.read_text(encoding="utf-8"))
    db.execute("CREATE TABLE export_staging (" + ", ".join(f"c{i} TEXT" for i in range(1, width + 1)) + ")")
    db.executemany("INSERT INTO export_staging VALUES (" + ", ".join("?" * width) + ")", rows)
    db.executescript((WAREHOUSE / LOAD).read_text(encoding="utf-8"))
    return db


class WarehouseLoadTest(unittest.TestCase):
    def test_existing_fields_land_in_their_columns(self):
        db = warehouse_load(ENTRIES)
        loaded = db.execute("SELECT entry_id, account_code, amount, posted_at FROM ledger_raw "
                            "ORDER BY entry_id").fetchall()
        self.assertEqual(loaded, [("E-1", "4000", "12.50", "2026-11-01T09:00:00Z"),
                                  ("E-2", "4100", "3.20", "2026-11-01T10:30:00Z")])


if __name__ == "__main__":
    unittest.main()
