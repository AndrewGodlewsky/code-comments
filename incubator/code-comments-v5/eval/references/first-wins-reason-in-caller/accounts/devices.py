"""Which device each user signed in from most recently."""


def last_devices(events):
    """Return {user: device of the user's latest login}."""
    return {event["user"]: event["device"] for event in events}
