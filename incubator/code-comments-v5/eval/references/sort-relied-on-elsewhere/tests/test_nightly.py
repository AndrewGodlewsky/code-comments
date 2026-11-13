import csv
import io
import unittest

from ledger.db import add_entries, connect
from ledger.nightly import export


class ExportTest(unittest.TestCase):
    def test_writes_a_header_and_every_row(self):
        conn = connect()
        add_entries(conn, [("E-0002", "4000", 500, "rent"), ("E-0001", "4100", 120, "coffee")])
        buf = io.StringIO()
        export(conn, buf)
        lines = list(csv.reader(io.StringIO(buf.getvalue())))
        self.assertEqual(lines[0], ["id", "account", "amount", "memo"])
        self.assertEqual({tuple(line) for line in lines[1:]},
                         {("E-0001", "4100", "1.20", "coffee"), ("E-0002", "4000", "5.00", "rent")})


if __name__ == "__main__":
    unittest.main()
