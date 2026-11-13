I renamed the `export` command's `--since` option to `--after`. Behaviour is unchanged: it still keeps rows whose `changed` date is on or after the given date, and omitting it still writes every row. The unit tests pass (`python -m unittest`, 3 tests).

What changed:
- `app/cli.py`: the argparse option is now `--after`, and the value is passed to `export_rows` as `after=`.
- `app/export.py`: the `export_rows` parameter is renamed from `since` to `after` to match. Nothing else in the repo called it with a keyword.
- `app/backfill.py`: the internal call to the CLI now passes `--after`.
- `tests/test_cli.py`: the test is renamed and uses `--after`.
- `README.md`, `docs/cli.md`, `docs/runbooks/backfill.md`: examples and the option table now use `--after`. In `docs/cli.md` the sentence about the API filter now says `--after` has the same meaning as the API's `since` query parameter, since the names no longer match.
- `CHANGELOG.md`: an Unreleased entry records the rename and that the old spelling is removed, not aliased.

Left alone on purpose:
- `docs/adr/0002-incremental-export.md` is an accepted ADR and still says `--since`. The ADR README says accepted ADRs are not edited, so if you want the record updated, it needs a new superseding ADR.
- `docs/incidents/2026-07-14-missed-night.md` is a historical record of the command that was run then.
- The older `CHANGELOG.md` entry for 1.2.0 still says `--since`, which is correct for that release.
- The orders API's `?since=` query parameter is not ours and is unchanged.

Action needed outside this repo: the nightly job that calls `reportctl export --since <last successful run>` (described in ADR 0002) is not in this repository. It will fail with an unrecognised-option error until its call is changed to `--after`. Please update it at the same time as this release, or it will miss the nightly export.
