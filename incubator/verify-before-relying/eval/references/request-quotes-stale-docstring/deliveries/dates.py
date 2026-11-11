"""Date input for the deliveries tools."""

from deliveries.formats import read_date


def parse_date(text):
    """Return the date written in text, or None if text holds no date (blank, or a note
    such as "tbc").

    Raises ValueError if text has the shape of a date that does not exist, such as
    2026-13-45.
    """
    return read_date(text.strip())
