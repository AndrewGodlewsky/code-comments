I deleted `docs/ingest.md`. I added nothing to the code, and I changed no code.

Everything on the page was already in the code or restated it:
- `read_rows`, `parse_price` and `clean` already have docstrings that say the same thing, including the comma decimal separator.
- `is_blank` is described by its name and body, so a comment would only repeat them.
- "Only uses the standard library's `csv` module" repeats the import at the top of `ingest/rows.py`.

The page gave no reasons, constraints or contracts beyond that, so nothing needed moving. No other file linked to the page (I searched for "ingest.md" and found nothing).
