"""The nightly table export."""
from accounts.events import one_login_per_user


def export_user_logins(conn, events):
    """Rebuild the user_logins table from the full login history, one row per user."""
    conn.execute("DELETE FROM user_logins")
    conn.executemany(
        "INSERT INTO user_logins (user, at, device) VALUES (?, ?, ?)",
        [(event["user"], event["at"].isoformat(sep=" "), event["device"])
         for event in one_login_per_user(events)],
    )
    conn.commit()
