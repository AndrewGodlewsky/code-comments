"""Login counts per user."""
from collections import Counter


def logins_per_user(events):
    """Return {user: number of logins}. Every login counts, unlike one_login_per_user."""
    return dict(Counter(event["user"] for event in events))
