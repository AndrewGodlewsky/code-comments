I deleted `docs/ingest.md`. I moved nothing into the code, because nothing on the page belonged there.

Each statement on the page already appears in the code:
- `read_rows`, `parse_price` and `clean` already have docstrings that say the same thing as the page.
- `is_blank` is short enough to read directly, so a docstring would only repeat its body.
- "Only uses the standard library's `csv` module" is visible in the imports.

The page gave no reasons, constraints or decisions, such as why commas are accepted as the decimal separator. I did not invent any. If you know why the comma is accepted, tell me and I'll record it beside `parse_price`.

Nothing else linked to the page (`README.md` and `docs/deploy.md` don't mention it), and I made no code changes.
