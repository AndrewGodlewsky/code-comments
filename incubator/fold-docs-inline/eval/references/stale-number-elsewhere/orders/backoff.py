"""How long the client waits before it tries a dropped request again."""

from orders.settings import PAUSE_SECONDS


def pause_after(failures):
    """Seconds to wait after the given number of failed attempts at one request."""
    return PAUSE_SECONDS * 2 ** (failures - 1)
