"""Builds and schedules notification digests."""

from collections import defaultdict
from datetime import timedelta

from notify.settings import MIN_HOURS_BETWEEN_DIGESTS


def due(last_sent, now):
    """True when the user may be sent another digest."""
    # Digests are spaced out because users on busy projects complained about digest
    # floods in the 2025 survey (NOTIF-9).
    return last_sent is None or now - last_sent >= timedelta(hours=MIN_HOURS_BETWEEN_DIGESTS)


def build_digest(notifications):
    groups = defaultdict(list)
    for note in notifications:
        if not note["read"]:
            groups[note["project"]].append(note["text"])
    return dict(groups)
