import io
import unittest

from export.columns import COLUMNS
from export.write import write_export
from ingest.read import read_export
from payments.model import payment


class RoundTripTest(unittest.TestCase):
    def test_every_field_reads_back_under_its_name(self):
        records = [payment("2026-11-01", "ACME Ltd", "12.50", "INV-1", "EUR"),
                   payment("2026-11-02", "Bolt & Co", "3.20", "INV-2", "CHF")]
        buf = io.StringIO()
        write_export(records, buf)
        back = read_export(io.StringIO(buf.getvalue()))
        currency = [column for column in COLUMNS if "currency" in column.lower()]
        self.assertEqual(len(currency), 1, COLUMNS)
        self.assertEqual(len(back), 2)
        for sent, read in zip(records, back):
            for key in ("date", "payee", "amount", "reference"):
                self.assertEqual(read.get(key), sent[key], key)
            self.assertEqual(read.get(currency[0]), sent["currency"])


if __name__ == "__main__":
    unittest.main()
