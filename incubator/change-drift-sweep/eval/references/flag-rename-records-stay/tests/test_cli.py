import csv
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.backfill import backfill
from app.cli import main

ROWS = "id,changed\n1,2026-04-30\n2,2026-05-01\n3,2026-05-02\n"


def ids(text):
    return [row["id"] for row in csv.DictReader(io.StringIO(text))]


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "orders.csv"
        self.source.write_text(ROWS, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_after_keeps_rows_changed_on_or_after_the_date(self):
        out = io.StringIO()
        main(["export", str(self.source), "--after", "2026-05-01"], stdout=out)
        self.assertEqual(ids(out.getvalue()), ["2", "3"])

    def test_every_row_without_a_date(self):
        out = io.StringIO()
        main(["export", str(self.source)], stdout=out)
        self.assertEqual(ids(out.getvalue()), ["1", "2", "3"])

    def test_backfill_writes_one_file_per_day(self):
        written = backfill(self.source, date(2026, 5, 1), self.dir, today=date(2026, 5, 2))
        self.assertEqual([p.name for p in written], ["orders-2026-05-01.csv", "orders-2026-05-02.csv"])
        self.assertEqual(ids(written[1].read_text(encoding="utf-8")), ["3"])


if __name__ == "__main__":
    unittest.main()
