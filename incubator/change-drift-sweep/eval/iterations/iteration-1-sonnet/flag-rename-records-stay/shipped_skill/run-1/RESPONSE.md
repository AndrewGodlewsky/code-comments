I renamed the export command's `--since` option to `--after`. It behaves exactly as before, and I did not keep `--since` as an alias, as you said. The 3 tests pass.

**Code and tests**
- `app/cli.py` now defines `--after`.
- `app/backfill.py` calls `export` with `--after`.
- The CLI test now uses `--after` and is renamed to match.
- I left the Python parameter `since` in `export_rows` alone, because it is internal and not part of the option.

**Docs I updated because they describe current usage**
- `README.md` and `docs/runbooks/backfill.md` now show `--after` in their examples.
- `docs/cli.md` now lists `--after`.
- I reworded one sentence in `docs/cli.md`. It said the option "shares its name" with the orders API filter, which is no longer true. It now says `--after` selects the same rows as the API's `since` filter, so a date copied from an API query still works. The API's `?since=` parameter is unchanged.
- I added an Unreleased entry to `CHANGELOG.md` noting the rename and that `--since` is no longer accepted.

**Left as written, because they are historical records**
- `docs/adr/0002-incremental-export.md`. The ADR index says accepted ADRs are not edited. If you want the new name recorded as a decision, it needs a new ADR that supersedes this one.
- `docs/incidents/2026-07-14-missed-night.md`, which records the command that was actually run on that day.
- The 1.2.0 entry in `CHANGELOG.md`.

**Needs your attention:** you said only your own jobs call `reportctl`. Any of them that still pass `--since` will fail after this change, so update them in the same release.
