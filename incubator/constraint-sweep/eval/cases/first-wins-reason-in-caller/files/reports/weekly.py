"""The weekly users report."""
from accounts.events import one_login_per_user


def distinct_users(events):
    """Return how many different users logged in during the week's events."""
    # Only the number of users matters here, so any one event per user would do.
    return len(one_login_per_user(events))
