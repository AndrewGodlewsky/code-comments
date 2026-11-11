import unittest
from datetime import datetime

from accounts.events import logins_for, one_login_per_user


def login(user, hour, device="web"):
    return {"user": user, "at": datetime(2026, 11, 2, hour), "device": device}


class OneLoginPerUserTest(unittest.TestCase):
    def test_one_event_per_user(self):
        events = [login("ana", 9), login("ben", 10), login("ana", 11)]
        self.assertEqual(sorted(event["user"] for event in one_login_per_user(events)), ["ana", "ben"])

    def test_no_events(self):
        self.assertEqual(one_login_per_user([]), [])


class LoginsForTest(unittest.TestCase):
    def test_keeps_stream_order(self):
        events = [login("ana", 9), login("ben", 10), login("ana", 11)]
        self.assertEqual([event["at"].hour for event in logins_for(events, "ana")], [9, 11])


if __name__ == "__main__":
    unittest.main()
