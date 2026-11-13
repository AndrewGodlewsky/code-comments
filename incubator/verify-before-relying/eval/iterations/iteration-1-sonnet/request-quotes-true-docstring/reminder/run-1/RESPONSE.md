The deliveries CLI now prints "invalid date" to stderr and exits with status 2 when `parse_date` returns None. The change is in `deliveries/cli.py`, and I added `tests/test_cli.py` to cover it.

Before relying on the `parse_date` docstring, I checked it against the code and tests. It is accurate. `parse_date` returns None for blank text, for non-dates like "tbc", for shapes it doesn't accept (such as "1/1/2026"), and for dates that don't exist (such as 2026-02-30 and 31/02/2026). I ran those cases and also looked at `tests/test_dates.py`. No docstring needed correcting, and I found no conflict with a stated requirement.

I also added a line about the new exit behaviour to the CLI module docstring.

When you run the CLI with no date argument, it still crashes with an IndexError on `argv[0]`. You didn't ask me to change that, so I left it alone.
