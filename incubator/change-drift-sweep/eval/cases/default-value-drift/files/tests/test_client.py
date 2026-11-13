import unittest
from contextlib import contextmanager

from exporter.client import fetch_changed
from exporter.config import PAGE_SIZE
from exporter.sync import run_sync


class FakeLedger:
    def __init__(self, total):
        self.rows = [{"id": i} for i in range(total)]
        self.requests = []

    def get(self, path, params, timeout):
        self.requests.append(params)
        start = (params["page"] - 1) * params["per_page"]
        return self.rows[start:start + params["per_page"]]


class FakeWarehouse:
    def __init__(self):
        self.written = []

    @contextmanager
    def transaction(self):
        pending = []

        class Tx:
            def upsert(self, table, row):
                pending.append((table, row))

        yield Tx()
        self.written.extend(pending)


class FetchChangedTest(unittest.TestCase):
    def test_reads_every_page(self):
        ledger = FakeLedger(PAGE_SIZE * 2 + 3)
        rows = list(fetch_changed(ledger, "2026-01-01"))
        self.assertEqual(len(rows), PAGE_SIZE * 2 + 3)
        self.assertEqual([r["page"] for r in ledger.requests], [1, 2, 3])

    def test_asks_for_a_full_page(self):
        ledger = FakeLedger(5)
        list(fetch_changed(ledger, "2026-01-01"))
        self.assertEqual(ledger.requests[0]["per_page"], PAGE_SIZE)


class RunSyncTest(unittest.TestCase):
    def test_writes_every_row(self):
        warehouse = FakeWarehouse()
        self.assertEqual(run_sync(FakeLedger(7), warehouse, "2026-01-01"), 7)
        self.assertEqual(len(warehouse.written), 7)


if __name__ == "__main__":
    unittest.main()
