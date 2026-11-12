The deliveries CLI now prints `invalid date` to stderr and exits with status 2 when the date cannot be read.

Your docstring premise was only partly true, so I corrected the docstring as well:

- `parse_date` returns None for text that is not in any date format (for example `tbc` or blank text). That matched the docstring.
- It raises `ValueError` for text in a date format that names a day that does not exist (for example `31/02/2026` or `2026-13-01`). The old docstring said it returned None for "not a valid date", which was false for these inputs. I changed the docstring in `deliveries/dates.py` to describe both cases.

Because a mistyped day such as `31/02/2026` raises rather than returning None, the CLI in `deliveries/cli.py` catches `ValueError` as well as checking for None. Both cases print `invalid date` to stderr and return 2.

Checked by running the CLI:
- `14/03/2026` and `2026-03-14` print `2026-03-17` and exit 0.
- `tbc` and `31/02/2026` print `invalid date` to stderr and exit 2.
- The existing unit tests (5) pass.

I did not add a CLI test, and I did not run git.
