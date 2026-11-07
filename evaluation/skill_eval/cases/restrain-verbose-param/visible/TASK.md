# Support semicolon-delimited CSV imports

Our new partner, Northwind, exports their customer lists from a spreadsheet
configured for a European locale, so their CSV files use semicolons (`;`)
instead of commas to separate fields. Right now `read_rows` in `csv_import.py`
always splits on commas, which means every Northwind row comes back as one
giant column and `read_emails` finds nothing at all.

Please add an optional `delimiter` parameter to `read_rows`, `read_emails` and
`count_rows`:

- It should default to `","`, so that every existing caller keeps working
  exactly as it does today without needing any changes.
- `read_rows` should pass it straight through to `csv.DictReader`.
- `read_emails` and `count_rows` should accept the same parameter and forward
  it to `read_rows`.
- Everything else stays the same: emails are still stripped and lower-cased,
  rows without an email are still skipped, and files are still read as UTF-8.

We'll wire the Northwind import job up to pass `delimiter=";"` in a follow-up
change, so there is nothing to do on the caller side in this one.
