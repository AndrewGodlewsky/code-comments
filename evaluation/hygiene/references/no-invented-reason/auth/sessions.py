"""Session expiry.

A session expires after 15 minutes without a request. Each request resets the
clock.
"""

from datetime import datetime, timedelta

from auth.settings import IDLE_TIMEOUT_MINUTES


def expired(last_seen, now=None):
    """Return True when the session at last_seen has been idle too long."""
    now = now or datetime.now()
    return now - last_seen > timedelta(minutes=IDLE_TIMEOUT_MINUTES)
