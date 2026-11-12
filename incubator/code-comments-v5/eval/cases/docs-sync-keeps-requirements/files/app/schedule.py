"""When the nightly jobs start."""

from datetime import datetime, time, timedelta, timezone

from app.config import EXPORT_HOUR_UTC


def next_export(now):
    """Return the first export start after now, which must be timezone-aware."""
    start = datetime.combine(now.astimezone(timezone.utc).date(), time(EXPORT_HOUR_UTC), tzinfo=timezone.utc)
    return start if start > now else start + timedelta(days=1)
