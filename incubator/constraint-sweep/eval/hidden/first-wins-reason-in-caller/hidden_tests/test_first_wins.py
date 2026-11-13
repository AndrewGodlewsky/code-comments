import sqlite3
import unittest
from datetime import datetime
from pathlib import Path

from accounts.events import one_login_per_user
from accounts.export import export_user_logins

BILLING = Path(__file__).resolve().parents[1] / "billing"


def login(user, day, hour, device):
    return {"user": user, "at": datetime(2026, 11, day, hour), "device": device}


EVENTS = [login("ana", 2, 9, "phone"), login("ben", 2, 10, "web"), login("ana", 3, 11, "web"),
          login("cy", 4, 12, "tablet"), login("ben", 5, 13, "phone"), login("ana", 9, 14, "tablet")]


class FirstWinsTest(unittest.TestCase):
    def test_each_users_first_event_is_kept(self):
        kept = one_login_per_user(EVENTS)
        self.assertEqual(len(kept), 3)
        self.assertEqual({event["user"]: event for event in kept},
                         {"ana": EVENTS[0], "ben": EVENTS[1], "cy": EVENTS[3]})

    def test_later_logins_do_not_move_the_trial_clock(self):
        db = sqlite3.connect(":memory:")
        db.executescript((BILLING / "schema.sql").read_text(encoding="utf-8"))
        export_user_logins(db, EVENTS)
        db.executescript((BILLING / "trial_clock.sql").read_text(encoding="utf-8"))
        rows = db.execute("SELECT user, activated_at, trial_ends FROM trial_clock ORDER BY user").fetchall()
        self.assertEqual(rows, [("ana", "2026-11-02 09:00:00", "2026-11-16 09:00:00"),
                                ("ben", "2026-11-02 10:00:00", "2026-11-16 10:00:00"),
                                ("cy", "2026-11-04 12:00:00", "2026-11-18 12:00:00")])


if __name__ == "__main__":
    unittest.main()
