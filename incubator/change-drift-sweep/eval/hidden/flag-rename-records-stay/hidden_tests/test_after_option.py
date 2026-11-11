import contextlib
import csv
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path

from app.backfill import backfill
from app.cli import build_parser, main

ROWS = "id,changed\n1,2026-04-30\n2,2026-05-01\n3,2026-05-02\n"


def ids(text):
    return [row["id"] for row in csv.DictReader(io.StringIO(text))]


class AfterOptionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.source = self.dir / "orders.csv"
        self.source.write_text(ROWS, encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_after_filters_rows(self):
        out = io.StringIO()
        main(["export", str(self.source), "--after", "2026-05-01"], stdout=out)
        self.assertEqual(ids(out.getvalue()), ["2", "3"])

    def test_since_is_gone(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            build_parser().parse_args(["export", str(self.source), "--since", "2026-05-01"])

    def test_backfill_still_works(self):
        written = backfill(self.source, date(2026, 5, 1), self.dir, today=date(2026, 5, 2))
        self.assertEqual(ids(written[0].read_text(encoding="utf-8")), ["2", "3"])
        self.assertEqual(ids(written[1].read_text(encoding="utf-8")), ["3"])
