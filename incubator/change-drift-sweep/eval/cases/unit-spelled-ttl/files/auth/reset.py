"""Password-reset links."""

import time

from auth.settings import RESET_LINK_TTL_S


def link_is_valid(issued_at, now=None):
    """A reset link works for fifteen minutes after it is sent."""
    now = time.time() if now is None else now
    return now - issued_at <= RESET_LINK_TTL_S
