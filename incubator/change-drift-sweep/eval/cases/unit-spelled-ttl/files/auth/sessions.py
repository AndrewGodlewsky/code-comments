"""Session checks for every admin console request.

A session expires after fifteen minutes without a request; the next request is
sent to the sign-in page.
"""

import time

from auth import settings


class SessionStore:
    """Sessions kept in memory, keyed by session id."""

    def __init__(self, clock=time.time):
        self.clock = clock
        self.last_seen = {}

    def start(self, user):
        session_id = f"s-{user}-{len(self.last_seen)}"
        self.last_seen[session_id] = self.clock()
        return session_id

    def touch(self, session_id):
        """Return True and restart the idle timer if the session is live; else end it."""
        seen = self.last_seen.get(session_id)
        if seen is None:
            return False
        now = self.clock()
        if now - seen > settings.SESSION_TTL_S:
            del self.last_seen[session_id]
            return False
        self.last_seen[session_id] = now
        return True

    def should_warn(self, session_id):
        """True while the session is live but close enough to its end to show the banner."""
        seen = self.last_seen.get(session_id)
        if seen is None:
            return False
        idle = self.clock() - seen
        return settings.SESSION_TTL_S - settings.IDLE_WARNING_S <= idle <= settings.SESSION_TTL_S
