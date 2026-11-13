"""The date formats the deliveries tools accept."""

import re
from datetime import date

# ISO dates first, then the day-first dates the warehouse spreadsheets use.
SHAPES = (
    re.compile(r"(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})"),
    re.compile(r"(?P<day>\d{2})/(?P<month>\d{2})/(?P<year>\d{4})"),
)


def read_date(text):
    """Return the date in text, read with the first shape in SHAPES that fits, or None if
    none fits or the date it names does not exist."""
    for shape in SHAPES:
        found = shape.fullmatch(text)
        if found:
            try:
                return date(int(found["year"]), int(found["month"]), int(found["day"]))
            except ValueError:
                return None
    return None
