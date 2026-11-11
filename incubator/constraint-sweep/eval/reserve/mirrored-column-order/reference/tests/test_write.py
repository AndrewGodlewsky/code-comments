import csv
import io
import unittest

from export.columns import COLUMNS
from export.write import write_export
from payments.model import payment


class WriteExportTest(unittest.TestCase):
    def test_one_field_per_column(self):
        buf = io.StringIO()
        write_export([payment("2026-11-01", "ACME Ltd", "12.50", "INV-1")], buf)
        (row,) = list(csv.reader(io.StringIO(buf.getvalue())))
        self.assertEqual(len(row), len(COLUMNS))
        self.assertEqual(row[COLUMNS.index("amount")], "12.50")

    def test_no_header_row(self):
        buf = io.StringIO()
        write_export([], buf)
        self.assertEqual(buf.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
