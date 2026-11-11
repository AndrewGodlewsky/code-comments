import unittest

from exporter import config
from exporter.client import fetch_changed


class Ledger:
    def __init__(self, total):
        self.rows = list(range(total))
        self.requests = []

    def get(self, path, params, timeout):
        self.requests.append(dict(params, timeout=timeout))
        start = (params["page"] - 1) * params["per_page"]
        return self.rows[start:start + params["per_page"]]


class PageSizeTest(unittest.TestCase):
    def test_page_size_is_200(self):
        self.assertEqual(config.PAGE_SIZE, 200)

    def test_each_request_asks_for_200_rows(self):
        ledger = Ledger(450)
        self.assertEqual(len(list(fetch_changed(ledger, "2026-01-01"))), 450)
        self.assertEqual([r["per_page"] for r in ledger.requests], [200, 200, 200])
        self.assertEqual([r["page"] for r in ledger.requests], [1, 2, 3])

    def test_timeout_unchanged(self):
        self.assertEqual(config.REQUEST_TIMEOUT_S, 30)
        ledger = Ledger(1)
        list(fetch_changed(ledger, "2026-01-01"))
        self.assertEqual(ledger.requests[0]["timeout"], 30)
