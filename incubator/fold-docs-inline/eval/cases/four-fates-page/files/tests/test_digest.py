import unittest
from datetime import datetime, timedelta

from notify.digest import build_digest, due
from notify.mail import SUBJECT_LIMIT, subject
from notify.settings import MIN_HOURS_BETWEEN_DIGESTS

NOW = datetime(2026, 5, 4, 8, 0)


class DigestTest(unittest.TestCase):
    def test_groups_unread_by_project(self):
        notes = [{"project": "web", "text": "a", "read": False},
                 {"project": "web", "text": "b", "read": True},
                 {"project": "api", "text": "c", "read": False}]
        self.assertEqual(build_digest(notes), {"web": ["a"], "api": ["c"]})

    def test_due_after_the_gap(self):
        self.assertTrue(due(None, NOW))
        self.assertFalse(due(NOW - timedelta(hours=MIN_HOURS_BETWEEN_DIGESTS) + timedelta(minutes=1), NOW))

    def test_subject_is_cut(self):
        self.assertLessEqual(len(subject("x" * 100, 3)), SUBJECT_LIMIT)


if __name__ == "__main__":
    unittest.main()
