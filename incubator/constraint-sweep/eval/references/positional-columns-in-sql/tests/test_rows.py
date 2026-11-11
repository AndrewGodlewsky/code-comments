import unittest

from exporter.rows import cleared_entries

RECORD = {"id": "E-1", "account": "4000", "amount": "12.50", "currency": "EUR", "ts": "2026-11-01T09:00:00Z"}


class ClearedEntriesTest(unittest.TestCase):
    def test_skips_uncleared(self):
        records = [dict(RECORD, cleared=True), dict(RECORD, id="E-2", cleared=False)]
        self.assertEqual([entry.id for entry in cleared_entries(records)], ["E-1"])

    def test_memo_defaults_to_empty(self):
        self.assertEqual(cleared_entries([dict(RECORD, cleared=True)])[0].memo, "")


if __name__ == "__main__":
    unittest.main()
