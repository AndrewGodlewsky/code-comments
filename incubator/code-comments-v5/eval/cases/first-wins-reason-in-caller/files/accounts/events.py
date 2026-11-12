"""Helpers over the login event stream.

Events are dicts with "user", "at" (a datetime) and "device", in the order the
gateway recorded them.
"""


def one_login_per_user(events):
    """Return one login event per user."""
    latest_seen = {}
    for event in reversed(events):
        latest_seen[event["user"]] = event
    ordered = []
    for event in events:
        kept = latest_seen.get(event["user"])
        if kept is not None and kept not in ordered:
            ordered.append(kept)
    return ordered


def logins_for(events, user):
    """Return every login event for one user, in stream order."""
    return [event for event in events if event["user"] == user]
