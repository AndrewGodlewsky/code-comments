import csv
import io
import unittest

from ledger.db import add_entries, connect
from ledger.nightly import export

# Stored in clearing order, which is not id order.
ENTRIES = [("E-0004", "4000", 900, "rent"), ("E-0001", "4000", 120, "coffee"),
           ("E-0003", "4100", 75, ""), ("E-0002", "4100", 500, "fee")]


class BankUploadOrderTest(unittest.TestCase):
    def test_export_lists_every_entry_in_ascending_id_order(self):
        conn = connect()
        add_entries(conn, ENTRIES)
        buf = io.StringIO()
        export(conn, buf)
        ids = [line[0] for line in list(csv.reader(io.StringIO(buf.getvalue())))[1:]]
        self.assertEqual(ids, ["E-0001", "E-0002", "E-0003", "E-0004"])


if __name__ == "__main__":
    unittest.main()
