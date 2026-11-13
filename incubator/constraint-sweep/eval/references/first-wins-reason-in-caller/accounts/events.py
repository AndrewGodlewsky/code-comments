"""Helpers over the login event stream.

Events are dicts with "user", "at" (a datetime) and "device", in the order the
gateway recorded them.
"""


def one_login_per_user(events):
    """Return one login event per user."""
    # Each user's first event wins: billing/trial_clock.sql starts the trial clock at it.
    first = {}
    for event in events:
        first.setdefault(event["user"], event)
    return list(first.values())


def logins_for(events, user):
    """Return every login event for one user, in stream order."""
    return [event for event in events if event["user"] == user]
