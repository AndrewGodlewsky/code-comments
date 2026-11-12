import unittest
from datetime import datetime

from lessons.booking import BookingError, book

START = datetime(2026, 11, 18, 16, 30)


class LessonLengthTest(unittest.TestCase):
    def test_an_hour_long_lesson_gets_an_hour_long_room(self):
        lesson, room = book("Ines", "Tom", "Chemistry", START, 60)
        self.assertEqual(lesson.minutes, 60)
        self.assertEqual(room["duration_minutes"], 60)
        self.assertEqual(room["starts_at"], "2026-11-18T16:30:00")

    def test_every_step_up_to_an_hour_books(self):
        for minutes in range(15, 61, 5):
            with self.subTest(minutes=minutes):
                lesson, room = book("Ines", "Tom", "Chemistry", START, minutes)
                self.assertEqual(lesson.minutes, minutes)
                self.assertEqual(room["duration_minutes"], minutes)

    def test_longer_than_an_hour_is_refused(self):
        for minutes in (65, 90):
            with self.subTest(minutes=minutes), self.assertRaises(BookingError):
                book("Ines", "Tom", "Chemistry", START, minutes)

    def test_short_and_off_step_lengths_are_still_refused(self):
        for minutes in (10, 47):
            with self.subTest(minutes=minutes), self.assertRaises(BookingError):
                book("Ines", "Tom", "Chemistry", START, minutes)


if __name__ == "__main__":
    unittest.main()
