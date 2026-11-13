import unittest
from datetime import date

from deliveries.dates import parse_date


class ParseDateTest(unittest.TestCase):
    def test_reads_iso_dates(self):
        self.assertEqual(parse_date("2026-03-14"), date(2026, 3, 14))

    def test_reads_day_first_dates(self):
        self.assertEqual(parse_date(" 14/03/2026 "), date(2026, 3, 14))

    def test_blank_text_is_none(self):
        self.assertIsNone(parse_date("   "))

    def test_a_note_instead_of_a_date_is_none(self):
        self.assertIsNone(parse_date("tbc"))


if __name__ == "__main__":
    unittest.main()
