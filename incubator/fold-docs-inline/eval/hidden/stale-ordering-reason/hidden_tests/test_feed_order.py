import io
import unittest

from stock.feed import write_feed


class FeedOrderTest(unittest.TestCase):
    def test_rows_in_any_order_are_all_written(self):
        out = io.StringIO()
        write_feed([("C", 1), ("A", 2), ("B", 3)], [("B", "2"), ("C", "3"), ("A", "1")], out)
        self.assertEqual(out.getvalue(), "A\t2\t1\nB\t3\t2\nC\t1\t3\n")

    def test_unpriced_and_unstocked_skus_are_passed_over(self):
        out = io.StringIO()
        write_feed([("D", 4), ("B", 3)], [("C", "3"), ("B", "2"), ("A", "1")], out)
        self.assertEqual(out.getvalue(), "B\t3\t2\n")
