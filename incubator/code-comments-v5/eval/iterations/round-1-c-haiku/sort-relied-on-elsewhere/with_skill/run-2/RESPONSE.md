I dropped the sort from `fetch_rows` (`ledger/rows.py`), so the balances API no longer pays for it. The nightly export still needs ids in ascending order, though, so I moved the sort into `export` in `ledger/nightly.py`.

Your premise was incomplete. `ops/nightly.sh` says the bank's matching service rejects the upload unless entry ids ascend, and the file goes up exactly as `ledger.nightly` writes it. Removing the sort outright would have broken that upload every night. The accounts team's sort does not help here, because the bank reads the file as it arrives.

Changes:
- `ledger/rows.py`: `fetch_rows` returns rows in database order, with no sort.
- `ledger/nightly.py`: `export` writes `sorted(fetch_rows(conn), key=id)`, with a comment that gives the bank requirement and points to `ops/nightly.sh`.
- `ops/nightly.sh`: the header comment said `fetch_rows` returns rows sorted by id. That is no longer true, so it now says `ledger.nightly.export` does the sort.
- `tests/test_nightly.py`: new `test_rows_are_sorted_by_id` covers the export ordering.

`python -m unittest` passes (5 tests).

Still open:
- I did not check whether the database order is actually faster for the balances API on a big ledger. Please re-profile.
- The bank's requirement is recorded only as a comment in `ops/nightly.sh`, with no ticket id. If there is an issue or contact for it, add the id there.
- `CHANGELOG.md` has no entry for this change. Add one if you release it.
