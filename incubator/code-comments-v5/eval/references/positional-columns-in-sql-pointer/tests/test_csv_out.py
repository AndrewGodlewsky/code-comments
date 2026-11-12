import csv
import io
import unittest

from exporter.csv_out import write_csv
from exporter.rows import Entry

ENTRY = Entry("E-1", "4000", "12.50", "EUR", "2026-11-01T09:00:00Z")


class WriteCsvTest(unittest.TestCase):
    def rows(self, entries):
        buf = io.StringIO()
        write_csv(entries, buf)
        return list(csv.reader(io.StringIO(buf.getvalue())))

    def test_header_names_the_columns(self):
        header = self.rows([])[0]
        for name in ("id", "account", "amount", "ts"):
            self.assertIn(name, header)

    def test_one_row_per_entry(self):
        self.assertEqual(len(self.rows([ENTRY, ENTRY])), 3)

    def test_amount_is_written_as_given(self):
        header, row = self.rows([ENTRY])
        self.assertEqual(row[header.index("amount")], "12.50")


if __name__ == "__main__":
    unittest.main()
