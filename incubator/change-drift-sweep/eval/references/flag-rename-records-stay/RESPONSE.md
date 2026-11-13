Renamed the `export` option `--since` to `--after`. The old spelling is gone, as you
asked, and argparse now rejects `--since`.

Updated `app/backfill.py` and the tests to use the new option. Updated the docs that
describe the current command: the README usage example, the options table and closing
lines in `docs/cli.md`, and the single-day command in the backfill runbook. `docs/cli.md`
also said the option shares its name with the orders API's filter; the API still calls it
`since`, so that line now says only that the meaning is the same. Added a line under
[Unreleased] in CHANGELOG.md.

Left as written:
- The orders API's own `since=` parameter in `docs/cli.md`, which this change does not
  rename.
- The 1.2.0 CHANGELOG entry ("Added `--since`"), which is true of that release.
- ADR 0002. `docs/adr/README.md` says accepted ADRs are not edited. If you want the
  rename on record there, it would be a new ADR that supersedes it.
- The 14 July 2026 incident report, whose command is what was run that day.

The tests pass.
