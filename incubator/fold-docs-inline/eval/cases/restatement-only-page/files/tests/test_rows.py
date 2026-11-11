import os
import tempfile
import unittest

from ingest.rows import clean, parse_price, read_rows


class RowsTest(unittest.TestCase):
    def test_parse_price_accepts_dot_and_comma(self):
        self.assertEqual(parse_price("12.50"), 1250)
        self.assertEqual(parse_price("12,5"), 1250)
        self.assertEqual(parse_price(" 3 "), 300)

    def test_clean_drops_blank_rows(self):
        rows = [{"sku": "a", "price": "1.00"}, {"sku": " ", "price": ""}]
        self.assertEqual(clean(rows), [{"sku": "a", "price": 100}])

    def test_read_rows_uses_the_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "prices.csv")
            with open(path, "w", newline="", encoding="utf-8") as handle:
                handle.write("sku,price\nA1,2.00\n")
            self.assertEqual(read_rows(path), [{"sku": "A1", "price": "2.00"}])


if __name__ == "__main__":
    unittest.main()
