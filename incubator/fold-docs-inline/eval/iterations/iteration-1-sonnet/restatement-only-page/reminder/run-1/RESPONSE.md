I deleted `docs/ingest.md`. I didn't add any comments, because every claim on the page was already shown by the code.

I checked each claim against `ingest/rows.py`:

- **`read_rows(path)`** opens a CSV and returns dicts keyed by the header row. The docstring says this and the `csv.DictReader` call shows it.
- **`is_blank(row)`** is true when every value is empty or whitespace. The `all(not (value or "").strip() ...)` expression says exactly that.
- **`parse_price(text)`** turns "12.50" into 1250 cents and accepts a comma as the decimal separator. The docstring covers it, the `.replace(",", ".")` shows it, and `tests/test_rows.py` tests it.
- **`clean(rows)`** drops blank rows and converts each price to cents. The docstring and the code say this.
- **"Only uses the standard library's `csv` module"** is visible from the single `import csv` at the top of the file.

Nothing on the page contradicts the code. Nothing on it was without code to sit beside, so no other document needed to take anything. `README.md` and `docs/deploy.md` don't link to the retired page, so no references were left dangling.

I changed no code and created no files other than this message.
