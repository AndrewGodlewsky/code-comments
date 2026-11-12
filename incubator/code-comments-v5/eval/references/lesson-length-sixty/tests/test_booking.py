import unittest
from datetime import datetime

from lessons.booking import LONGEST_MINUTES, SHORTEST_MINUTES, BookingError, book

START = datetime(2026, 11, 16, 17, 0)


class BookingTest(unittest.TestCase):
    def test_books_a_half_hour_lesson(self):
        lesson, room = book("Ines", "Tom", "Chemistry", START, 30)
        self.assertEqual(lesson.minutes, 30)
        self.assertEqual(room["duration_minutes"], 30)
        self.assertEqual(room["starts_at"], "2026-11-16T17:00:00")

    def test_refuses_lengths_outside_the_range(self):
        for minutes in (SHORTEST_MINUTES - 5, LONGEST_MINUTES + 5, 22):
            with self.subTest(minutes=minutes), self.assertRaises(BookingError):
                book("Ines", "Tom", "Chemistry", START, minutes)


if __name__ == "__main__":
    unittest.main()
