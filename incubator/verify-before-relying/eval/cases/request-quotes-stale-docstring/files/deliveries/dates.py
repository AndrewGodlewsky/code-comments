"""Date input for the deliveries tools."""

from deliveries.formats import read_date


def parse_date(text):
    """Return the date written in text, or None if text is not a valid date."""
    return read_date(text.strip())
