The CLI now prints "invalid date" to stderr and exits with status 2 when `parse_date`
returns None. It does that for blank text, for text with no date in it and for a date that
does not exist, such as 2026-13-45 (`read_date` in deliveries/formats.py returns None for all
three). A valid date still prints its delivery estimate.
