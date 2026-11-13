import sqlite3
import unittest
from datetime import datetime
from pathlib import Path

from accounts.export import export_user_logins

SCHEMA = Path(__file__).resolve().parents[1] / "billing" / "schema.sql"


def login(user, hour, device="web"):
    return {"user": user, "at": datetime(2026, 11, 2, hour), "device": device}


class ExportTest(unittest.TestCase):
    def test_writes_one_row_per_user(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(SCHEMA.read_text(encoding="utf-8"))
        export_user_logins(conn, [login("ana", 9), login("ben", 10), login("ana", 11)])
        users = [row[0] for row in conn.execute("SELECT user FROM user_logins ORDER BY user")]
        self.assertEqual(users, ["ana", "ben"])


if __name__ == "__main__":
    unittest.main()
