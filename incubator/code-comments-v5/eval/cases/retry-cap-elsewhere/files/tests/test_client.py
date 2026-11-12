import unittest

from fetcher.client import ReportUnavailable, fetch_report
from fetcher.config import MAX_RETRIES


class TimingOut:
    def __init__(self):
        self.calls = 0

    def get(self, path):
        self.calls += 1
        raise TimeoutError(path)


class Ok:
    def get(self, path):
        return "body"


class FetchReportTest(unittest.TestCase):
    def test_gives_up_after_the_retry_cap(self):
        session = TimingOut()
        with self.assertRaises(ReportUnavailable):
            fetch_report(session, "r1", sleep=lambda seconds: None)
        self.assertEqual(session.calls, MAX_RETRIES + 1)

    def test_returns_the_body(self):
        self.assertEqual(fetch_report(Ok(), "r1", sleep=lambda seconds: None), "body")


if __name__ == "__main__":
    unittest.main()
