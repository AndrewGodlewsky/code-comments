import io
import unittest
from datetime import datetime, timezone

from app.export import export_accounts
from app.schedule import next_export
from app.search import page


class SearchPagingTest(unittest.TestCase):
    def test_pages_hold_page_size_results(self):
        results = list(range(250))
        self.assertEqual(page(results, 1), list(range(100)))
        self.assertEqual(page(results, 3), list(range(200, 250)))


class ExportTest(unittest.TestCase):
    def test_writes_a_header_then_one_row_per_account(self):
        out = io.StringIO()
        export_accounts([{"account_id": 7, "email": "a@example.com", "plan": "pro", "deleted": False}], out)
        self.assertEqual(out.getvalue(), "account_id,email,plan,deleted\n7,a@example.com,pro,False\n")


class ScheduleTest(unittest.TestCase):
    def test_next_export_is_at_two_utc(self):
        now = datetime(2026, 3, 14, 1, 30, tzinfo=timezone.utc)
        self.assertEqual(next_export(now), datetime(2026, 3, 14, 2, 0, tzinfo=timezone.utc))

    def test_after_two_utc_the_next_export_is_tomorrow(self):
        now = datetime(2026, 3, 14, 9, 0, tzinfo=timezone.utc)
        self.assertEqual(next_export(now), datetime(2026, 3, 15, 2, 0, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
