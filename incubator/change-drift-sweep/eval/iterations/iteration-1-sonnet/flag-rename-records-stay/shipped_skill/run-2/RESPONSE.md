I renamed the export command's `--since` option to `--after`. Behaviour is unchanged: rows changed on or after the date are kept. The old spelling is no longer accepted, as you said. The three unit tests pass.

**Code and tests**
- `app/cli.py` now defines `--after`.
- `app/backfill.py` calls `export` with `--after`.
- `tests/test_cli.py` uses `--after`, and I renamed the test to `test_after_keeps_rows_changed_on_or_after_the_date`.
- The `since` argument of `export_rows` in `app/export.py` is unchanged. It's internal, and its docstring is still accurate.

**Docs**
- `README.md`, `docs/cli.md` and `docs/runbooks/backfill.md` now show `--after`.
- `docs/cli.md` used to say `--since` shares its name with the orders API's `since` filter. That is no longer true, so it now says `--after` is that filter under the CLI's usual option name, with the same meaning.
- I added an Unreleased entry to `CHANGELOG.md` noting the rename and that the old spelling is gone.

**Left as written**
- The 1.2.0 changelog line, `docs/adr/0002-incremental-export.md` and `docs/incidents/2026-07-14-missed-night.md` still say `--since`. They record what was true at the time. The ADR's title and decision text name a flag that no longer exists, so you may want a short superseding note or ADR.
- The orders API's `?since=` query parameter is unchanged.

**Things to check**
- Only your own jobs call reportctl, but the nightly job is described as passing the date to `--since`. I found no job definition in this repo, so please update it wherever it lives, or its next run will fail.
- `--after` reads as "strictly after", but the behaviour stays inclusive ("on or after"), as you asked. `docs/cli.md` says so explicitly.
