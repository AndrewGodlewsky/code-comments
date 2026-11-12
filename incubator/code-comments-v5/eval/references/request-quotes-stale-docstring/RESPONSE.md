The CLI now prints "invalid date" to stderr and exits with status 2 when the date cannot be
read.

One correction to the premise first: `parse_date` does not return None for every date that is
not valid. It returns None only when the text holds no date at all, such as a blank or "next
tuesday". A mistyped date that still has a date's shape, such as 2026-13-45 or 31/02/2026,
raises ValueError: `read_date` (deliveries/formats.py:19) builds it with `datetime.date`,
which rejects a day that does not exist, and the order-sheet importer
(deliveries/importer.py:19) catches that ValueError to list the row for correction. A check
for None alone would still have crashed with a traceback on exactly the mistyped dates you
mentioned, so the CLI handles both.

I left `parse_date`'s behaviour alone, because the importer and its test rely on the raise,
and corrected its docstring to say when it raises.
