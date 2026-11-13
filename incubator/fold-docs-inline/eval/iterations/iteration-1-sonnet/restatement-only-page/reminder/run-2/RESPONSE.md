I deleted `docs/ingest.md`. I didn't add or change any comments or code, because everything on the page was already visible in the code.

I checked each claim against `ingest/rows.py`:

- **`read_rows(path)`:** The code and its docstring already say it returns the CSV rows as dicts keyed by the header row. I left it out.
- **`is_blank(row)`:** The one-line `all(not (value or "").strip() ...)` already shows it is true when every value is empty or whitespace. I left it out.
- **`parse_price(text)`:** The docstring says it returns cents and accepts "12.50" and "12,50", and the `replace(",", ".")` line shows how. The tests cover it too. I left it out.
- **`clean(rows)`:** The docstring already says it drops blank rows and converts each price to cents. I left it out.
- **"Only uses the standard library's `csv` module":** The only import in the module is `csv`, so the code shows this. I left it out.

**Contradictions:** None. Every claim on the page matches the code.

**Kept in a document:** Nothing. No claim was left that had no code to sit beside. `README.md` and `docs/deploy.md` don't link to the deleted page, so no references are left dangling.
