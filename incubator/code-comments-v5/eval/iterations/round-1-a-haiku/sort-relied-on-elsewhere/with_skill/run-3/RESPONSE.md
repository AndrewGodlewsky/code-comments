I dropped the sort from `fetch_rows`, but I did not leave the nightly export unsorted, because `ops/nightly.sh` shows the bank depends on that order.

The bank's matching service reads the file in a single pass and rejects the upload unless the entry ids ascend. The nightly export is that upload, so removing the sort from `fetch_rows` alone would make the nightly job fail. The accounts team sorting the sheet themselves does not change this, since the bank's check happens before anyone opens the file.

What changed:
- `ledger/rows.py`: `fetch_rows` no longer sorts. Its docstring now says the rows come back in no guaranteed order. The balances API (`ledger/api.py`) gets the speedup.
- `ledger/nightly.py`: `export` sorts the rows by id before writing them, with a comment giving the bank reason. The export output is unchanged.
- `ops/nightly.sh`: the comment said the upload relied on `fetch_rows` sorting. That is no longer true, so it now says `ledger.nightly` sorts the rows by id.
- `tests/test_nightly.py`: added `test_rows_are_ordered_by_id`, which inserts out-of-order rows and checks the export is ascending.

`python -m unittest` passes (5 tests).

Open points:
- The nightly job still pays the sort cost, so the speedup applies to the balances API only. If the big-ledger slowness is in the nightly export, this change does not fix it. Tell me if the bank's requirement has changed, and I will drop the sort there too.
- I did not add a CHANGELOG entry for the `fetch_rows` behaviour change. It may be worth an unreleased note.
- `docs/accounts-sheet.md` is still accurate and is unchanged.
