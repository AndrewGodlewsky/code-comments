import io
import unittest

from stock.feed import write_feed
from stock.format import MAX_FEED_QTY, feed_line
from stock.rows import stock_rows


class FeedTest(unittest.TestCase):
    def test_rows_skip_empty_stock(self):
        self.assertEqual(stock_rows({"B": 2, "A": 0, "C": 5}), [("B", 2), ("C", 5)])

    def test_line_caps_quantity(self):
        self.assertEqual(feed_line("A", MAX_FEED_QTY + 1, "9.99"), f"A\t{MAX_FEED_QTY}\t9.99\n")

    def test_feed_skips_unpriced(self):
        out = io.StringIO()
        write_feed([("A", 12), ("B", 3)], [("A", "9.99")], out)
        self.assertEqual(out.getvalue(), "A\t12\t9.99\n")


if __name__ == "__main__":
    unittest.main()
